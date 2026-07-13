# store/db.py
"""DatabaseManager：SQLite 连接管理器。

职责：
  - 以 WAL 模式打开 SQLite 数据库。
  - 启动时按顺序执行所有 PRAGMA。
  - 启动时自动调用 migrations.migrate() 完成 Schema 迁移。
  - 暴露只读 connection 属性供各 Store 使用。
  - 提供 close() 方法。

规则：
  - 本模块不提供任何 async 方法；异步包装在各 Store 中完成。
  - 传入 ":memory:" 路径时用于单元测试。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


class DatabaseManager:
    def __init__(self, path: str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._configure()

        from store import migrations
        migrations.migrate(self._conn)

    def _configure(self) -> None:
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()
