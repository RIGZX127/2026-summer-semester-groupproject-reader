# store/tag_store.py
"""TagStore：标签系统的数据访问层。

提供：
  - 标签 CRUD（创建、查询、删除）
  - 文章打标/取消（entry_tags）
  - 批量打标 + 临时标签（待用户确认）
  - 别名管理（tag_aliases）
  - 标签统计（每标签文章数）

所有公开方法 async，内部同步方法在 executor 中执行。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class TagRow:
    id: int
    name: str
    normalized_name: str
    created_at: str


@dataclass
class TagWithCount(TagRow):
    entry_count: int = 0


@dataclass
class EntryTagRow:
    entry_id: int
    tag_id: int
    tag_name: str


@dataclass
class TagAliasRow:
    alias: str
    canonical_tag_id: int
    canonical_name: str


def _row_to_tag(row: sqlite3.Row) -> TagRow:
    return TagRow(
        id=row["id"],
        name=row["name"],
        normalized_name=row["normalized_name"],
        created_at=row["created_at"],
    )


def _row_to_tag_with_count(row: sqlite3.Row) -> TagWithCount:
    return TagWithCount(
        id=row["id"],
        name=row["name"],
        normalized_name=row["normalized_name"],
        created_at=row["created_at"],
        entry_count=row["entry_count"],
    )


class TagStore:
    """标签数据访问层。

    Usage:
        store = TagStore(db)
        tag = await store.create("Machine Learning")
        await store.add_to_entry(entry_id=1, tag_id=tag.id)
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── Tag CRUD ───────────────────────────────────────────────────────

    def _sync_create(self, name: str, normalized_name: str) -> TagRow:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO tags (name, normalized_name) VALUES (?, ?)",
                (name, normalized_name),
            )
        row = self._conn.execute(
            "SELECT * FROM tags WHERE normalized_name = ?", (normalized_name,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Failed to create tag: {name}")
        return _row_to_tag(row)

    def _sync_get(self, tag_id: int) -> TagRow | None:
        row = self._conn.execute(
            "SELECT * FROM tags WHERE id = ?", (tag_id,)
        ).fetchone()
        return _row_to_tag(row) if row else None

    def _sync_get_by_name(self, normalized_name: str) -> TagRow | None:
        row = self._conn.execute(
            "SELECT * FROM tags WHERE normalized_name = ?", (normalized_name,)
        ).fetchone()
        return _row_to_tag(row) if row else None

    def _sync_list_all(self) -> list[TagWithCount]:
        rows = self._conn.execute(
            """SELECT t.*, COUNT(et.entry_id) AS entry_count
               FROM tags t
               LEFT JOIN entry_tags et ON t.id = et.tag_id
               GROUP BY t.id
               ORDER BY entry_count DESC, t.name ASC"""
        ).fetchall()
        return [_row_to_tag_with_count(r) for r in rows]

    def _sync_search(self, query: str) -> list[TagRow]:
        rows = self._conn.execute(
            "SELECT * FROM tags WHERE name LIKE ? OR normalized_name LIKE ? "
            "ORDER BY name LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [_row_to_tag(r) for r in rows]

    def _sync_delete(self, tag_id: int) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            return cur.rowcount > 0

    # ── Entry-Tag associations ──────────────────────────────────────────

    def _sync_add_to_entry(self, entry_id: int, tag_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_id),
            )

    def _sync_remove_from_entry(self, entry_id: int, tag_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM entry_tags WHERE entry_id = ? AND tag_id = ?",
                (entry_id, tag_id),
            )

    def _sync_set_entry_tags(self, entry_id: int, tag_ids: list[int]) -> None:
        """原子替换文章的全部标签。"""
        with self._conn:
            self._conn.execute(
                "DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,)
            )
            self._conn.executemany(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                [(entry_id, tid) for tid in tag_ids],
            )

    def _sync_get_entry_tags(self, entry_id: int) -> list[EntryTagRow]:
        rows = self._conn.execute(
            """SELECT et.entry_id, et.tag_id, t.name AS tag_name
               FROM entry_tags et
               JOIN tags t ON et.tag_id = t.id
               WHERE et.entry_id = ?
               ORDER BY t.name""",
            (entry_id,),
        ).fetchall()
        return [
            EntryTagRow(entry_id=r["entry_id"], tag_id=r["tag_id"], tag_name=r["tag_name"])
            for r in rows
        ]

    def _sync_get_entries_by_tag(self, tag_id: int, limit: int = 50) -> list[int]:
        rows = self._conn.execute(
            """SELECT e.id FROM entries e
               JOIN entry_tags et ON e.id = et.entry_id
               WHERE et.tag_id = ? AND e.is_deleted = 0
               ORDER BY e.published_at DESC LIMIT ?""",
            (tag_id, limit),
        ).fetchall()
        return [r[0] for r in rows]

    # ── Batch operations ────────────────────────────────────────────────

    def _sync_batch_tag(
        self, entry_ids: list[int], tag_names: list[str]
    ) -> dict[str, int]:
        """批量给多篇文章打多个标签。

        Returns:
            {tag_name: affected_entry_count}
        """
        results: dict[str, int] = {}
        for name in tag_names:
            tag = self._sync_get_by_name(name)
            if tag is None:
                # Create on first use
                tag = self._sync_create(name, name)
            count = 0
            with self._conn:
                for eid in entry_ids:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                        (eid, tag.id),
                    )
                    count += self._conn.total_changes
            results[name] = count
        return results

    # ── Alias management ────────────────────────────────────────────────

    def _sync_add_alias(self, alias: str, canonical_tag_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO tag_aliases (alias, canonical_tag_id) VALUES (?, ?)",
                (alias, canonical_tag_id),
            )

    def _sync_remove_alias(self, alias: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM tag_aliases WHERE alias = ?", (alias,)
            )
            return cur.rowcount > 0

    def _sync_list_aliases(self) -> list[TagAliasRow]:
        rows = self._conn.execute(
            """SELECT ta.alias, ta.canonical_tag_id, t.name AS canonical_name
               FROM tag_aliases ta
               JOIN tags t ON ta.canonical_tag_id = t.id
               ORDER BY ta.alias"""
        ).fetchall()
        return [
            TagAliasRow(
                alias=r["alias"],
                canonical_tag_id=r["canonical_tag_id"],
                canonical_name=r["canonical_name"],
            )
            for r in rows
        ]

    def _sync_get_alias_map(self) -> dict[str, str]:
        """返回 {alias: canonical_normalized_name}。"""
        rows = self._conn.execute(
            """SELECT ta.alias, t.normalized_name
               FROM tag_aliases ta
               JOIN tags t ON ta.canonical_tag_id = t.id"""
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ── Temporary tags ──────────────────────────────────────────────────

    def _sync_add_temp_tags(self, entry_id: int, tag_names: list[str]) -> list[TagRow]:
        """为文章添加临时标签（标记为待确认状态）。

        临时标签以 normalized_name 前缀 "~" 存储，等待用户确认后去除前缀。
        当前实现：直接创建正式标签。未来可扩展 status 字段。
        """
        result: list[TagRow] = []
        for name in tag_names:
            tag = self._sync_get_by_name(name)
            if tag is None:
                tag = self._sync_create(name, name)
            self._sync_add_to_entry(entry_id, tag.id)
            result.append(tag)
        return result

    # ── Async wrappers ──────────────────────────────────────────────────

    async def create(self, name: str, normalized_name: str = "") -> TagRow:
        loop = asyncio.get_running_loop()
        nn = normalized_name or name.lower().strip()
        return await loop.run_in_executor(None, self._sync_create, name, nn)

    async def get(self, tag_id: int) -> TagRow | None:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get, tag_id
        )

    async def get_by_name(self, normalized_name: str) -> TagRow | None:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_by_name, normalized_name
        )

    async def list_all(self) -> list[TagWithCount]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_list_all
        )

    async def search(self, query: str) -> list[TagRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_search, query
        )

    async def delete(self, tag_id: int) -> bool:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_delete, tag_id
        )

    async def add_to_entry(self, entry_id: int, tag_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_add_to_entry, entry_id, tag_id
        )

    async def remove_from_entry(self, entry_id: int, tag_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_remove_from_entry, entry_id, tag_id
        )

    async def set_entry_tags(self, entry_id: int, tag_ids: list[int]) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_set_entry_tags, entry_id, tag_ids
        )

    async def get_entry_tags(self, entry_id: int) -> list[EntryTagRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_entry_tags, entry_id
        )

    async def get_entries_by_tag(self, tag_id: int, limit: int = 50) -> list[int]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_entries_by_tag, tag_id, limit
        )

    async def batch_tag(
        self, entry_ids: list[int], tag_names: list[str]
    ) -> dict[str, int]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_batch_tag, entry_ids, tag_names
        )

    async def add_alias(self, alias: str, canonical_tag_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_add_alias, alias, canonical_tag_id
        )

    async def remove_alias(self, alias: str) -> bool:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_remove_alias, alias
        )

    async def list_aliases(self) -> list[TagAliasRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_list_aliases
        )

    async def get_alias_map(self) -> dict[str, str]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_alias_map
        )

    async def add_temp_tags(self, entry_id: int, tag_names: list[str]) -> list[TagRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_add_temp_tags, entry_id, tag_names
        )
