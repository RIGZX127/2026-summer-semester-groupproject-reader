# main.py
"""Mercury Cross-Platform RSS Reader — 程序唯一入口。

职责：
  1. 实例化 QApplication，设置组织/应用名称（QSettings 命名空间）。
  2. 集成 qasync.QEventLoop，替换默认 Qt 事件循环。
  3. 实例化 MercuryApp，打开主窗口。
  4. 顶层异常保护：未预期异常打印堆栈后以退出码 1 退出。
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from pathlib import Path

import qasync
from PySide6.QtWidgets import QApplication

from app.app import MercuryApp
from app.state import state


def _fixup_qt_paths() -> None:
    """Ensure Qt finds its plugins and QWebEngineProcess in PyInstaller bundles.

    Works for both --onedir (files alongside exe) and --onefile (temp extraction).
    """
    if not getattr(sys, "frozen", False):
        return

    # sys._MEIPASS points to _internal/ (onedir) or temp dir (onefile)
    base = Path(sys._MEIPASS)  # type: ignore[attr-defined]

    qt_plugins = base / "PySide6" / "plugins"
    if qt_plugins.is_dir():
        os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)

    webengine = base / "PySide6" / "QtWebEngineProcess.exe"
    if webengine.is_file():
        os.environ["QTWEBENGINEPROCESS_PATH"] = str(webengine)

    # Also check one level up (onedir: _internal is sibling of exe)
    if not webengine.is_file():
        webengine = base.parent / "PySide6" / "QtWebEngineProcess.exe"
        if webengine.is_file():
            os.environ["QTWEBENGINEPROCESS_PATH"] = str(webengine)

    # Translations for Qt (otherwise Chinese/English text may not render)
    qt_translations = base / "PySide6" / "translations"
    if qt_translations.is_dir():
        os.environ["QT_TRANSLATIONS_DIR"] = str(qt_translations)


def main() -> int:
    print("[Mercury] Starting application...", flush=True)
    _fixup_qt_paths()

    app = QApplication(sys.argv)
    app.setOrganizationName("Mercury")
    app.setApplicationName("ChenXing")

    # qasync: QEventLoop must be created BEFORE any async-using widgets
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    print("[Mercury] Event loop initialized.", flush=True)

    print("[Mercury] Initializing database...", flush=True)
    try:
        mercury = MercuryApp()
    except Exception as exc:
        _show_fatal_error("数据库初始化失败", str(exc))
        return 1
    print("[Mercury] Database ready.", flush=True)

    print("[Mercury] Creating main window...", flush=True)
    try:
        window = mercury.create_main_window()
    except Exception as exc:
        _show_fatal_error("窗口创建失败", str(exc))
        if state.db is not None:
            state.db.close()
        return 1
    print("[Mercury] Main window created.", flush=True)

    print("[Mercury] Showing window...", flush=True)
    window.show()
    print("[Mercury] Window shown. Entering event loop.", flush=True)

    try:
        with loop:
            return loop.run_forever()
    finally:
        if state.db is not None:
            state.db.close()


def _show_fatal_error(title: str, detail: str) -> None:
    """Display a critical error dialog and write full traceback to a log file."""
    tb = traceback.format_exc()
    print(tb, flush=True)

    # Write to log file on desktop for easy access
    try:
        log_path = Path.home() / "Desktop" / "mercury_startup_error.log"
        log_path.write_text(
            f"=== Mercury Startup Error ===\n{title}\n{detail}\n\n{tb}", encoding="utf-8"
        )
        print(f"[Mercury] Error log written to: {log_path}", flush=True)
    except Exception:
        pass

    from PySide6.QtWidgets import QMessageBox

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(f"ChenXing — {title}")
    msg.setText(f"启动失败：{title}\n\n{detail}")
    msg.setDetailedText(tb)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
