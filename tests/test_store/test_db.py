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
    assert version == 3


def test_migration_v1_all_tables_exist(db: DatabaseManager) -> None:
    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = {r[0] for r in rows}
    expected = {
        "feeds",
        "entries",
        "content",
        "notes",
        "tags",
        "entry_tags",
        "tag_aliases",
        "agent_runs",
        "llm_usage",
        "app_settings",
    }
    assert expected.issubset(table_names)


def test_migration_idempotent(db: DatabaseManager) -> None:
    """二次迁移不抛异常，user_version 不变。"""
    from store import migrations

    migrations.migrate(db.connection)
    version = db.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == 3


def test_required_indexes_exist(db: DatabaseManager) -> None:
    rows = db.connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    index_names = {r[0] for r in rows}
    assert "idx_entries_feed_id" in index_names
    assert "idx_entries_published" in index_names
    assert "idx_agent_runs_entry" in index_names


def test_migration_v3_adds_is_deleted_to_existing_table() -> None:
    """v3 迁移为没有 is_deleted 列的旧表补齐该列。"""
    import sqlite3
    import tempfile
    import os

    # 模拟"早期开发版本创建的 entries 表"——没有 is_deleted 列
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    try:
        old = sqlite3.connect(tmp_path)
        old.execute("PRAGMA user_version=0")
        old.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id      INTEGER NOT NULL,
                guid         TEXT    NOT NULL,
                url          TEXT,
                title        TEXT    NOT NULL DEFAULT '',
                summary      TEXT    NOT NULL DEFAULT '',
                author       TEXT    NOT NULL DEFAULT '',
                published_at TEXT,
                is_read      INTEGER NOT NULL DEFAULT 0,
                is_starred   INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                UNIQUE(feed_id, guid)
            );
        """)
        old.close()

        # 打开该旧数据库——应触发所有迁移
        from store.db import DatabaseManager
        mgr = DatabaseManager(tmp_path)

        # 验证 is_deleted 列已补齐
        cols = {
            row[1]
            for row in mgr.connection.execute(
                "PRAGMA table_info('entries')"
            ).fetchall()
        }
        assert "is_deleted" in cols

        # 验证版本号
        version = mgr.connection.execute("PRAGMA user_version").fetchone()[0]
        assert version == 3

        # 验证可以正常写入带 is_deleted 的数据
        mgr.connection.execute(
            "INSERT INTO entries (feed_id, guid, title) VALUES (1, 'g1', 't')"
        )
        row = mgr.connection.execute(
            "SELECT is_deleted FROM entries WHERE guid='g1'"
        ).fetchone()
        assert row["is_deleted"] == 0

        mgr.close()
    finally:
        os.unlink(tmp_path)
        for ext in ("-wal", "-shm"):
            p = tmp_path + ext
            if os.path.exists(p):
                os.unlink(p)
