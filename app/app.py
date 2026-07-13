# app/app.py
"""MercuryApp：顶层应用类，负责初始化数据库并启动主窗口。

Phase 1 桩版本：仅打开一个空 QMainWindow，验证启动流程。
"""
from __future__ import annotations

import pathlib
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from app.state import state
from store.db import DatabaseManager


def _default_data_path() -> str:
    """返回平台默认数据库路径（Phase 1 硬编码在用户目录）。"""
    base = pathlib.Path.home() / ".mercury"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "mercury.db")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mercury RSS Reader")
        self.setMinimumSize(1100, 700)

        # 占位标签，Phase 1.4 由成员 C 替换为真实 UI
        placeholder = QLabel("Mercury — Phase 1 脚手架启动成功 ✓", self)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(placeholder)


class MercuryApp:
    """应用生命周期管理器。"""

    def __init__(self) -> None:
        # 初始化数据库并注入到全局状态
        db_path = _default_data_path()
        state.db = DatabaseManager(db_path)

    def create_main_window(self) -> MainWindow:
        return MainWindow()
