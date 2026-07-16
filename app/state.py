# app/state.py
"""全局应用状态单例。

AppState 是整个应用的唯一可变全局状态容器。
禁止其他模块声明可变全局变量；所有跨模块共享状态必须挂载到此对象上。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # 避免循环导入；运行时类型通过 Any 注解


@dataclass
class AppState:
    """Phase 1 初始字段集合，后续里程碑增量扩充。"""

    # ── 订阅源列表（Phase 1.2 填充，类型为 list[FeedRow]）──────────────
    feeds: list = field(default_factory=list)

    # ── 当前选中的订阅源 ID（None 表示未选中）──────────────────────────
    selected_feed_id: int | None = None

    # ── 数据库管理器（启动时由 app/app.py 注入 DatabaseManager 实例）──
    db: Any | None = None

    # ── AI Agent 运行时（Phase 3 注入）──────────────────────────────────
    agent_runtime: Any | None = None

    # ── LLM 是否已配置（Phase 3 注入）────────────────────────────────────
    has_llm: bool = False


# 模块级单例 —— 整个进程共享同一个 AppState 实例
state = AppState()
