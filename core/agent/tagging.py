# core/agent/tagging.py
"""TagAgent: AI 标签建议与去重。

通过 AgentRuntime 注册，流式调用 LLM 为文章生成标签建议。
建议的标签会与已有标签做去重（语义去重由 LLM prompt 完成，
本地再做名称规范化后的精确去重）。

依赖：
  - 强制：ReaderPipeline, LLMRouter, TemplateLoader
  - 可选：TagStore（G4.1 交付后注入），Normalizer（G4.1 交付后注入）
    未注入时仅返回 LLM 建议的原始标签列表。
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from core.agent.providers import LLMRouter
from core.agent.template_loader import TemplateLoader

if TYPE_CHECKING:
    from collections.abc import Callable

    from core.agent.runtime import AgentRuntime
    from core.reader.pipeline import ReaderPipeline


class TagAgentError(Exception):
    """标签生成失败。"""


class TagAgent:
    """文章标签 AI Agent。

    通过 AgentRuntime 注册，handler 签名匹配 (entry_id, run_id) -> dict | None。

    设计要点：
      - LLM 在 prompt 层面基于已有标签列表做语义去重
      - 本地仅做名称规范化后的精确去重（小写、去首尾空白）
      - TagStore 和 Normalizer 为可选注入（G4.1 未交付前可独立运行）

    Usage:
        agent = TagAgent(pipeline, router, templates)
        agent.register(runtime)

        # 可选：注入标签依赖（G4.1 交付后）
        agent.set_tag_dependencies(normalizer=norm_fn, existing_tags_fn=get_tags)

        # UI 触发：
        run_id = runtime.submit(entry_id, "tagging")
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

        # 可选依赖（G4.1 后注入）
        self._normalizer: Callable[[str], str] | None = None
        self._existing_tags_fn: Callable[[], list[str]] | None = None

        # 可配置参数
        self.max_tags: int = 5  # 每次建议的最大标签数
        self.language: str = "Chinese"

    # ── 可选依赖注入 ─────────────────────────────────────────────────────

    def set_tag_dependencies(
        self,
        normalizer: Callable[[str], str] | None = None,
        existing_tags_fn: Callable[[], list[str]] | None = None,
    ) -> None:
        """注入标签系统的可选依赖（G4.1 交付后由 A 调用）。

        Args:
            normalizer: 标签规范化函数，签名 (raw_tag: str) -> normalized: str。
            existing_tags_fn: 获取当前文章已有标签的函数。
        """
        if normalizer is not None:
            self._normalizer = normalizer
        if existing_tags_fn is not None:
            self._existing_tags_fn = existing_tags_fn

    # ── 注册 ─────────────────────────────────────────────────────────────

    def register(self, runtime: AgentRuntime) -> None:
        """向 AgentRuntime 注册 'tagging' handler。"""
        self._runtime = runtime
        runtime.register("tagging", self._handler)

    # ── Runtime handler ──────────────────────────────────────────────────

    async def _handler(self, entry_id: int, run_id: str) -> dict | None:
        """AgentRuntime handler 接口：(entry_id, run_id) -> dict | None。"""
        return await self.suggest(entry_id, run_id)

    # ── 核心逻辑 ─────────────────────────────────────────────────────────

    async def suggest(self, entry_id: int, run_id: str) -> dict:
        """为文章建议标签。

        流程：
          1. 获取文章 Markdown
          2. 收集已有标签列表
          3. 渲染提示词模板（含已有标签）
          4. 流式调用 LLM 生成建议
          5. 解析 JSON 响应
          6. 规范化 + 去重
          7. 返回结果

        Returns:
            {
                "tags": ["tag1", "tag2", ...],
                "raw_tags": ["raw1", ...],
                "existing_tags": [...],
                "provider": str,
                "model": str,
            }
        """
        # ── 1. 获取文章内容 ──────────────────────────────────────────
        rendered = await self._pipeline.build(entry_id)
        content = rendered.markdown or rendered.html
        if not content:
            raise TagAgentError(
                f"No content available for entry {entry_id}"
            )

        # ── 2. 收集已有标签 ──────────────────────────────────────────
        existing: list[str] = []
        if self._existing_tags_fn is not None:
            try:
                existing = self._existing_tags_fn()
            except Exception:
                pass  # 标签获取失败不影响核心流程

        # ── 3. 渲染提示词 ────────────────────────────────────────────
        tpl = self._templates.load("tagging")
        system_prompt, user_prompt = self._templates.render(
            tpl,
            content=content[:6000],  # 截断过长的文章
            existing_tags=existing,
            max_tags=self.max_tags,
            language=self.language,
        )

        # ── 4. 流式调用 LLM ──────────────────────────────────────────
        parts: list[str] = []
        async for chunk in self._router.chat_stream(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=tpl.config.get("temperature", 0.5),
            max_tokens=tpl.config.get("max_tokens", 256),
        ):
            parts.append(chunk)
            # 广播流式 chunk（TagAgent 也支持流式）
            if self._runtime:
                self._runtime.broadcast_chunk(
                    run_id, entry_id, "tagging", chunk
                )

        full_text = "".join(parts)

        # ── 5. 解析 JSON ─────────────────────────────────────────────
        raw_tags = self._parse_tags(full_text)

        # ── 6. 规范化 + 去重 ─────────────────────────────────────────
        final_tags = self._normalize_and_dedup(raw_tags, existing)

        # ── 7. 返回结果 ──────────────────────────────────────────────
        return {
            "tags": final_tags,
            "raw_tags": raw_tags,
            "existing_tags": existing,
            "provider": self._router.active_provider_name,
            "model": self._router.active_model_name,
            "prompt_version": tpl.version,
        }

    # ── 标签解析 ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_tags(text: str) -> list[str]:
        """从 LLM 响应中提取 JSON 数组。

        容错处理：
          - 直接 JSON 解析
          - Markdown 代码块包裹：```json [...] ```
          - 逐行匹配 "tag" 格式
        """
        import re

        text = text.strip()

        # 尝试直接解析
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return [str(t).strip() for t in result if str(t).strip()]
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的 JSON
        code_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if code_match:
            try:
                result = json.loads(code_match.group(1))
                if isinstance(result, list):
                    return [str(t).strip() for t in result if str(t).strip()]
            except json.JSONDecodeError:
                pass

        # 尝试提取任意 JSON 数组
        array_match = re.search(r"\[.*?\]", text, re.DOTALL)
        if array_match:
            try:
                result = json.loads(array_match.group(0))
                if isinstance(result, list):
                    return [str(t).strip() for t in result if str(t).strip()]
            except json.JSONDecodeError:
                pass

        # 最终回退：按行拆分，取引号中的字符串
        candidates = re.findall(r'"([^"]+)"', text)
        if candidates:
            return [c.strip() for c in candidates if c.strip()]

        return []

    def _normalize_and_dedup(
        self, raw_tags: list[str], existing: list[str]
    ) -> list[str]:
        """规范化并去重标签。

        步骤：
          1. 规范化每个标签（使用 Normalizer 或内置简易方法）
          2. 过滤已存在于 existing 中的标签（规范化后比较）
          3. 过滤列表内部的重复（保留首次出现）
        """
        normalized_existing: set[str] = set()
        for tag in existing:
            n = self._normalize_one(tag)
            normalized_existing.add(n)

        seen: set[str] = set()
        result: list[str] = []

        for raw in raw_tags:
            if len(result) >= self.max_tags:
                break
            n = self._normalize_one(raw)
            if n and n not in normalized_existing and n not in seen:
                seen.add(n)
                result.append(raw)  # 保留原始大小写，但已去重

        return result

    def _normalize_one(self, tag: str) -> str:
        """规范化单个标签。"""
        if self._normalizer is not None:
            try:
                return self._normalizer(tag)
            except Exception:
                pass
        # 内置简易规范化：小写 + 去首尾空白
        return tag.strip().lower()
