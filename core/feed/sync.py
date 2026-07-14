# core/feed/sync.py
"""SyncService：并发同步所有订阅源，发射 Qt 信号上报进度。

设计决策：
  - asyncio.Semaphore 控制并发上限（默认 5）。
  - asyncio.gather 并发执行所有 sync_feed，单个失败不中断其他任务。
  - sync_feed 返回 -1 表示本次同步失败（已发射 sync_error），>=0 表示新增数。
  - SyncSignals 使用 PySide6 Signal；若 PySide6 不可用（测试环境），
    回退到轻量级 _FallbackSignals（仅持有回调列表）。
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from core.feed.parser import FeedParseError, parse_feed
from store.entry_store import EntryStore
from store.feed_store import FeedStore

if TYPE_CHECKING:
    from store.db import DatabaseManager

_SYNC_FAILED = -1  # sync_feed 失败哨兵返回值

# ── 信号层：优先使用 PySide6，测试环境自动降级 ────────────────────────────

try:
    from PySide6.QtCore import QObject  # type: ignore[import]
    from PySide6.QtCore import Signal as QtSignal

    class SyncSignals(QObject):
        """Feed 同步进度信号集合（PySide6 实现）。"""
        sync_started = QtSignal(int)        # feed_id
        sync_finished = QtSignal(int, int)  # feed_id, new_count
        sync_error = QtSignal(int, str)     # feed_id, error_msg
        sync_all_done = QtSignal(int, int)  # total_new, total_failed

except Exception:  # noqa: BLE001

    class _CB:  # type: ignore[no-redef]
        """轻量级回调列表，模拟 Qt Signal 的 connect / emit 接口。"""
        def __init__(self) -> None:
            self._cbs: list = []

        def connect(self, fn) -> None:  # noqa: ANN001
            self._cbs.append(fn)

        def emit(self, *args) -> None:
            for fn in self._cbs:
                fn(*args)

    class SyncSignals:  # type: ignore[no-redef]
        """Feed 同步进度信号集合（测试用降级实现）。"""
        def __init__(self) -> None:
            self.sync_started = _CB()
            self.sync_finished = _CB()
            self.sync_error = _CB()
            self.sync_all_done = _CB()


class SyncService:
    """并发 Feed 同步服务。"""

    def __init__(self, db: DatabaseManager) -> None:
        self._feed_store = FeedStore(db)
        self._entry_store = EntryStore(db)
        self.signals = SyncSignals()

    async def sync_feed(self, feed_id: int) -> int:
        """同步单个订阅源。

        Returns:
            新增文章数（>=0），或 _SYNC_FAILED（-1）表示失败。
        """
        self.signals.sync_started.emit(feed_id)

        feed = await self._feed_store.get(feed_id)
        if feed is None:
            self.signals.sync_error.emit(feed_id, f"Feed {feed_id} not found")
            return _SYNC_FAILED

        try:
            feed_data = await parse_feed(feed.url)
        except FeedParseError as exc:
            self.signals.sync_error.emit(feed_id, str(exc))
            return _SYNC_FAILED

        new_count = 0
        for entry in feed_data.entries:
            if not await self._entry_store.guid_exists(feed_id, entry.guid):
                await self._entry_store.add(
                    feed_id=feed_id,
                    guid=entry.guid,
                    url=entry.url,
                    title=entry.title,
                    summary=entry.summary,
                    author=entry.author,
                    published_at=entry.published_at,
                )
                new_count += 1

        if feed_data.title and feed_data.title != feed.title:
            await self._feed_store.update(feed_id, title=feed_data.title)

        self.signals.sync_finished.emit(feed_id, new_count)
        return new_count

    async def sync_all(self, concurrency: int = 5) -> tuple[int, int]:
        """并发同步所有订阅源。

        Returns:
            (total_new, total_failed) 新增文章总数和失败的 Feed 数量。
        """
        feeds = await self._feed_store.list_all()
        sem = asyncio.Semaphore(concurrency)

        async def _guarded(feed_id: int) -> int:
            async with sem:
                return await self.sync_feed(feed_id)

        results = await asyncio.gather(
            *[_guarded(f.id) for f in feeds],
            return_exceptions=True,
        )

        total_new = 0
        total_failed = 0
        for result in results:
            if isinstance(result, Exception):
                # sync_feed 本身抛了未预期异常（不是 FeedParseError）
                total_failed += 1
            elif result == _SYNC_FAILED:
                # sync_feed 内部捕获了 FeedParseError，发射了 sync_error 后返回 -1
                total_failed += 1
            else:
                total_new += result

        self.signals.sync_all_done.emit(total_new, total_failed)
        return total_new, total_failed
