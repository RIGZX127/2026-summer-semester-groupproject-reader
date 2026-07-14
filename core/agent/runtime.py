# core/agent/runtime.py
"""AgentRuntime: 共享 AI Agent 运行时。

G3.1+G3.2 gate 接口：状态机 + 队列 + 信号发射。

设计决策：
  - 单例模式（__new__），通过 AppState 注入。
  - 状态机：idle -> queued -> running -> done | error | cancelled。
  - 队列每个 agent_type 最多 1 个等待槽，新提交替换旧等待任务。
  - 取消通过 asyncio.Task.cancel() 实现，handler 内会收到 CancelledError。
  - 所有信号通过 PySide6 Signal 发射，Qt 自动排队到主线程。

线程安全说明：
  假定 asyncio 事件循环与 Qt 主线程在同一线程运行（qasync 模式），
  共享状态（_queue, _processing 等）不需要额外锁保护。
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import QObject, Signal

# ── 类型别名 ────────────────────────────────────────────────────────────────

AgentStatus = Literal["idle", "queued", "running", "done", "error", "cancelled"]


# ── G3.2 frozen 接口 ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentUIEvent:
    """Agent UI 事件，通过信号传递给前端。

    所有字段在构造后不可变（frozen dataclass）。
    """
    run_id: str
    entry_id: int
    agent_type: str
    status: AgentStatus
    chunk: str = ""
    progress: float = 0.0
    error: str | None = None
    result_json: str | None = None


# ── Qt 信号层 ──────────────────────────────────────────────────────────────

class AgentSignals(QObject):
    """Agent 运行时 Qt 信号集合。"""
    state_changed = Signal(object)   # AgentUIEvent
    chunk_received = Signal(object)  # AgentUIEvent (status=running, chunk=text)


# ── 运行时核心 ─────────────────────────────────────────────────────────────

class AgentRuntime:
    """共享 AI Agent 运行时（单例）。

    状态机: idle -> queued -> running -> done | error | cancelled

    使用方式::

        runtime = AgentRuntime()
        runtime.register("translate", my_async_handler)
        run_id = runtime.submit(entry_id=42, agent_type="translate")
        ...

        # 在 handler 内广播流式文本
        runtime.broadcast_chunk(run_id, entry_id, "translate", "partial text")
    """

    _instance: AgentRuntime | None = None

    def __new__(cls) -> AgentRuntime:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._signals = AgentSignals()
        self._handlers: dict[str, Callable[[int, str], Awaitable[dict | None]]] = {}
        # (run_id, entry_id, agent_type) 三元组
        self._queue: list[tuple[str, int, str]] = []
        self._current_run_id: str | None = None
        self._current_agent_type: str | None = None
        self._current_task: asyncio.Task | None = None
        self._cancel_requested = False
        self._processing = False

    # ── 公开属性 ───────────────────────────────────────────────────────────

    @property
    def signals(self) -> AgentSignals:
        """获取 AgentSignals 信号对象。"""
        return self._signals

    # ── 注册 / 提交 / 取消 ─────────────────────────────────────────────────

    def register(
        self,
        agent_type: str,
        handler: Callable[[int, str], Awaitable[dict | None]],
    ) -> None:
        """注册指定 agent_type 的异步处理函数。

        Args:
            agent_type: Agent 类型标识符（如 "translate", "summarize"）。
            handler: 异步处理函数，签名 ``(entry_id: int, run_id: str) -> dict | None``。
                     返回值会被序列化为 result_json 发送给前端。
        """
        self._handlers[agent_type] = handler

    def submit(self, entry_id: int, agent_type: str) -> str:
        """提交一个 Agent 任务。

        规则:
        - 如果当前 idle，立即开始处理。
        - 如果已有同类型任务在队列中等待，替换之（latest-replace 策略）。
        - 如果当前有同类型任务正在运行，新任务排队等待（仅保留一个等待槽）。

        Args:
            entry_id: 条目 ID。
            agent_type: Agent 类型标识符。

        Returns:
            本次提交的 run_id（12 位十六进制字符串）。
        """
        run_id = uuid.uuid4().hex[:12]

        # 检查是否有同 agent_type 的排队任务，替换之
        for i, (_rid, _eid, at) in enumerate(self._queue):
            if at == agent_type:
                self._queue[i] = (run_id, entry_id, agent_type)
                self._emit_status(run_id, entry_id, agent_type, "queued")
                return run_id

        # 无替换，加入队列尾部
        self._queue.append((run_id, entry_id, agent_type))
        self._emit_status(run_id, entry_id, agent_type, "queued")

        # 如果空闲，启动处理循环
        if not self._processing:
            asyncio.create_task(self._process_next())

        return run_id

    def cancel(self, run_id: str) -> None:
        """取消指定 run_id 的任务。

        - 如果任务在队列中，直接从队列移除并发射 ``cancelled`` 状态。
        - 如果任务正在运行，取消其 asyncio Task 并发射 ``cancelled``。
        - 如果 run_id 不存在，无操作。
        """
        # 尝试从队列移除
        for i, (rid, eid, at) in enumerate(self._queue):
            if rid == run_id:
                self._queue.pop(i)
                self._emit_status(rid, eid, at, "cancelled")
                return

        # 如果正在运行，标记取消并取消 asyncio Task
        if run_id == self._current_run_id:
            self._cancel_requested = True
            if self._current_task is not None and not self._current_task.done():
                self._current_task.cancel()

    def broadcast_chunk(
        self, run_id: str, entry_id: int, agent_type: str, chunk_text: str
    ) -> None:
        """广播流式文本 chunk 到 UI。

        由 Agent handler 通过 StreamBuffer 的回调调用::

            async def on_flush(text: str) -> None:
                runtime.broadcast_chunk(run_id, entry_id, agent_type, text)
            buf = StreamBuffer(on_flush=on_flush)
        """
        event = AgentUIEvent(
            run_id=run_id,
            entry_id=entry_id,
            agent_type=agent_type,
            status="running",
            chunk=chunk_text,
        )
        self._signals.chunk_received.emit(event)

    # ── 内部方法 ───────────────────────────────────────────────────────────

    def _emit_status(
        self,
        run_id: str,
        entry_id: int,
        agent_type: str,
        status: AgentStatus,
        *,
        error: str | None = None,
        result_json: str | None = None,
    ) -> None:
        """构造 AgentUIEvent 并发射 state_changed 信号。"""
        event = AgentUIEvent(
            run_id=run_id,
            entry_id=entry_id,
            agent_type=agent_type,
            status=status,
            error=error,
            result_json=result_json,
        )
        self._signals.state_changed.emit(event)

    async def _process_next(self) -> None:
        """异步处理队列中的下一个任务（由 asyncio.create_task 启动）。

        流程:
        1. 从队列弹出下一个任务
        2. 发射 ``running`` 状态
        3. 将 handler 包装为独立 asyncio.Task（可被 cancel() 取消）
        4. 等待 handler 完成
        5. 发射 ``done`` / ``error`` / ``cancelled``
        6. 重复直到队列为空
        """
        self._processing = True
        try:
            while self._queue:
                run_id, entry_id, agent_type = self._queue.pop(0)
                self._current_run_id = run_id
                self._current_agent_type = agent_type
                self._cancel_requested = False

                self._emit_status(run_id, entry_id, agent_type, "running")

                handler = self._handlers.get(agent_type)
                if handler is None:
                    self._emit_status(
                        run_id,
                        entry_id,
                        agent_type,
                        "error",
                        error=f"No handler registered for agent_type={agent_type!r}",
                    )
                    self._current_run_id = None
                    self._current_agent_type = None
                    continue

                # 将 handler 包装为独立 Task，以便 cancel() 可以取消它
                handler_task = asyncio.create_task(handler(entry_id, run_id))
                self._current_task = handler_task

                try:
                    result = await handler_task

                    if self._cancel_requested:
                        self._emit_status(run_id, entry_id, agent_type, "cancelled")
                    else:
                        result_json = None
                        if result is not None:
                            result_json = json.dumps(result, ensure_ascii=False)
                        self._emit_status(
                            run_id,
                            entry_id,
                            agent_type,
                            "done",
                            result_json=result_json,
                        )

                except asyncio.CancelledError:
                    self._emit_status(run_id, entry_id, agent_type, "cancelled")
                except Exception as exc:
                    self._emit_status(
                        run_id,
                        entry_id,
                        agent_type,
                        "error",
                        error=str(exc),
                    )
                finally:
                    self._current_task = None
                    self._current_run_id = None
                    self._current_agent_type = None

        finally:
            self._processing = False
            self._current_run_id = None
            self._current_agent_type = None
