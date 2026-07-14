# core/agent/translation.py
"""TranslationAgent: AI 文章翻译。

通过 AgentRuntime 注册，按 HTML 块级元素分段，并发调用 LLM 逐段翻译。
每段附带前一段的上下文以提升连贯性，组装为原文+译文交错的双语 HTML。

特性：
- 按 p/ul/ol/blockquote/h1-h6 顶级块分段（beautifulsoup4）
- asyncio.Semaphore(degree) 控制并发（默认 3，范围 1–5）
- 上下文传递：每段翻译时附带前一段的原文+译文
- 段落级失败恢复：失败段标记，全部完成后统一重试
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.agent.providers import LLMRouter
from core.agent.template_loader import TemplateLoader

if TYPE_CHECKING:
    from core.agent.runtime import AgentRuntime
    from core.reader.pipeline import ReaderPipeline

# 顶级块级标签：翻译的最小单元
_BLOCK_TAGS = {"p", "ul", "ol", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
_MAX_RETRIES = 2

# 双语 HTML 模板
_BLOCK_HTML = """<div class="mercury-trans-block">
<div class="mercury-original">{original}</div>
<div class="mercury-translated" style="margin-left:1.6em;background:#f0f4f8;font-style:italic;padding:8px 12px;border-radius:4px;border-left:3px solid #93c5fd;">{translation}</div>
</div>"""


@dataclass
class _Segment:
    """翻译单元。"""

    index: int
    html: str  # 原始 HTML
    text: str  # 提取的纯文本
    translation: str = ""
    error: str = ""


class TranslationAgentError(Exception):
    """翻译生成失败。"""


class TranslationAgent:
    """文章翻译 AI Agent。

    通过 AgentRuntime 注册，handler 签名匹配 (entry_id, run_id) -> dict | None。

    Usage:
        agent = TranslationAgent(pipeline, router, templates)
        agent.register(runtime)

        # UI 触发翻译：
        run_id = runtime.submit(entry_id, "translation")
    """

    def __init__(
        self,
        pipeline: ReaderPipeline,
        router: LLMRouter,
        templates: TemplateLoader,
    ) -> None:
        self._pipeline = pipeline
        self._router = router
        self._templates = templates
        self._runtime: AgentRuntime | None = None

        # 可配置参数
        self.target_language: str = "Chinese"
        self._degree: int = 3  # 并发度，1–5

    # ── 属性 ─────────────────────────────────────────────────────────────

    @property
    def degree(self) -> int:
        return self._degree

    @degree.setter
    def degree(self, value: int) -> None:
        if not 1 <= value <= 5:
            raise ValueError("degree must be between 1 and 5")
        self._degree = value

    # ── 注册 ─────────────────────────────────────────────────────────────

    def register(self, runtime: AgentRuntime) -> None:
        """向 AgentRuntime 注册 'translation' handler。"""
        self._runtime = runtime
        runtime.register("translation", self._handler)

    # ── Runtime handler ──────────────────────────────────────────────────

    async def _handler(self, entry_id: int, run_id: str) -> dict | None:
        """AgentRuntime handler 接口：(entry_id, run_id) -> dict | None。"""
        return await self.translate(entry_id, run_id)

    # ── 核心翻译逻辑 ─────────────────────────────────────────────────────

    async def translate(self, entry_id: int, run_id: str) -> dict:
        """执行翻译流程。

        1. 从 ReaderPipeline 获取 HTML
        2. 按顶级块元素分段
        3. 并发翻译每段（带上下文）
        4. 重试失败段
        5. 组装双语 HTML
        6. 返回结果

        Returns:
            {"html": str, "paragraphs_total": int, "paragraphs_success": int,
             "paragraphs_failed": int, "target_language": str}
        """
        # ── 1. 获取 HTML ──────────────────────────────────────────────
        rendered = await self._pipeline.build(entry_id)
        if not rendered.html:
            raise TranslationAgentError(
                f"No HTML content available for entry {entry_id}"
            )

        # ── 2. 分段 ───────────────────────────────────────────────────
        segments = self._split_html(rendered.html)
        if not segments:
            raise TranslationAgentError("No translatable blocks found in article")

        total = len(segments)
        self._broadcast_progress(run_id, entry_id, 0.0)

        # ── 3. 并发翻译 ───────────────────────────────────────────────
        tpl = self._templates.load("translation")
        sem = asyncio.Semaphore(self._degree)
        failed_segments: list[_Segment] = []

        async def translate_one(seg: _Segment, prev: _Segment | None) -> None:
            async with sem:
                await self._translate_segment(
                    seg, prev, tpl, run_id, entry_id
                )
            # 更新进度
            done = sum(1 for s in segments if s.translation)
            self._broadcast_progress(run_id, entry_id, done / total)

        # 顺序提交（确保上下文正确），并发执行受 sem 控制
        prev: _Segment | None = None
        tasks = []
        for seg in segments:
            task = asyncio.create_task(translate_one(seg, prev))
            tasks.append(task)
            prev = seg

        # 等待全部完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                segments[i].error = str(result)
                failed_segments.append(segments[i])

        # ── 4. 重试失败段 ──────────────────────────────────────────────
        if failed_segments:
            for _retry in range(_MAX_RETRIES):
                if not failed_segments:
                    break
                still_failed: list[_Segment] = []
                for seg in failed_segments:
                    seg.error = ""
                    prev_seg = segments[seg.index - 1] if seg.index > 0 else None
                    try:
                        await self._translate_segment(
                            seg, prev_seg, tpl, run_id, entry_id
                        )
                    except Exception as exc:
                        seg.error = str(exc)
                        still_failed.append(seg)
                failed_segments = still_failed

        # ── 5. 组装双语 HTML ──────────────────────────────────────────
        bilingual_html = self._assemble_html(segments)
        success_count = total - len(failed_segments)

        # 广播最终结果
        self._broadcast_progress(run_id, entry_id, 1.0)
        if self._runtime:
            self._runtime.broadcast_chunk(run_id, entry_id, "translation", bilingual_html)

        return {
            "html": bilingual_html,
            "paragraphs_total": total,
            "paragraphs_success": success_count,
            "paragraphs_failed": len(failed_segments),
            "target_language": self.target_language,
        }

    # ── 内部分段 ─────────────────────────────────────────────────────────

    def _split_html(self, html: str) -> list[_Segment]:
        """将 HTML 按顶级块元素分段。

        跳过被嵌套的元素（如 li 在 ul 内部），避免重复翻译。
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        segments: list[_Segment] = []
        idx = 0

        for el in soup.find_all(_BLOCK_TAGS):
            # 跳过嵌套在其他块元素中的元素
            parent = el.parent
            if parent and parent.name in _BLOCK_TAGS:
                continue
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue
            segments.append(
                _Segment(
                    index=idx,
                    html=str(el),
                    text=text,
                )
            )
            idx += 1

        return segments

    # ── 单段翻译 ─────────────────────────────────────────────────────────

    async def _translate_segment(
        self,
        seg: _Segment,
        prev: _Segment | None,
        tpl,
        run_id: str,
        entry_id: int,
    ) -> None:
        """翻译单个段落，附带前一段上下文。"""
        system_prompt, user_prompt = self._templates.render(
            tpl,
            target_language=self.target_language,
            previous_original=prev.text if prev else "",
            previous_translation=prev.translation if prev else "",
            paragraph=seg.text,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        parts: list[str] = []
        async for chunk in self._router.chat_stream(
            messages,
            temperature=tpl.config.get("temperature", 0.1),
            max_tokens=tpl.config.get("max_tokens", 2048),
        ):
            parts.append(chunk)

        seg.translation = "".join(parts)

    # ── 组装 ─────────────────────────────────────────────────────────────

    def _assemble_html(self, segments: list[_Segment]) -> str:
        """将原文和译文组装为双语 HTML。"""
        blocks: list[str] = []
        for seg in segments:
            translation = seg.translation or (
                f'<span class="mercury-error">{seg.error}</span>'
                if seg.error
                else '<span class="mercury-pending">[translation pending]</span>'
            )
            blocks.append(
                _BLOCK_HTML.format(
                    original=seg.html,
                    translation=f"<p>{translation}</p>",
                )
            )
        return "\n".join(blocks)

    # ── 进度广播 ─────────────────────────────────────────────────────────

    def _broadcast_progress(
        self, run_id: str, entry_id: int, progress: float
    ) -> None:
        """广播翻译进度（0.0–1.0）给 UI。"""
        if self._runtime:
            from core.agent.runtime import AgentUIEvent

            self._runtime.signals.state_changed.emit(
                AgentUIEvent(
                    run_id=run_id,
                    entry_id=entry_id,
                    agent_type="translation",
                    status="running",
                    progress=progress,
                )
            )
