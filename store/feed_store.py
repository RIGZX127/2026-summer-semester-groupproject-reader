# store/feed_store.py
"""FeedStore：订阅源（Feed）的数据访问层。

所有阻塞的 sqlite3 调用均通过 run_in_executor 包装为协程，
保证不阻塞 Qt 主线程。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


class DuplicateFeedError(Exception):
    """尝试插入重复 URL 的订阅源时抛出。"""


@dataclass
class FeedRow:
    id: int
    url: str
    title: str
    description: str
    favicon_url: str | None
    created_at: str
    updated_at: str


def _row_to_feed(row: sqlite3.Row) -> FeedRow:
    return FeedRow(
        id=row["id"],
        url=row["url"],
        title=row["title"],
        description=row["description"],
        favicon_url=row["favicon_url"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class FeedStore:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── 内部同步方法（在 executor 线程中运行）──────────────────────────

    def _sync_add(self, url: str, title: str, description: str) -> FeedRow:
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO feeds (url, title, description) VALUES (?, ?, ?)",
                    (url, title, description),
                )
            row = self._conn.execute(
                "SELECT * FROM feeds WHERE url = ?", (url,)
            ).fetchone()
            return _row_to_feed(row)
        except sqlite3.IntegrityError as exc:
            raise DuplicateFeedError(f"Feed URL already exists: {url}") from exc

    def _sync_get(self, feed_id: int) -> FeedRow | None:
        row = self._conn.execute(
            "SELECT * FROM feeds WHERE id = ?", (feed_id,)
        ).fetchone()
        return _row_to_feed(row) if row else None

    def _sync_list_all(self) -> list[FeedRow]:
        rows = self._conn.execute(
            "SELECT * FROM feeds ORDER BY created_at ASC"
        ).fetchall()
        return [_row_to_feed(r) for r in rows]

    def _sync_update(self, feed_id: int, title: str | None, favicon_url: str | None) -> None:
        fields, values = [], []
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if favicon_url is not None:
            fields.append("favicon_url = ?")
            values.append(favicon_url)
        if not fields:
            return
        fields.append("updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')")
        values.append(feed_id)
        with self._conn:
            self._conn.execute(
                f"UPDATE feeds SET {', '.join(fields)} WHERE id = ?", values
            )

    def _sync_delete(self, feed_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))

    def _sync_unread_count(self, feed_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE feed_id = ? AND is_read = 0 AND is_deleted = 0",
            (feed_id,),
        ).fetchone()
        return row[0]

    # ── 公共 async API ─────────────────────────────────────────────────

    async def add(self, url: str, title: str = "", description: str = "") -> FeedRow:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_add, url, title, description)

    async def get(self, feed_id: int) -> FeedRow | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, feed_id)

    async def list_all(self) -> list[FeedRow]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_list_all)

    async def update(
        self,
        feed_id: int,
        *,
        title: str | None = None,
        favicon_url: str | None = None,
    ) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_update, feed_id, title, favicon_url)

    async def delete(self, feed_id: int) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_delete, feed_id)

    async def unread_count(self, feed_id: int) -> int:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_unread_count, feed_id)