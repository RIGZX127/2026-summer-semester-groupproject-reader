# store/collection_store.py
"""CollectionStore：收藏夹数据访问层。

提供：
  - 收藏夹 CRUD（创建、查询、更新、删除）
  - 文章关联（添加、移除、查询、存在性检查）
  - 默认收藏夹管理
  - 一键收藏/取消到默认夹

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
class CollectionRow:
    id: int
    name: str
    description: str
    sort_order: int
    is_default: bool
    created_at: str
    updated_at: str


def _row_to_collection(row: sqlite3.Row) -> CollectionRow:
    return CollectionRow(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        sort_order=row["sort_order"],
        is_default=bool(row["is_default"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CollectionStore:
    """收藏夹数据访问层。

    Usage:
        store = CollectionStore(db)
        fav = await store.create("技术参考")
        await store.add_entry(fav.id, entry_id=42)
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ── Collection CRUD ────────────────────────────────────────────────

    def _sync_create(
        self, name: str, description: str = "", sort_order: int = 0, is_default: bool = False
    ) -> CollectionRow:
        if is_default:
            with self._conn:
                self._conn.execute(
                    "UPDATE collections SET is_default = 0, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')"
                )
        with self._conn:
            self._conn.execute(
                "INSERT INTO collections (name, description, sort_order, is_default) VALUES (?, ?, ?, ?)",
                (name, description, sort_order, int(is_default)),
            )
        row = self._conn.execute(
            "SELECT * FROM collections WHERE id = last_insert_rowid()"
        ).fetchone()
        if row is None:
            raise ValueError(f"Failed to create collection: {name}")
        return _row_to_collection(row)

    def _sync_get(self, collection_id: int) -> CollectionRow | None:
        row = self._conn.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        return _row_to_collection(row) if row else None

    def _sync_get_default(self) -> CollectionRow | None:
        row = self._conn.execute(
            "SELECT * FROM collections WHERE is_default = 1 LIMIT 1"
        ).fetchone()
        return _row_to_collection(row) if row else None

    def _sync_list_all(self) -> list[CollectionRow]:
        rows = self._conn.execute(
            "SELECT * FROM collections ORDER BY sort_order, name"
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def _sync_update(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        sort_order: int | None = None,
        is_default: bool | None = None,
    ) -> CollectionRow:
        existing = self._sync_get(collection_id)
        if existing is None:
            raise ValueError(f"Collection {collection_id} not found")

        new_name = name if name is not None else existing.name
        new_desc = description if description is not None else existing.description
        new_order = sort_order if sort_order is not None else existing.sort_order
        new_default = is_default if is_default is not None else existing.is_default

        if new_default and not existing.is_default:
            with self._conn:
                self._conn.execute(
                    "UPDATE collections SET is_default = 0, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')"
                )

        with self._conn:
            self._conn.execute(
                """UPDATE collections
                   SET name = ?, description = ?, sort_order = ?, is_default = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')
                   WHERE id = ?""",
                (new_name, new_desc, new_order, int(new_default), collection_id),
            )
        row = self._conn.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        return _row_to_collection(row)

    def _sync_delete(self, collection_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM collections WHERE id = ?", (collection_id,)
            )

    # ── Entry associations ──────────────────────────────────────────────

    def _sync_add_entry(self, collection_id: int, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO collection_entries (collection_id, entry_id) VALUES (?, ?)",
                (collection_id, entry_id),
            )

    def _sync_remove_entry(self, collection_id: int, entry_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM collection_entries WHERE collection_id = ? AND entry_id = ?",
                (collection_id, entry_id),
            )

    def _sync_get_entries(
        self,
        collection_id: int,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[int]:
        """返回收藏夹内文章 entry_id 列表，按添加时间倒序。"""
        if search:
            rows = self._conn.execute(
                """SELECT e.id FROM entries e
                   JOIN collection_entries ce ON e.id = ce.entry_id
                   WHERE ce.collection_id = ? AND e.is_deleted = 0
                     AND (e.title LIKE ? OR e.summary LIKE ?)
                   ORDER BY ce.added_at DESC LIMIT ? OFFSET ?""",
                (collection_id, f"%{search}%", f"%{search}%", limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT e.id FROM entries e
                   JOIN collection_entries ce ON e.id = ce.entry_id
                   WHERE ce.collection_id = ? AND e.is_deleted = 0
                   ORDER BY ce.added_at DESC LIMIT ? OFFSET ?""",
                (collection_id, limit, offset),
            ).fetchall()
        return [r[0] for r in rows]

    def _sync_get_collections_for_entry(self, entry_id: int) -> list[CollectionRow]:
        rows = self._conn.execute(
            """SELECT c.* FROM collections c
               JOIN collection_entries ce ON c.id = ce.collection_id
               WHERE ce.entry_id = ?
               ORDER BY c.sort_order, c.name""",
            (entry_id,),
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def _sync_is_in_collection(self, collection_id: int, entry_id: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM collection_entries WHERE collection_id = ? AND entry_id = ?",
            (collection_id, entry_id),
        ).fetchone()
        return row is not None

    # ── Quick star ──────────────────────────────────────────────────────

    def _sync_quick_star(self, entry_id: int) -> CollectionRow:
        """一键收藏到默认夹。无默认夹则自动创建"默认收藏夹"。"""
        default = self._sync_get_default()
        if default is None:
            default = self._sync_create("默认收藏夹", is_default=True)
        self._sync_add_entry(default.id, entry_id)
        return default

    def _sync_quick_unstar(self, entry_id: int) -> None:
        """从默认收藏夹移除文章。"""
        default = self._sync_get_default()
        if default is not None:
            self._sync_remove_entry(default.id, entry_id)

    # ── Async wrappers ──────────────────────────────────────────────────

    async def create(
        self, name: str, description: str = "", sort_order: int = 0, is_default: bool = False
    ) -> CollectionRow:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_create, name, description, sort_order, is_default
        )

    async def get(self, collection_id: int) -> CollectionRow | None:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get, collection_id
        )

    async def get_default(self) -> CollectionRow | None:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_default
        )

    async def list_all(self) -> list[CollectionRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_list_all
        )

    async def update(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        sort_order: int | None = None,
        is_default: bool | None = None,
    ) -> CollectionRow:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_update, collection_id, name, description, sort_order, is_default
        )

    async def delete(self, collection_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_delete, collection_id
        )

    async def add_entry(self, collection_id: int, entry_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_add_entry, collection_id, entry_id
        )

    async def remove_entry(self, collection_id: int, entry_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_remove_entry, collection_id, entry_id
        )

    async def get_entries(
        self,
        collection_id: int,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[int]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_entries, collection_id, search, limit, offset
        )

    async def get_collections_for_entry(self, entry_id: int) -> list[CollectionRow]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_collections_for_entry, entry_id
        )

    async def is_in_collection(self, collection_id: int, entry_id: int) -> bool:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_is_in_collection, collection_id, entry_id
        )

    async def quick_star(self, entry_id: int) -> CollectionRow:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_quick_star, entry_id
        )

    async def quick_unstar(self, entry_id: int) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_quick_unstar, entry_id
        )
