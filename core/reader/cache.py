# core/reader/cache.py
"""Reader 管线缓存层：版本号匹配逻辑。

检查 content 表中缓存是否与当前算法版本一致；
一致则命中，否则返回 None 触发重新抓取。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from store.content_store import ContentRow, ContentStore

if TYPE_CHECKING:
    from store.db import DatabaseManager


class ReaderCache:
    def __init__(self, db: DatabaseManager) -> None:
        self._store = ContentStore(db)

    async def get(
        self,
        entry_id: int,
        reader_version: int,
        markdown_version: int,
    ) -> ContentRow | None:
        """精确匹配版本号。任意不一致返回 None（缓存失效）。"""
        row = await self._store.get_by_entry(entry_id)
        if row is None:
            return None
        if row.reader_version == reader_version and row.markdown_version == markdown_version:
            return row
        return None

    async def save(
        self,
        entry_id: int,
        source_html: str,
        cleaned_html: str,
        markdown: str,
        reader_version: int,
        markdown_version: int,
        render_version: int,
    ) -> ContentRow:
        """写入或覆盖缓存记录。"""
        return await self._store.upsert(
            entry_id=entry_id,
            source_html=source_html,
            cleaned_html=cleaned_html,
            markdown=markdown,
            reader_version=reader_version,
            markdown_version=markdown_version,
            render_version=render_version,
        )
