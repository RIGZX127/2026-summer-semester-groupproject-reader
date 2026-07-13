# store/entry_store.py
"""EntryStore：文章（Entry）的数据访问层（Phase 1 子集）。

Phase 2 将在此基础上扩展 mark_read / toggle_star / search / soft_delete 等方法。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class EntryRow:
    id: int
    feed_id: int
    guid: str
    url: str | None
    title: str
    summary: str
    author: str
    published_at: str | None
    is_read: bool
    is_starred: bool
    is_deleted: bool
    created_at: str


@dataclass
class EntryListItem:
    id: int
    feed_id: int
    title: str
    summary_snippet: str   # summary 截取前 120 字符
    author: str
    published_at: str | None
    is_read: bool
    is_starred: bool


def _row_to_entry(row: sqlite3.Row) -> EntryRow:
    return EntryRow(
        id=row["id"],
        feed_id=row["feed_id"],
        guid=row["guid"],
        url=row["url"],
        title=row["title"],
        summary=row["summary"],
        author=row["author"],
        published_at=row["published_at"],
        is_read=bool(row["is_read"]),
        is_starred=bool(row["is_starred"]),
        is_deleted=bool(row["is_deleted"]),
        created_at=row["created_at"],
    )


def _row_to_list_item(row: sqlite3.Row) -> EntryListItem:
    summary = row["summary"] or ""
    return EntryListItem(
        id=row["id"],
        feed_id=row["feed_id"],
        title=row["title"],
        summary_snippet=summary[:120],
        author=row["author"],
        published_at=row["published_at"],
        is_read=bool(row["is_read"]),
        is_starred=bool(row["is_starred"]),
    )


class EntryStore:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── 内部同步方法 ───────────────────────────────────────────────────

    def _sync_add(
        self,
        feed_id: int,
        guid: str,
        url: str | None,
        title: str,
        summary: str,
        author: str,
        published_at: str | None,
    ) -> EntryRow:
        with self._conn:
            self._conn.execute(
                """INSERT INTO entries
                   (feed_id, guid, url, title, summary, author, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (feed_id, guid, url, title, summary, author, published_at),
            )
        row = self._conn.execute(
            "SELECT * FROM entries WHERE feed_id = ? AND guid = ?", (feed_id, guid)
        ).fetchone()
        return _row_to_entry(row)

    def _sync_get(self, entry_id: int) -> EntryRow | None:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def _sync_list_by_feed(self, feed_id: int, limit: int, offset: int) -> list[EntryListItem]:
        rows = self._conn.execute(
            """SELECT * FROM entries
               WHERE feed_id = ? AND is_deleted = 0
               ORDER BY published_at DESC
               LIMIT ? OFFSET ?""",
            (feed_id, limit, offset),
        ).fetchall()
        return [_row_to_list_item(r) for r in rows]

    def _sync_guid_exists(self, feed_id: int, guid: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM entries WHERE feed_id = ? AND guid = ?", (feed_id, guid)
        ).fetchone()
        return row is not None

    # ── 公共 async API ─────────────────────────────────────────────────

    async def add(
        self,
        feed_id: int,
        guid: str,
        url: str | None = None,
        title: str = "",
        summary: str = "",
        author: str = "",
        published_at: str | None = None,
    ) -> EntryRow:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_add, feed_id, guid, url, title, summary, author, published_at
        )

    async def get(self, entry_id: int) -> EntryRow | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, entry_id)

    async def list_by_feed(
        self, feed_id: int, limit: int = 50, offset: int = 0
    ) -> list[EntryListItem]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_list_by_feed, feed_id, limit, offset)

    async def guid_exists(self, feed_id: int, guid: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_guid_exists, feed_id, guid)