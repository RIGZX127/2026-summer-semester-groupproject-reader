# tests/conftest.py
"""pytest 全局 fixture。"""
from __future__ import annotations

# ── sys.path 修复 ──────────────────────────────────────────────────────────────
# 项目根目录包含 platform/ 包，会遮蔽 Python 标准库的 platform 模块。
# 在导入任何模块前，将标准库目录移到 sys.path 最前面，确保标准库优先。
import sys as _sys


def _fix_stdlib_path() -> None:
    import sysconfig as _sc
    stdlib_dir = _sc.get_paths()["stdlib"]
    if stdlib_dir not in _sys.path:
        _sys.path.insert(0, stdlib_dir)
    # 同时确保 platlibdir 在前
    platstdlib_dir = _sc.get_paths().get("platstdlib", "")
    if platstdlib_dir and platstdlib_dir not in _sys.path:
        _sys.path.insert(0, platstdlib_dir)

_fix_stdlib_path()
# ──────────────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402

from store.db import DatabaseManager  # noqa: E402
from store.entry_store import EntryStore  # noqa: E402
from store.feed_store import FeedStore  # noqa: E402


@pytest.fixture
def db() -> DatabaseManager:
    """内存数据库，每个测试函数独立一个实例，测试结束自动关闭。"""
    manager = DatabaseManager(":memory:")
    yield manager
    manager.close()


@pytest.fixture
def feed_store(db: DatabaseManager) -> FeedStore:
    return FeedStore(db)


@pytest.fixture
def entry_store(db: DatabaseManager) -> EntryStore:
    return EntryStore(db)