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

    # ══════════════════════════════════════════════════════════════════
    #  Phase 2.2 — 文章管理扩展
    # ══════════════════════════════════════════════════════════════════

    # ── 内部同步方法 ──────────────────────────────────────────────────

    def _sync_mark_read(self, entry_id: int, value: int) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE entries SET is_read = ? WHERE id = ?", (value, entry_id)
            )

    def _sync_batch_mark_read(self, feed_id: int, only_before: str | None) -> int:
        sql = (
            "UPDATE entries SET is_read = 1 "
            "WHERE feed_id = ? AND is_deleted = 0 AND is_read = 0"
        )
        params: list = [feed_id]
        if only_before is not None:
            sql += " AND published_at <= ?"
            params.append(only_before)
        with self._conn:
            cur = self._conn.execute(sql, params)
        return cur.rowcount

    def _sync_toggle_star(self, entry_id: int) -> bool:
        row = self._conn.execute(
            "SELECT is_starred FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            return False
        new_value = 1 - row["is_starred"]
        with self._conn:
            self._conn.execute(
                "UPDATE entries SET is_starred = ? WHERE id = ?", (new_value, entry_id)
            )
        return bool(new_value)

    def _sync_search(
        self,
        query: str,
        feed_id: int | None,
        limit: int,
        offset: int,
    ) -> list[EntryListItem]:
        if not query:
            # 空查询等价于列出全部（feed_id 限定范围）
            if feed_id is not None:
                sql = (
                    "SELECT id, feed_id, title, summary, author, published_at, "
                    "is_read, is_starred FROM entries "
                    "WHERE feed_id = ? AND is_deleted = 0 "
                    "ORDER BY published_at DESC LIMIT ? OFFSET ?"
                )
                rows = self._conn.execute(sql, (feed_id, limit, offset)).fetchall()
            else:
                sql = (
                    "SELECT id, feed_id, title, summary, author, published_at, "
                    "is_read, is_starred FROM entries "
                    "WHERE is_deleted = 0 "
                    "ORDER BY published_at DESC LIMIT ? OFFSET ?"
                )
                rows = self._conn.execute(sql, (limit, offset)).fetchall()
        else:
            pattern = f"%{query}%"
            if feed_id is not None:
                sql = (
                    "SELECT id, feed_id, title, summary, author, published_at, "
                    "is_read, is_starred FROM entries "
                    "WHERE (title LIKE ? OR summary LIKE ?) "
                    "AND is_deleted = 0 AND feed_id = ? "
                    "ORDER BY published_at DESC LIMIT ? OFFSET ?"
                )
                rows = self._conn.execute(sql, (pattern, pattern, feed_id, limit, offset)).fetchall()
            else:
                sql = (
                    "SELECT id, feed_id, title, summary, author, published_at, "
                    "is_read, is_starred FROM entries "
                    "WHERE (title LIKE ? OR summary LIKE ?) AND is_deleted = 0 "
                    "ORDER BY published_at DESC LIMIT ? OFFSET ?"
                )
                rows = self._conn.execute(sql, (pattern, pattern, limit, offset)).fetchall()
        return [_row_to_list_item(r) for r in rows]

    def _sync_soft_delete(self, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE entries SET is_deleted = 1 WHERE id = ?", (entry_id,)
            )

    # ── 公开 async 方法 ───────────────────────────────────────────────

    async def mark_read(self, entry_id: int) -> None:
        """将单篇文章标记为已读。entry_id 不存在时静默忽略。"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_mark_read, entry_id, 1)

    async def mark_unread(self, entry_id: int) -> None:
        """将单篇文章标记为未读。entry_id 不存在时静默忽略。"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_mark_read, entry_id, 0)

    async def batch_mark_read(
        self, feed_id: int, only_before: str | None = None
    ) -> int:
        """批量标记 feed_id 下所有未读文章为已读。返回实际标记的数量。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_batch_mark_read, feed_id, only_before
        )

    async def toggle_star(self, entry_id: int) -> bool:
        """切换收藏状态。返回操作后的新状态（True=已收藏）。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_toggle_star, entry_id)

    async def search(
        self,
        query: str,
        feed_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EntryListItem]:
        """在标题和摘要中搜索关键词（LIKE，不区分大小写）。支持分页。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_search, query, feed_id, limit, offset
        )

    async def soft_delete(self, entry_id: int) -> None:
        """软删除：is_deleted=1，物理数据保留。entry_id 不存在时静默忽略。"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_soft_delete, entry_id)
