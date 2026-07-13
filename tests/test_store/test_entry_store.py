# tests/test_store/test_entry_store.py
"""EntryStore 单元测试。"""
from __future__ import annotations

import pytest

from store.entry_store import EntryStore


@pytest.mark.asyncio
async def test_add_entry_returns_correct_fields(
    feed_store, entry_store: EntryStore
) -> None:
    feed = await feed_store.add("https://example.com/feed")
    entry = await entry_store.add(
        feed.id,
        guid="guid-001",
        url="https://example.com/1",
        title="Hello World",
        summary="This is a summary",
        author="Alice",
    )
    assert entry.id > 0
    assert entry.feed_id == feed.id
    assert entry.guid == "guid-001"
    assert entry.title == "Hello World"
    assert entry.is_read is False
    assert entry.is_starred is False
    assert entry.is_deleted is False


@pytest.mark.asyncio
async def test_get_entry_by_id(feed_store, entry_store: EntryStore) -> None:
    feed = await feed_store.add("https://example.com/feed")
    created = await entry_store.add(feed.id, "guid-x", title="X")
    fetched = await entry_store.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_nonexistent_entry_returns_none(entry_store: EntryStore) -> None:
    result = await entry_store.get(99999)
    assert result is None


@pytest.mark.asyncio
async def test_list_by_feed_excludes_deleted(
    feed_store, entry_store: EntryStore
) -> None:
    feed = await feed_store.add("https://example.com/feed")
    await entry_store.add(feed.id, "guid-1", title="Visible")
    entry2 = await entry_store.add(feed.id, "guid-2", title="Hidden")
    # 直接 SQL 标记为删除（Phase 2 提供 soft_delete 接口前的测试辅助）
    entry_store._conn.execute(
        "UPDATE entries SET is_deleted = 1 WHERE id = ?", (entry2.id,)
    )
    entry_store._conn.commit()
    items = await entry_store.list_by_feed(feed.id)
    assert len(items) == 1
    assert items[0].title == "Visible"


@pytest.mark.asyncio
async def test_guid_exists_true_after_add(feed_store, entry_store: EntryStore) -> None:
    feed = await feed_store.add("https://example.com/feed")
    await entry_store.add(feed.id, "guid-abc")
    assert await entry_store.guid_exists(feed.id, "guid-abc") is True


@pytest.mark.asyncio
async def test_guid_exists_false_before_add(feed_store, entry_store: EntryStore) -> None:
    feed = await feed_store.add("https://example.com/feed")
    assert await entry_store.guid_exists(feed.id, "guid-xyz") is False


@pytest.mark.asyncio
async def test_summary_snippet_truncated_at_120(
    feed_store, entry_store: EntryStore
) -> None:
    feed = await feed_store.add("https://example.com/feed")
    long_summary = "A" * 200
    await entry_store.add(feed.id, "guid-long", summary=long_summary)
    items = await entry_store.list_by_feed(feed.id)
    assert len(items[0].summary_snippet) == 120


@pytest.mark.asyncio
async def test_list_by_feed_pagination(feed_store, entry_store: EntryStore) -> None:
    feed = await feed_store.add("https://example.com/feed")
    for i in range(10):
        await entry_store.add(feed.id, f"guid-{i}", title=f"Entry {i}")
    page1 = await entry_store.list_by_feed(feed.id, limit=5, offset=0)
    page2 = await entry_store.list_by_feed(feed.id, limit=5, offset=5)
    assert len(page1) == 5
    assert len(page2) == 5
    ids_p1 = {e.id for e in page1}
    ids_p2 = {e.id for e in page2}
    assert ids_p1.isdisjoint(ids_p2)