# tests/test_store/test_feed_store.py
"""FeedStore 单元测试。"""
from __future__ import annotations

import pytest

from store.feed_store import DuplicateFeedError, FeedStore


@pytest.mark.asyncio
async def test_add_feed_persists_url_and_title(feed_store: FeedStore) -> None:
    feed = await feed_store.add("https://example.com/feed", title="Test Feed")
    assert feed.id > 0
    assert feed.url == "https://example.com/feed"
    assert feed.title == "Test Feed"


@pytest.mark.asyncio
async def test_add_duplicate_feed_raises_error(feed_store: FeedStore) -> None:
    await feed_store.add("https://example.com/feed")
    with pytest.raises(DuplicateFeedError):
        await feed_store.add("https://example.com/feed")


@pytest.mark.asyncio
async def test_get_feed_by_id(feed_store: FeedStore) -> None:
    created = await feed_store.add("https://example.com/feed", title="Hello")
    fetched = await feed_store.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Hello"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(feed_store: FeedStore) -> None:
    result = await feed_store.get(99999)
    assert result is None


@pytest.mark.asyncio
async def test_list_all_returns_all_feeds(feed_store: FeedStore) -> None:
    await feed_store.add("https://a.com/feed")
    await feed_store.add("https://b.com/feed")
    feeds = await feed_store.list_all()
    assert len(feeds) == 2


@pytest.mark.asyncio
async def test_update_feed_title(feed_store: FeedStore) -> None:
    feed = await feed_store.add("https://example.com/feed", title="Old")
    await feed_store.update(feed.id, title="New")
    updated = await feed_store.get(feed.id)
    assert updated.title == "New"


@pytest.mark.asyncio
async def test_delete_feed(feed_store: FeedStore) -> None:
    feed = await feed_store.add("https://example.com/feed")
    await feed_store.delete(feed.id)
    result = await feed_store.get(feed.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_feed_cascades_to_entries(
    feed_store: FeedStore, entry_store
) -> None:
    feed = await feed_store.add("https://example.com/feed")
    await entry_store.add(feed.id, "guid-1", title="Entry 1")
    await feed_store.delete(feed.id)
    entries = await entry_store.list_by_feed(feed.id)
    assert entries == []


@pytest.mark.asyncio
async def test_unread_count(feed_store: FeedStore, entry_store) -> None:
    feed = await feed_store.add("https://example.com/feed")
    await entry_store.add(feed.id, "guid-1")
    await entry_store.add(feed.id, "guid-2")
    count = await feed_store.unread_count(feed.id)
    assert count == 2