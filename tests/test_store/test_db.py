# tests/test_store/test_db.py
"""DatabaseManager 与 migrations 单元测试。"""
from __future__ import annotations

import os
import tempfile

from store.db import DatabaseManager


def test_wal_mode_enabled_disk_db() -> None:
    """WAL 模式只对磁盘数据库有效；在临时文件上验证。"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    try:
        mgr = DatabaseManager(tmp_path)
        result = mgr.connection.execute("PRAGMA journal_mode").fetchone()[0]
        mgr.close()
        assert result == "wal"
    finally:
        os.unlink(tmp_path)
        wal = tmp_path + "-wal"
        shm = tmp_path + "-shm"
        if os.path.exists(wal):
            os.unlink(wal)
        if os.path.exists(shm):
            os.unlink(shm)


def test_wal_mode_memory_returns_memory(db: DatabaseManager) -> None:
    """:memory: 数据库的 journal_mode 固定为 'memory'（SQLite 规范行为）。"""
    result = db.connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert result == "memory"


def test_foreign_keys_enabled(db: DatabaseManager) -> None:
    result = db.connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert result == 1


def test_migration_v1_user_version(db: DatabaseManager) -> None:
    version = db.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == 1


def test_migration_v1_all_tables_exist(db: DatabaseManager) -> None:
    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = {r[0] for r in rows}
    expected = {
        "feeds", "entries", "content", "notes",
        "tags", "entry_tags", "tag_aliases",
        "agent_runs", "llm_usage", "app_settings",
    }
    assert expected.issubset(table_names)


def test_migration_idempotent(db: DatabaseManager) -> None:
    """二次迁移不抛异常，user_version 不变。"""
    from store import migrations
    migrations.migrate(db.connection)
    version = db.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == 1


def test_required_indexes_exist(db: DatabaseManager) -> None:
    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()
    index_names = {r[0] for r in rows}
    assert "idx_entries_feed_id" in index_names
    assert "idx_entries_published" in index_names
    assert "idx_agent_runs_entry" in index_names