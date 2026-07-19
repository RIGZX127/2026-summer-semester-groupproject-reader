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

        流程：读取文件 → 解析 XML → 逐条查重添加 → 返回分类汇总。
        文件读取在 executor 中执行，避免阻塞事件循环。
        """
        loop = asyncio.get_running_loop()

        # 读取文件
        try:
            xml_str = await loop.run_in_executor(
                None, pathlib.Path(path).read_text, "utf-8"
            )
        except FileNotFoundError:
            raise ValueError(f"OPML 文件不存在：{path}")
        except OSError as exc:
            raise ValueError(f"无法读取 OPML 文件：{exc}")

        # 解析
        try:
            feeds = import_opml(xml_str)
        except ValueError as exc:
            raise ValueError(f"OPML 解析失败：{exc}") from exc

        if not feeds:
            raise ValueError("OPML 文件中未找到任何订阅源。")

        # 逐条导入
        result = ImportResult()
        for feed_url in feeds:
            try:
                await self._feed_store.add(feed_url.url, title=feed_url.title)
                result.success.append(feed_url)
            except Exception as exc:
                from store.feed_store import DuplicateFeedError
                if isinstance(exc, DuplicateFeedError):
                    result.skipped.append(feed_url)
                else:
                    result.failed.append((feed_url, str(exc)))

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
