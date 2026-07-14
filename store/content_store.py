# store/content_store.py
"""ContentStore：Reader 管线结果缓存的数据访问层。

content 表由 Phase 1 的 migrations.py v1 建立，此 Store 只做 CRUD，
不包含版本比较逻辑（那是 core/reader/cache.py 的职责）。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class ContentRow:
    id: int
    entry_id: int
    source_html: str | None
    cleaned_html: str | None
    markdown: str | None
    reader_version: int
    markdown_version: int
    render_version: int
    fetched_at: str


def _row_to_content(row: sqlite3.Row) -> ContentRow:
    return ContentRow(
        id=row["id"],
        entry_id=row["entry_id"],
        source_html=row["source_html"],
        cleaned_html=row["cleaned_html"],
        markdown=row["markdown"],
        reader_version=row["reader_version"],
        markdown_version=row["markdown_version"],
        render_version=row["render_version"],
        fetched_at=row["fetched_at"],
    )


class ContentStore:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── 内部同步方法 ──────────────────────────────────────────────────────

    def _sync_get_by_entry(self, entry_id: int) -> ContentRow | None:
        row = self._conn.execute(
            "SELECT * FROM content WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return _row_to_content(row) if row else None

    def _sync_upsert(
        self,
        entry_id: int,
        source_html: str | None,
        cleaned_html: str | None,
        markdown: str | None,
        reader_version: int,
        markdown_version: int,
        render_version: int,
    ) -> ContentRow:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        # 问题2.5：用 RETURNING * 把 INSERT/UPDATE 和 SELECT 合并为一次往返
        with self._conn:
            row = self._conn.execute(
                """
                INSERT INTO content
                    (entry_id, source_html, cleaned_html, markdown,
                     reader_version, markdown_version, render_version, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                    source_html      = excluded.source_html,
                    cleaned_html     = excluded.cleaned_html,
                    markdown         = excluded.markdown,
                    reader_version   = excluded.reader_version,
                    markdown_version = excluded.markdown_version,
                    render_version   = excluded.render_version,
                    fetched_at       = excluded.fetched_at
                RETURNING *
                """,
                (entry_id, source_html, cleaned_html, markdown,
                 reader_version, markdown_version, render_version, now),
            ).fetchone()
        return _row_to_content(row)

    def _sync_delete_by_entry(self, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM content WHERE entry_id = ?", (entry_id,)
            )

    # ── 公开 async 方法 ───────────────────────────────────────────────────

    async def get_by_entry(self, entry_id: int) -> ContentRow | None:
        loop = asyncio.get_running_loop()   # 问题2.1：已更新为非废弃 API
        return await loop.run_in_executor(None, self._sync_get_by_entry, entry_id)

    async def upsert(
        self,
        entry_id: int,
        source_html: str | None,
        cleaned_html: str | None,
        markdown: str | None,
        reader_version: int,
        markdown_version: int,
        render_version: int,
    ) -> ContentRow:
        loop = asyncio.get_running_loop()   # 问题2.1：已更新为非废弃 API
        return await loop.run_in_executor(
            None,
            self._sync_upsert,
            entry_id, source_html, cleaned_html, markdown,
            reader_version, markdown_version, render_version,
        )

    async def delete_by_entry(self, entry_id: int) -> None:
        loop = asyncio.get_running_loop()   # 问题2.1：已更新为非废弃 API
        await loop.run_in_executor(None, self._sync_delete_by_entry, entry_id)

