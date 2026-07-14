# core/agent/summary.py
"""SummaryAgent: AI 文章摘要生成。

通过 AgentRuntime 注册，流式调用 LLM 生成文章摘要。
支持缓存命中、可配置详细程度和语言。

缓存键：(entry_id, provider_name, model, prompt_version)
四字段全匹配走缓存，任一变化触发重新生成。
"""
from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from core.agent.providers import LLMRouter
from core.agent.stream_buffer import StreamBuffer
from core.agent.template_loader import TemplateLoader

if TYPE_CHECKING:
    from core.agent.runtime import AgentRuntime
    from core.reader.pipeline import ReaderPipeline
    from store.agent_store import AgentRun, AgentStore

_CACHE_KEY_VERSION = 1


def _build_cache_key(
    entry_id: int, provider: str, model: str, prompt_version: int
) -> str:
    """构建缓存键字符串，用于匹配已缓存结果。"""
    return f"{entry_id}:{provider}:{model}:{prompt_version}:v{_CACHE_KEY_VERSION}"


class SummaryAgentError(Exception):
    """摘要生成失败。"""


class SummaryAgent:
    """文章摘要 AI Agent。

    通过 AgentRuntime 注册，handler 签名匹配 (entry_id, run_id) -> dict | None。

    Usage:
        agent = SummaryAgent(pipeline, router, templates, agent_store)
        agent.register(runtime)

        # UI 触发摘要：
        run_id = runtime.submit(entry_id, "summary")
    """

    def __init__(
        self,
        pipeline: ReaderPipeline,
        router: LLMRouter,
        templates: TemplateLoader,
        agent_store: AgentStore,
    ) -> None:
        self._pipeline = pipeline
        self._router = router
        self._templates = templates
        self._agent_store = agent_store
        self._runtime: AgentRuntime | None = None

        # 可配置参数（由 UI 在注册前或运行时修改）
        self.detail_level: str = "standard"  # "brief" | "standard" | "detailed"
        self.language: str = "Chinese"        # 目标摘要语言

    # ── 注册 ─────────────────────────────────────────────────────────────

    def register(self, runtime: AgentRuntime) -> None:
        """向 AgentRuntime 注册 'summary' handler。

        注册后 UI 可通过 ``runtime.submit(entry_id, 'summary')`` 触发。
        """
        self._runtime = runtime
        runtime.register("summary", self._handler)

    # ── Runtime handler ──────────────────────────────────────────────────

    async def _handler(self, entry_id: int, run_id: str) -> dict | None:
        """AgentRuntime handler 接口：(entry_id, run_id) -> dict | None。"""
        # 创建 AgentStore 记录
        db_run = await self._agent_store.create(entry_id, "summary")
        try:
            result = await self._generate(entry_id, run_id, db_run)
            await self._agent_store.complete(db_run.id, result)
            return result
        except asyncio.CancelledError:
            await self._agent_store.cancel(db_run.id)
            raise
        except Exception as exc:
            await self._agent_store.complete(db_run.id, None, error=str(exc))
            raise

    # ── 核心生成逻辑 ─────────────────────────────────────────────────────

    async def _generate(
        self, entry_id: int, run_id: str, db_run: AgentRun
    ) -> dict:
        """执行摘要生成流程。

        1. 检查 AgentStore 缓存（同 entry + 同 provider 的已完成结果）
        2. 从 ReaderPipeline 获取文章 Markdown
        3. 渲染提示词模板
        4. 流式调用 LLM，经 StreamBuffer 广播 chunk
        5. 返回完整摘要 dict
        """
        # 加载模板（含版本号用于缓存键）
        tpl = self._templates.load("summary")

        # 获取当前 provider/model 信息用于缓存匹配
        provider_name = self._router.active_provider_name
        model_name = self._router.active_model_name

        # ── 1. 检查缓存 ──────────────────────────────────────────────
        cache_key = _build_cache_key(entry_id, provider_name, model_name, tpl.version)
        cached = await self._agent_store.get_latest(entry_id, "summary")
        if cached and cached.status == "done" and cached.result_json:
            try:
                cached_result = json.loads(cached.result_json)
                if cached_result.get("_cache_key") == cache_key:
                    # 缓存命中：一次性广播完整文本
                    summary_text = cached_result.get("summary", "")
                    if self._runtime and summary_text:
                        self._runtime.broadcast_chunk(
                            run_id, entry_id, "summary", summary_text
                        )
                    return cached_result
            except (json.JSONDecodeError, KeyError):
                pass  # 缓存损坏，重新生成

        # ── 2. 获取文章 Markdown ──────────────────────────────────────
        rendered = await self._pipeline.build(entry_id)
        if not rendered.markdown:
            raise SummaryAgentError(
                f"No markdown content available for entry {entry_id}"
            )

        # ── 3. 渲染提示词 ────────────────────────────────────────────
        system_prompt, user_prompt = self._templates.render(
            tpl,
            content=rendered.markdown,
            language=self.language,
            detail_level=self.detail_level,
        )

        # ── 4. 流式调用 LLM ──────────────────────────────────────────
        full_text_parts: list[str] = []

        async def on_chunk_flush(text: str) -> None:
            if self._runtime:
                self._runtime.broadcast_chunk(run_id, entry_id, "summary", text)

        buf = StreamBuffer(on_flush=on_chunk_flush, interval_ms=80)

        try:
            async for chunk in self._router.chat_stream(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=tpl.config.get("temperature", 0.3),
                max_tokens=tpl.config.get("max_tokens", 1024),
            ):
                full_text_parts.append(chunk)
                await buf.feed(chunk)
            await buf.close()
        except Exception:
            await buf.close()
            raise

        full_text = "".join(full_text_parts)

        # ── 5. 返回结果 ──────────────────────────────────────────────
        return {
            "summary": full_text,
            "provider": provider_name,
            "model": model_name,
            "prompt_version": tpl.version,
            "_cache_key": cache_key,
        }
