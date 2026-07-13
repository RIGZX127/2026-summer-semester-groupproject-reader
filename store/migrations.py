# store/migrations.py
"""版本化数据库迁移管理器。

规则：
  - PRAGMA user_version 记录当前已应用的迁移版本号。
  - 每个迁移函数在独立事务中执行；失败则回滚该迁移，已完成的不受影响。
  - migrate() 幂等：已达目标版本则直接返回。
"""
from __future__ import annotations

import sqlite3

CURRENT_VERSION: int = 1


def migrate(conn: sqlite3.Connection) -> None:
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    migrations = [
        (1, _migration_v1),
    ]
    for target_version, fn in migrations:
        if version < target_version:
            try:
                with conn:
                    fn(conn)
                    conn.execute(f"PRAGMA user_version={target_version}")
                version = target_version
            except Exception:
                raise


def _migration_v1(conn: sqlite3.Connection) -> None:
    """创建 v1 初始 Schema：全部 10 张表 + 必要索引。"""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS feeds (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        url         TEXT    NOT NULL UNIQUE,
        title       TEXT    NOT NULL DEFAULT '',
        description TEXT    NOT NULL DEFAULT '',
        favicon_url TEXT,
        created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS entries (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        feed_id      INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
        guid         TEXT    NOT NULL,
        url          TEXT,
        title        TEXT    NOT NULL DEFAULT '',
        summary      TEXT    NOT NULL DEFAULT '',
        author       TEXT    NOT NULL DEFAULT '',
        published_at TEXT,
        is_read      INTEGER NOT NULL DEFAULT 0,
        is_starred   INTEGER NOT NULL DEFAULT 0,
        is_deleted   INTEGER NOT NULL DEFAULT 0,
        created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        UNIQUE(feed_id, guid)
    );
    CREATE INDEX IF NOT EXISTS idx_entries_feed_id    ON entries(feed_id);
    CREATE INDEX IF NOT EXISTS idx_entries_published  ON entries(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_entries_is_deleted ON entries(is_deleted);

    CREATE TABLE IF NOT EXISTS content (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id         INTEGER NOT NULL UNIQUE REFERENCES entries(id) ON DELETE CASCADE,
        source_html      TEXT,
        cleaned_html     TEXT,
        markdown         TEXT,
        reader_version   INTEGER NOT NULL DEFAULT 0,
        markdown_version INTEGER NOT NULL DEFAULT 0,
        render_version   INTEGER NOT NULL DEFAULT 0,
        fetched_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id   INTEGER NOT NULL UNIQUE REFERENCES entries(id) ON DELETE CASCADE,
        body       TEXT    NOT NULL DEFAULT '',
        updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS tags (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL UNIQUE,
        normalized_name TEXT    NOT NULL UNIQUE,
        created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS entry_tags (
        entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
        tag_id   INTEGER NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
        PRIMARY KEY (entry_id, tag_id)
    );

    CREATE TABLE IF NOT EXISTS tag_aliases (
        alias            TEXT    NOT NULL PRIMARY KEY,
        canonical_tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS agent_runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
        agent_type  TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'idle',
        result_json TEXT,
        error       TEXT,
        started_at  TEXT,
        finished_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_agent_runs_entry ON agent_runs(entry_id, agent_type);

    CREATE TABLE IF NOT EXISTS llm_usage (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        provider          TEXT    NOT NULL,
        model             TEXT    NOT NULL,
        agent_type        TEXT    NOT NULL,
        prompt_tokens     INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS app_settings (
        key   TEXT NOT NULL PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    """)