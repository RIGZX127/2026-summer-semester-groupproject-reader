# platform/file_dialog.py
"""跨平台文件对话框适配器。

封装 QFileDialog，对外暴露纯字符串接口。
Core 和 Store 模块不得直接依赖本模块——调用方（UI）先通过本模块获取路径，
再将路径字符串传递给 Core Controller。

使用方式:
    from platform.file_dialog import select_export_directory
    path = select_export_directory()
    if path:
        result = await digest_controller.export_single(entry_id, path)
"""
from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QWidget


def _ensure_parent(parent: QWidget | None = None) -> QWidget | None:
    """Return a safe parent widget, or None if no QApplication is running."""
    if parent is not None:
        return parent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return None
    # Use the active window if available, otherwise None (which is fine)
    return app.activeWindow()


def select_export_directory(parent: QWidget | None = None) -> str | None:
    """打开"选择目录"对话框，返回所选目录路径或 None。"""
    return QFileDialog.getExistingDirectory(
        _ensure_parent(parent),
        "选择导出目录",
        "",
    ) or None


def open_opml_file(parent: QWidget | None = None) -> str | None:
    """打开"选择 OPML 文件"对话框，返回文件路径或 None。"""
    path, _ = QFileDialog.getOpenFileName(
        _ensure_parent(parent),
        "导入 OPML",
        "",
        "OPML 文件 (*.opml *.xml);;所有文件 (*)",
    )
    return path or None


def save_opml_file(parent: QWidget | None = None) -> str | None:
    """打开"保存 OPML 文件"对话框，返回文件路径或 None。"""
    path, _ = QFileDialog.getSaveFileName(
        _ensure_parent(parent),
        "导出 OPML",
        "mercury_subscriptions.opml",
        "OPML 文件 (*.opml);;所有文件 (*)",
    )
    return path or None
