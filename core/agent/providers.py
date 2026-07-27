# core/agent/providers.py
"""LLM 提供者配置与模型路由。

- ProviderConfig: 单个 LLM 提供者配置
- LLMRouter: 主模型 -> 回退模型路由，async chat_stream() 返回异步生成器
- api_key 使用 keyring 存储，不存数据库
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import httpx

SERVICE_NAME = "mercury-llm"


def _keyring():
    """Lazy-import keyring. Returns None if unavailable (e.g. PyInstaller bundle)."""
    try:
        import keyring

        return keyring
    except ImportError:
        return None


@dataclass
class ProviderConfig:
    """单个 LLM 提供者配置。

    API key 优先从系统 keyring 读取，不可用时降级到内存存储。
    """

    name: str
    base_url: str
    model: str
    is_primary: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)
    _key: str | None = field(default=None, repr=False)

    def get_api_key(self) -> str | None:
        kr = _keyring()
        if kr is not None:
            stored = kr.get_password(SERVICE_NAME, self.name)
            if stored:
                return stored
        return self._key

    def set_api_key(self, key: str) -> None:
        self._key = key
        kr = _keyring()
        if kr is not None:
            kr.set_password(SERVICE_NAME, self.name, key)

    def delete_api_key(self) -> None:
        self._key = None
        kr = _keyring()
        if kr is not None:
            try:
                kr.delete_password(SERVICE_NAME, self.name)
            except Exception:
                pass


class LLMRouterError(Exception):
    """所有已配置的 LLM 提供者均失败。"""


class LLMRouter:
    """LLM 路由：主模型 -> 回退模型。

    主模型连续 2 次失败后自动切换至回退模型。
    每次调用后自动记录用量到 llm_usage 表（通过 UsageStore）。
    """

    def __init__(
        self,
        primary: ProviderConfig,
        fallback: ProviderConfig | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_failures = 0
        self._using_fallback = False
        self._usage_store = None  # 由调用方在初始化后注入

    def set_usage_store(self, store) -> None:
        """注入 UsageStore 实例，用于记录 LLM 调用用量。"""
        self._usage_store = store

    def _get_active(self) -> ProviderConfig:
        if self._using_fallback and self._fallback:
            return self._fallback
        return self._primary

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        agent_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式 LLM 调用。

        Args:
            messages: 对话消息列表。
            temperature: 采样温度。
            max_tokens: 最大输出 token 数。
            agent_type: Agent 类型标识（如 "summary", "translation", "tagging"），
                       用于用量统计记录。

        Yields:
            每个 chunk 的文本增量（delta.content）。

        Raises:
            LLMRouterError: 主模型和回退模型均失败。
        """
        provider = self._get_active()
        api_key = provider.get_api_key() or ""
        full_text_parts: list[str] = []

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=provider.base_url,
                api_key=api_key,
                timeout=httpx.Timeout(60.0),
            )
            stream = await client.chat.completions.create(
                model=provider.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                extra_headers=provider.extra_headers or None,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full_text_parts.append(delta.content)
                    yield delta.content

            self._primary_failures = 0
            if self._using_fallback:
                self._using_fallback = False

            # ── 记录用量（仅成功路径；fallback 递归调用各自记录）───
            await self._record_usage(
                messages, "".join(full_text_parts),
                provider.name, provider.model, agent_type,
            )

        except Exception as exc:
            self._primary_failures += 1
            if not self._using_fallback and self._fallback and self._primary_failures >= 2:
                self._using_fallback = True
                self._primary_failures = 0
                async for chunk in self.chat_stream(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    agent_type=agent_type,
                ):
                    yield chunk
                return
            raise LLMRouterError(
                f"LLM call failed (provider={provider.name}, "
                f"failures={self._primary_failures}): {exc}"
            ) from exc

    async def test_connection(self, provider: ProviderConfig) -> tuple[bool, list[str], str]:
        """测试提供者连接。

        Returns:
            (success, model_list, error_message)
        """
        try:
            api_key = provider.get_api_key() or ""
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=provider.base_url,
                api_key=api_key,
                timeout=httpx.Timeout(15.0),
            )
            models = await client.models.list()
            model_ids = [m.id for m in models.data]
            return True, model_ids, ""
        except Exception as exc:
            return False, [], str(exc)

    @property
    def active_provider_name(self) -> str:
        return self._get_active().name

    @property
    def active_model_name(self) -> str:
        return self._get_active().model

    async def _record_usage(
        self,
        messages: list[dict[str, str]],
        full_text: str,
        provider_name: str,
        model_name: str,
        agent_type: str | None,
    ) -> None:
        """记录单次 LLM 调用用量到 UsageStore。"""
        if self._usage_store is None or agent_type is None:
            return
        try:
            # 字符数 ÷ 3 估算 token（混合中英文，跨 provider 通用）
            prompt_chars = sum(len(m.get("content", "")) for m in messages)
            prompt_tokens = max(1, prompt_chars // 3)
            completion_tokens = max(1, len(full_text) // 3)
            await self._usage_store.record(
                provider=provider_name,
                model=model_name,
                agent_type=agent_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        except Exception:
            pass  # 用量记录失败不影响核心流程
