# app/app.py
"""Mercury application lifecycle and dependency wiring."""

from __future__ import annotations

import pathlib

from PySide6.QtWidgets import QApplication

from app.state import state
from app.styles import application_stylesheet
from core.feed.sync import SyncService
from store.db import DatabaseManager
from store.entry_store import EntryStore
from store.feed_store import FeedStore
from ui.main_window import MainWindow


def _default_data_path() -> str:
    """返回平台默认数据库路径（Phase 1 硬编码在用户目录）。"""
    base = pathlib.Path.home() / ".mercury"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "mercury.db")


class MercuryApp:
    """应用生命周期管理器。"""

    def __init__(self) -> None:
        # 初始化数据库并注入到全局状态
        db_path = _default_data_path()
        state.db = DatabaseManager(db_path)

    def create_main_window(self) -> MainWindow:
        """创建主窗口并注入已锁定的数据与同步接口。"""
        if state.db is None:
            raise RuntimeError("Database is not initialized")

        window = MainWindow(
            feed_store=FeedStore(state.db),
            entry_store=EntryStore(state.db),
            sync_service=SyncService(state.db),
        )

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(application_stylesheet())

        return window