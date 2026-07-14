# core/agent/stream_buffer.py
"""流式 chunk 缓冲器。

80ms 合并窗口：收到的 chunk 先累积，定时器到期后合并输出。
所有 Agent 必须通过此缓冲器发送 UI 信号，不得绕过。
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class StreamBuffer:
    """流式文本缓冲器。

    Usage:
        buf = StreamBuffer(on_flush=handle_text)
        await buf.feed("Hello ")
        await buf.feed("World")
        await buf.close()  # 确保最后一批 flushed
    """

    def __init__(
        self,
        on_flush: Callable[[str], Awaitable[None]],
        interval_ms: int = 80,
    ) -> None:
        self._on_flush = on_flush
        self._interval = interval_ms / 1000.0
        self._buffer: list[str] = []
        self._task: asyncio.Task | None = None
        self._closed = False

    async def feed(self, chunk: str) -> None:
        """输入一个 chunk。"""
        if self._closed:
            return
        self._buffer.append(chunk)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._flush_after_delay())

    async def _flush_after_delay(self) -> None:
        await asyncio.sleep(self._interval)
        await self.flush()

    async def flush(self) -> None:
        """立即合并并输出当前缓冲内容。"""
        if self._buffer:
            merged = "".join(self._buffer)
            self._buffer.clear()
            await self._on_flush(merged)

    async def close(self) -> None:
        """关闭缓冲器，flush 剩余内容。"""
        self._closed = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.flush()
