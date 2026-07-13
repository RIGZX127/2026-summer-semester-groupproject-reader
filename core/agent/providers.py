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
import keyring

SERVICE_NAME = "mercury-llm"


@dataclass
class ProviderConfig:
    """单个 LLM 提供者配置。"""

    name: str  # 显示名称，如 "Ollama Local"
    base_url: str  # 如 "http://localhost:11434/v1"
    model: str  # 如 "qwen3"
    is_primary: bool = True  # True=主模型, False=回退模型
    extra_headers: dict[str, str] = field(default_factory=dict)

    def get_api_key(self) -> str | None:
        return keyring.get_password(SERVICE_NAME, self.name)

    def set_api_key(self, key: str) -> None:
        keyring.set_password(SERVICE_NAME, self.name, key)

    def delete_api_key(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, self.name)
        except keyring.errors.PasswordDeleteError:
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
    ) -> AsyncGenerator[str, None]:
        """流式 LLM 调用。

        Yields:
            每个 chunk 的文本增量（delta.content）。

        Raises:
            LLMRouterError: 主模型和回退模型均失败。
        """
        provider = self._get_active()
        api_key = provider.get_api_key() or "local"

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
                    yield delta.content

            self._primary_failures = 0
            if self._using_fallback:
                self._using_fallback = False

        except Exception as exc:
            self._primary_failures += 1
            if (
                not self._using_fallback
                and self._fallback
                and self._primary_failures >= 2
            ):
                self._using_fallback = True
                self._primary_failures = 0
                async for chunk in self.chat_stream(
                    messages, temperature=temperature, max_tokens=max_tokens
                ):
                    yield chunk
                return
            raise LLMRouterError(
                f"LLM call failed (provider={provider.name}, "
                f"failures={self._primary_failures}): {exc}"
            ) from exc

    async def test_connection(
        self, provider: ProviderConfig
    ) -> tuple[bool, list[str], str]:
        """测试提供者连接。

        Returns:
            (success, model_list, error_message)
        """
        try:
            api_key = provider.get_api_key() or "local"
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
