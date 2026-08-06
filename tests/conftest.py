# tests/conftest.py
"""pytest 全局 fixture。"""

from __future__ import annotations

import pytest

from store.db import DatabaseManager
from store.entry_store import EntryStore
from store.feed_store import FeedStore


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
