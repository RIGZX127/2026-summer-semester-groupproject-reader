# core/feed/opml_controller.py
"""OPML 导入导出编排器。

将 OPML 解析/生成函数与 FeedStore 连接起来，
提供完整的导入去重汇总和导出流程。
"""
from __future__ import annotations

import asyncio
import pathlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.feed.opml import FeedUrl, export_opml, import_opml

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class ImportResult:
    """OPML 导入结果汇总。"""
    success: list[FeedUrl] = field(default_factory=list)
    skipped: list[FeedUrl] = field(default_factory=list)
    failed: list[tuple[FeedUrl, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.success) + len(self.skipped) + len(self.failed)


class OPMLController:
    """OPML 导入导出控制器。

    Usage:
        ctrl = OPMLController(db)
        result = await ctrl.import_feeds_from_opml("/path/to/feeds.opml")
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _feed_store(self):
        from store.feed_store import FeedStore
        if "_cache_feed_store" not in self.__dict__:
            self.__dict__["_cache_feed_store"] = FeedStore(self._db)
        return self.__dict__["_cache_feed_store"]

    async def import_feeds_from_opml(self, path: str) -> ImportResult:
        """从 OPML 文件导入订阅源。

        流程：读取文件 → 解析 XML → 单事务批量查重添加 → 返回分类汇总。
        所有新增操作在单个 SQLite 事务中完成，避免并行写入的线程竞争。
        """
        loop = asyncio.get_running_loop()

        # 读取文件
        try:
            xml_str = await loop.run_in_executor(
                None, pathlib.Path(path).read_text, "utf-8"
            )
        except FileNotFoundError:
            raise ValueError(f"OPML 文件不存在：{path}") from None
        except OSError as exc:
            raise ValueError(f"无法读取 OPML 文件：{exc}") from exc

        # 解析
        try:
            feeds = import_opml(xml_str)
        except ValueError as exc:
            raise ValueError(f"OPML 解析失败：{exc}") from exc

        if not feeds:
            raise ValueError("OPML 文件中未找到任何订阅源。")

        # 批量导入（单事务，INSERT OR IGNORE 去重）
        items = [(f.url, f.title) for f in feeds]
        try:
            added = await self._feed_store.add_many(items)
        except Exception as exc:
            raise ValueError(f"OPML 导入失败：{exc}") from exc

        # 分类汇总
        added_urls = {url for _, url, _ in added}
        result = ImportResult()
        for feed_url in feeds:
            if feed_url.url in added_urls:
                result.success.append(feed_url)
            else:
                result.skipped.append(feed_url)

        return result

    async def import_urls(
        self, items: list[tuple[str, str]]
    ) -> ImportResult:
        """直接导入 URL+标题列表（由对话框预解析后传入）。

        Returns:
            ImportResult 含 success / skipped / failed 分类。
        """
        result = ImportResult()
        try:
            added = await self._feed_store.add_many(items)
        except Exception as exc:
            # 全部失败
            for url, title in items:
                result.failed.append((FeedUrl(url=url, title=title), str(exc)))
            return result

        added_urls = {url for _, url, _ in added}
        for url, title in items:
            feed_url = FeedUrl(url=url, title=title)
            if url in added_urls:
                result.success.append(feed_url)
            else:
                result.skipped.append(feed_url)
        return result

    async def export_feeds_to_opml(self, path: str) -> str:
        """将所有订阅源导出为 OPML 文件。

        Returns:
            写入的绝对路径。
        """
        feeds = await self._feed_store.list_all()
        if not feeds:
            raise ValueError("没有可导出的订阅源。")

        xml_str = export_opml(feeds)

        loop = asyncio.get_running_loop()
        out_path = pathlib.Path(path).resolve()
        await loop.run_in_executor(None, out_path.write_text, xml_str, "utf-8")

        return str(out_path)
