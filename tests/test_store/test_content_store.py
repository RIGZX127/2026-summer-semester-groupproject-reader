# tests/test_store/test_content_store.py
"""ContentStore 单元测试。"""
from __future__ import annotations

import pytest

from store.content_store import ContentStore


@pytest.mark.asyncio
async def test_content_store_upsert_creates_row(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-1", None, "Title", "Summary", "", None)
    store = ContentStore(db)
    row = await store.upsert(entry.id, "<html/>", "<p>clean</p>", "# clean", 1, 1, 1)
    assert row.entry_id == entry.id
    assert row.markdown == "# clean"
    assert row.reader_version == 1
    assert row.fetched_at is not None


@pytest.mark.asyncio
async def test_content_store_upsert_overwrites_existing(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-2", None, "Title", "Summary", "", None)
    store = ContentStore(db)
    await store.upsert(entry.id, "<html/>", "<p>v1</p>", "# v1", 1, 1, 1)
    await store.upsert(entry.id, "<html/>", "<p>v2</p>", "# v2", 2, 1, 1)
    row = await store.get_by_entry(entry.id)
    assert row is not None
    assert row.markdown == "# v2"
    assert row.reader_version == 2
    # 确认只有一行（无重复）
    count = db.connection.execute(
        "SELECT COUNT(*) FROM content WHERE entry_id = ?", (entry.id,)
    ).fetchone()[0]
    assert count == 1


@pytest.mark.asyncio
async def test_content_store_get_returns_none_for_missing(db) -> None:
    store = ContentStore(db)
    result = await store.get_by_entry(99999)
    assert result is None


@pytest.mark.asyncio
async def test_content_store_delete_removes_row(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-3", None, "Title", "Summary", "", None)
    store = ContentStore(db)
    await store.upsert(entry.id, None, None, "# test", 1, 1, 1)
    await store.delete_by_entry(entry.id)
    result = await store.get_by_entry(entry.id)
    assert result is None
