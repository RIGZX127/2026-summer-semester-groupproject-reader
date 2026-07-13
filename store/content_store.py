# store/content_store.py
"""ContentStore：Reader 管线 4 阶段缓存的数据访问层。

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

    # ── 内部同步方法（在 executor 线程中运行）──────────────────────────

    def _sync_upsert(
        self,
        entry_id: int,
        source_html: str | None = None,
        cleaned_html: str | None = None,
        markdown: str | None = None,
        reader_version: int | None = None,
        markdown_version: int | None = None,
        render_version: int | None = None,
    ) -> ContentRow:
        """插入或更新 entry_id 对应的内容缓存行。

        仅更新显式传入的非 None 字段，未传入的字段保留原值。
        """
        # 收集 INSERT 阶段的非 None 值
        insert_fields = ["entry_id"]
        insert_values = [entry_id]

        for field, value in (
            ("source_html", source_html),
            ("cleaned_html", cleaned_html),
            ("markdown", markdown),
            ("reader_version", reader_version),
            ("markdown_version", markdown_version),
            ("render_version", render_version),
        ):
            if value is not None:
                insert_fields.append(field)
                insert_values.append(value)

        # 构建 UPDATE SET 子句：仅更新非 None 字段 + 刷新 fetched_at
        set_parts = []
        set_values = []
        for field, value in (
            ("source_html", source_html),
            ("cleaned_html", cleaned_html),
            ("markdown", markdown),
            ("reader_version", reader_version),
            ("markdown_version", markdown_version),
            ("render_version", render_version),
        ):
            if value is not None:
                set_parts.append(f"{field} = ?")
                set_values.append(value)

        # 始终刷新 fetched_at
        set_parts.append("fetched_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')")

        placeholders = ", ".join("?" for _ in insert_fields)
        set_clause = ", ".join(set_parts)

        sql = (
            f"INSERT INTO content ({', '.join(insert_fields)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(entry_id) DO UPDATE SET {set_clause}"
        )

        with self._conn:
            self._conn.execute(sql, insert_values + set_values)

        row = self._conn.execute(
            "SELECT * FROM content WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return _row_to_content(row)

    def _sync_get(self, entry_id: int) -> ContentRow | None:
        row = self._conn.execute(
            "SELECT * FROM content WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return _row_to_content(row) if row else None

    def _sync_delete(self, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM content WHERE entry_id = ?", (entry_id,)
            )

    # ── 公共 async API ─────────────────────────────────────────────────

    async def upsert(
        self,
        entry_id: int,
        *,
        source_html: str | None = None,
        cleaned_html: str | None = None,
        markdown: str | None = None,
        reader_version: int | None = None,
        markdown_version: int | None = None,
        render_version: int | None = None,
    ) -> ContentRow:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_upsert,
            entry_id,
            source_html,
            cleaned_html,
            markdown,
            reader_version,
            markdown_version,
            render_version,
        )

    async def get(self, entry_id: int) -> ContentRow | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, entry_id)

    async def delete(self, entry_id: int) -> None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_delete, entry_id)
