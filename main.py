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
import sys
import traceback

from PySide6.QtWidgets import QApplication

import qasync

from app.app import MercuryApp


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("Mercury")
    app.setApplicationName("Mercury")

    mercury = MercuryApp()
    window = mercury.create_main_window()
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
