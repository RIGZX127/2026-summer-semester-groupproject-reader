# core/digest/controller.py
"""DigestController：跨 Store 数据组装 + 导出编排。

将 DigestExporter 的纯渲染能力与 Store 数据查询连接起来，
UI 只需注入一个 Controller 即可完成完整的导出流程。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from core.digest.exporter import DigestExporter, EntryDigest, ExportResult

if TYPE_CHECKING:
    from store.db import DatabaseManager


class DigestController:
    """导出文章 Digest 的控制器。

    负责：
      - 从 EntryStore / ContentStore / NoteStore / TagStore 组装 EntryDigest
      - 委托 DigestExporter 进行模板渲染和文件写入
      - 对外暴露简洁的 async API

    Usage:
        ctrl = DigestController(db)
        result = await ctrl.export_single(entry_id, "/output/dir")
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── 懒加载 Store（避免循环导入）────────────────────────────────

    @property
    def _entry_store(self):
        from store.entry_store import EntryStore
        if "_cache_entry_store" not in self.__dict__:
            self.__dict__["_cache_entry_store"] = EntryStore(self._db)
        return self.__dict__["_cache_entry_store"]

    @property
    def _feed_store(self):
        from store.feed_store import FeedStore
        if "_cache_feed_store" not in self.__dict__:
            self.__dict__["_cache_feed_store"] = FeedStore(self._db)
        return self.__dict__["_cache_feed_store"]

    @property
    def _content_store(self):
        from store.content_store import ContentStore
        if "_cache_content_store" not in self.__dict__:
            self.__dict__["_cache_content_store"] = ContentStore(self._db)
        return self.__dict__["_cache_content_store"]

    @property
    def _note_store(self):
        from store.note_store import NoteStore
        if "_cache_note_store" not in self.__dict__:
            self.__dict__["_cache_note_store"] = NoteStore(self._db)
        return self.__dict__["_cache_note_store"]

    @property
    def _tag_store(self):
        from store.tag_store import TagStore
        if "_cache_tag_store" not in self.__dict__:
            self.__dict__["_cache_tag_store"] = TagStore(self._db)
        return self.__dict__["_cache_tag_store"]

    # ── 数据组装 ────────────────────────────────────────────────────

    async def build_digest(self, entry_id: int) -> EntryDigest:
        """从各 Store 收集数据，组装为单篇 EntryDigest。

        缺失的数据（无笔记、无缓存内容等）静默置空，不抛出异常。
        """
        entry = await self._entry_store.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id} not found")

        # 内容缓存（markdown）
        content_markdown = ""
        try:
            cached = await self._content_store.get_by_entry(entry_id)
            if cached and cached.markdown:
                content_markdown = cached.markdown
        except Exception:
            pass

        # 笔记
        notes = ""
        try:
            note = await self._note_store.get(entry_id)
            if note:
                notes = note.body
        except Exception:
            pass

        # 标签
        tags: list[str] = []
        try:
            entry_tags = await self._tag_store.get_entry_tags(entry_id)
            tags = [et.tag_name for et in entry_tags]
        except Exception:
            pass

        # Feed 标题
        feed_title = ""
        try:
            feed = await self._feed_store.get(entry.feed_id)
            if feed:
                feed_title = feed.title
        except Exception:
            pass

        return EntryDigest(
            entry_id=entry.id,
            title=entry.title,
            url=entry.url or "",
            author=entry.author or "",
            published_at=entry.published_at or "",
            feed_title=feed_title,
            summary=entry.summary or "",
            notes=notes,
            tags=tags,
            content_markdown=content_markdown,
        )

    async def build_digests(self, entry_ids: list[int]) -> list[EntryDigest]:
        """批量组装 EntryDigest（并发查询）。"""
        results = await asyncio.gather(
            *(self.build_digest(eid) for eid in entry_ids),
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, EntryDigest)]

    # ── 导出 ─────────────────────────────────────────────────────────

    async def export_single(
        self,
        entry_id: int,
        dest_dir: str | Path,
        template: str = "single.md.j2",
        filename: str | None = None,
    ) -> ExportResult:
        """单篇导出：组装 → 渲染 → 写入。"""
        digest = await self.build_digest(entry_id)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            DigestExporter.export_single,
            digest,
            dest_dir,
            template,
            filename,
        )

    async def export_multi(
        self,
        entry_ids: list[int],
        dest_dir: str | Path,
        template: str = "multi.md.j2",
        filename: str | None = None,
    ) -> ExportResult:
        """多篇合并导出：批量组装 → 渲染 → 写入。"""
        digests = await self.build_digests(entry_ids)
        if not digests:
            return ExportResult(ok=False, error="没有可导出的文章")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            DigestExporter.export_multi,
            digests,
            dest_dir,
            template,
            filename,
        )

    async def preview(
        self,
        entry_id: int,
        template: str = "single.md.j2",
        max_chars: int = 500,
    ) -> str:
        """预览导出内容（不写文件）。"""
        digest = await self.build_digest(entry_id)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            DigestExporter.preview,
            digest,
            template,
            max_chars,
        )

    @staticmethod
    def list_templates() -> list[str]:
        """返回可用模板列表。"""
        return DigestExporter.list_templates()
