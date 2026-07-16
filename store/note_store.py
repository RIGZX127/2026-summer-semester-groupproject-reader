# store/note_store.py
"""NoteStore：文章笔记的数据访问层。

notes 表由 migrations v1 创建，Schema 为：
    notes(id, entry_id UNIQUE, body TEXT, updated_at TEXT)

每篇文章最多一条笔记（UNIQUE entry_id）。
- get(entry_id)       → NoteRow | None
- save(entry_id, body) → NoteRow     # upsert，body 为空字符串时保留记录
- delete(entry_id)     → None
- list_all()           → list[NoteRow]

所有公开方法均为 async，内部同步操作在 run_in_executor 中执行。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class NoteRow:
    id: int
    entry_id: int
    body: str
    updated_at: str


def _row_to_note(row: sqlite3.Row) -> NoteRow:
    return NoteRow(
        id=row["id"],
        entry_id=row["entry_id"],
        body=row["body"],
        updated_at=row["updated_at"],
    )


class NoteStore:
    """文章笔记的 CRUD 层，对应 notes 表。"""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── 内部同步方法 ─────────────────────────────────────────────────

    def _sync_get(self, entry_id: int) -> NoteRow | None:
        row = self._conn.execute(
            "SELECT * FROM notes WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return _row_to_note(row) if row else None

    def _sync_save(self, entry_id: int, body: str) -> NoteRow:
        """Upsert：有则更新 body + updated_at，无则插入。"""
        with self._conn:
            self._conn.execute(
                """INSERT INTO notes (entry_id, body, updated_at)
                   VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                   ON CONFLICT(entry_id) DO UPDATE SET
                       body       = excluded.body,
                       updated_at = excluded.updated_at""",
                (entry_id, body),
            )
        row = self._conn.execute(
            "SELECT * FROM notes WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return _row_to_note(row)

    def _sync_delete(self, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM notes WHERE entry_id = ?", (entry_id,)
            )

    def _sync_list_all(self) -> list[NoteRow]:
        rows = self._conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_note(r) for r in rows]

    def _sync_list_by_entry_ids(self, entry_ids: list[int]) -> dict[int, NoteRow]:
        """批量查询，返回 {entry_id: NoteRow} 字典，方便 UI 层快速检查。"""
        if not entry_ids:
            return {}
        placeholders = ",".join("?" * len(entry_ids))
        rows = self._conn.execute(
            f"SELECT * FROM notes WHERE entry_id IN ({placeholders})",  # noqa: S608
            entry_ids,
        ).fetchall()
        return {r["entry_id"]: _row_to_note(r) for r in rows}

    # ── 公开 async API ────────────────────────────────────────────────

    async def get(self, entry_id: int) -> NoteRow | None:
        """获取指定文章的笔记。不存在返回 None。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, entry_id)

    async def save(self, entry_id: int, body: str) -> NoteRow:
        """创建或更新笔记。body 可为空字符串（保留空白笔记占位）。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_save, entry_id, body)

    async def delete(self, entry_id: int) -> None:
        """删除笔记。entry_id 不存在时静默忽略。"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_delete, entry_id)

    async def list_all(self) -> list[NoteRow]:
        """返回全部笔记，按 updated_at 倒序。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_list_all)

    async def list_by_entry_ids(self, entry_ids: list[int]) -> dict[int, NoteRow]:
        """批量查询多篇文章的笔记，返回 {entry_id: NoteRow}。
        仅返回有笔记的条目，无笔记的 entry_id 不在结果中。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_list_by_entry_ids, entry_ids)
