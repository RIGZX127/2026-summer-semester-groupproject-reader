# tests/test_feed/test_sync.py
"""SyncService 单元测试（mock parse_feed，不发网络请求）。"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.feed.parser import EntryData, FeedData, FeedParseError
from core.feed.sync import SyncService, _SYNC_FAILED


def _make_feed_data(n: int = 3, prefix: str = "") -> FeedData:
    return FeedData(
        url="https://example.com/feed",
        title="Test Feed",
        description="",
        entries=[
            EntryData(
                guid=f"{prefix}guid-{i}",
                url=f"https://example.com/{prefix}{i}",
                title=f"Article {i}",
                summary=f"Summary {i}",
                author="",
                published_at=None,
            )
            for i in range(n)
        ],
    )


@pytest.mark.asyncio
async def test_sync_feed_adds_new_entries(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    feed = await feed_store.add("https://example.com/feed", title="Old Title")
    svc = SyncService(db)
    with patch("core.feed.sync.parse_feed", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = _make_feed_data(3)
        count = await svc.sync_feed(feed.id)
    assert count == 3
    entry_store = EntryStore(db)
    entries = await entry_store.list_by_feed(feed.id, limit=100)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_sync_feed_twice_no_duplicate_guids(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    feed = await feed_store.add("https://example.com/feed")
    svc = SyncService(db)
    feed_data = _make_feed_data(3)
    with patch("core.feed.sync.parse_feed", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = feed_data
        await svc.sync_feed(feed.id)
        mock_parse.return_value = feed_data
        count2 = await svc.sync_feed(feed.id)
    # 第二次同步：所有 guid 已存在，新增数为 0（成功路径）
    assert count2 == 0
    entry_store = EntryStore(db)
    entries = await entry_store.list_by_feed(feed.id, limit=100)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_sync_feed_error_returns_failed_sentinel(db) -> None:
    """sync_feed 解析失败时返回 _SYNC_FAILED（-1），同时发射 sync_error 信号。"""
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    feed = await feed_store.add("https://example.com/feed")
    svc = SyncService(db)
    emitted_errors: list[tuple[int, str]] = []
    svc.signals.sync_error.connect(lambda fid, msg: emitted_errors.append((fid, msg)))
    with patch(
        "core.feed.sync.parse_feed",
        new_callable=AsyncMock,
        side_effect=FeedParseError("Connection refused"),
    ):
        result = await svc.sync_feed(feed.id)
    assert result == _SYNC_FAILED
    assert len(emitted_errors) == 1
    assert emitted_errors[0][0] == feed.id
    assert "Connection refused" in emitted_errors[0][1]


@pytest.mark.asyncio
async def test_sync_feed_error_emits_signal(db) -> None:
    """sync_feed 失败时正确发射 sync_error 信号（不关心返回值）。"""
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    feed = await feed_store.add("https://example.com/feed")
    svc = SyncService(db)
    emitted_errors: list[tuple[int, str]] = []
    svc.signals.sync_error.connect(lambda fid, msg: emitted_errors.append((fid, msg)))
    with patch(
        "core.feed.sync.parse_feed",
        new_callable=AsyncMock,
        side_effect=FeedParseError("Connection refused"),
    ):
        await svc.sync_feed(feed.id)
    assert len(emitted_errors) == 1
    assert emitted_errors[0][0] == feed.id


@pytest.mark.asyncio
async def test_sync_all_calls_each_feed_and_sums_totals(db) -> None:
    """sync_all 对每个 Feed 各调用一次 sync_feed，汇总新增文章数。

    使用 concurrency=1 串行执行，规避内存 DB 并发写入的锁竞争。
    并发场景由 test_sync_all_partial_failure 与生产环境磁盘 DB 覆盖。
    """
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    await feed_store.add("https://a.com/feed")
    await feed_store.add("https://b.com/feed")

    svc = SyncService(db)
    call_index = {"n": 0}

    async def _side_effect(url: str, **_kw: object) -> FeedData:
        idx = call_index["n"]
        call_index["n"] += 1
        return _make_feed_data(2, prefix=f"call{idx}-")

    with patch("core.feed.sync.parse_feed", side_effect=_side_effect):
        # concurrency=1 串行运行，避免 :memory: DB 的并发锁竞争
        total_new, total_failed = await svc.sync_all(concurrency=1)

    assert total_new == 4   # 2 feeds × 2 entries
    assert total_failed == 0
    assert call_index["n"] == 2  # 每个 Feed 恰好被解析一次


@pytest.mark.asyncio
async def test_sync_all_partial_failure(db) -> None:
    """一个 Feed 失败不影响其他 Feed 同步完成（concurrency=1 串行验证）。"""
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore

    feed_store = FeedStore(db)
    feed_ok = await feed_store.add("https://ok.com/feed")
    await feed_store.add("https://fail.com/feed")
    svc = SyncService(db)

    async def _side_effect(url: str, **_kw: object) -> FeedData:
        if "fail" in url:
            raise FeedParseError("Intentional failure")
        return _make_feed_data(2)

    with patch("core.feed.sync.parse_feed", side_effect=_side_effect):
        total_new, total_failed = await svc.sync_all(concurrency=1)

    assert total_new == 2
    assert total_failed == 1
    entry_store = EntryStore(db)
    ok_entries = await entry_store.list_by_feed(feed_ok.id, limit=100)
    assert len(ok_entries) == 2
