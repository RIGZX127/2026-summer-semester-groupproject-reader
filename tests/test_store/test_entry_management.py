# tests/test_store/test_entry_management.py
"""Phase 2.2 — EntryStore 文章管理扩展测试。"""
from __future__ import annotations

import pytest


async def _setup(db):
    """创建 feed + 3 篇文章（1 已读，2 未读），返回 (feed, entries)。"""
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    feed = await FeedStore(db).add("https://example.com/feed")
    es = EntryStore(db)
    e1 = await es.add(feed.id, "g1", None, "Python Tutorial", "Learn Python programming", "Alice", "2024-01-01T00:00:00Z")
    e2 = await es.add(feed.id, "g2", None, "JavaScript Basics", "JS for beginners", "Bob",   "2024-01-02T00:00:00Z")
    e3 = await es.add(feed.id, "g3", None, "Python Advanced",  "Advanced python topics", "Alice", "2024-01-03T00:00:00Z")
    # 让 e1 预先已读
    await es.mark_read(e1.id)
    return feed, es, [e1, e2, e3]


# ── mark_read / mark_unread ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_read_persists(db) -> None:
    _, es, entries = await _setup(db)
    e2 = entries[1]
    await es.mark_read(e2.id)
    row = await es.get(e2.id)
    assert row is not None and row.is_read is True


@pytest.mark.asyncio
async def test_mark_unread_persists(db) -> None:
    _, es, entries = await _setup(db)
    e1 = entries[0]  # 已在 _setup 中标记为已读
    await es.mark_unread(e1.id)
    row = await es.get(e1.id)
    assert row is not None and row.is_read is False


@pytest.mark.asyncio
async def test_mark_read_nonexistent_does_not_raise(db) -> None:
    from store.entry_store import EntryStore
    es = EntryStore(db)
    await es.mark_read(99999)  # 不存在，应静默忽略


@pytest.mark.asyncio
async def test_unread_count_decrements_after_mark_read(db) -> None:
    from store.feed_store import FeedStore
    feed, es, entries = await _setup(db)
    fs = FeedStore(db)
    before = await fs.unread_count(feed.id)
    await es.mark_read(entries[1].id)
    after = await fs.unread_count(feed.id)
    assert after == before - 1


# ── batch_mark_read ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_mark_read_returns_correct_count(db) -> None:
    _, es, entries = await _setup(db)
    # _setup 后有 2 篇未读 (e2, e3)
    count = await es.batch_mark_read(entries[0].feed_id)
    assert count == 2


@pytest.mark.asyncio
async def test_batch_mark_read_only_affects_target_feed(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    fs = FeedStore(db)
    feed1 = await fs.add("https://a.com/feed")
    feed2 = await fs.add("https://b.com/feed")
    es = EntryStore(db)
    await es.add(feed1.id, "f1g1", None, "A1", "s", "", None)
    await es.add(feed2.id, "f2g1", None, "B1", "s", "", None)
    await es.batch_mark_read(feed1.id)
    # feed2 的文章应仍未读
    assert await fs.unread_count(feed2.id) == 1


@pytest.mark.asyncio
async def test_batch_mark_read_excludes_deleted(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    feed = await FeedStore(db).add("https://example.com/feed2")
    es = EntryStore(db)
    e = await es.add(feed.id, "del-g1", None, "Del", "s", "", None)
    await es.soft_delete(e.id)
    count = await es.batch_mark_read(feed.id)
    assert count == 0  # 被软删除的不应被标记


@pytest.mark.asyncio
async def test_batch_mark_read_only_before_filter(db) -> None:
    _, es, entries = await _setup(db)
    # e2 published_at = 2024-01-02，e3 = 2024-01-03
    # 只标记 2024-01-02 之前（含当天）的
    count = await es.batch_mark_read(entries[0].feed_id, only_before="2024-01-02T23:59:59Z")
    assert count == 1  # 只有 e2 (2024-01-02) 符合


# ── toggle_star ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_toggle_star_false_to_true(db) -> None:
    _, es, entries = await _setup(db)
    e2 = entries[1]
    new_state = await es.toggle_star(e2.id)
    assert new_state is True
    row = await es.get(e2.id)
    assert row is not None and row.is_starred is True


@pytest.mark.asyncio
async def test_toggle_star_true_to_false(db) -> None:
    _, es, entries = await _setup(db)
    e2 = entries[1]
    await es.toggle_star(e2.id)   # False → True
    new_state = await es.toggle_star(e2.id)  # True → False
    assert new_state is False
    row = await es.get(e2.id)
    assert row is not None and row.is_starred is False


@pytest.mark.asyncio
async def test_toggle_star_nonexistent_returns_false(db) -> None:
    from store.entry_store import EntryStore
    result = await EntryStore(db).toggle_star(99999)
    assert result is False


# ── search ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_returns_matching_by_title(db) -> None:
    _, es, _ = await _setup(db)
    results = await es.search("Python")
    assert len(results) == 2
    titles = [r.title for r in results]
    assert "Python Tutorial" in titles
    assert "Python Advanced" in titles


@pytest.mark.asyncio
async def test_search_returns_matching_by_summary(db) -> None:
    _, es, _ = await _setup(db)
    results = await es.search("beginners")
    assert len(results) == 1
    assert results[0].title == "JavaScript Basics"


@pytest.mark.asyncio
async def test_search_case_insensitive(db) -> None:
    _, es, _ = await _setup(db)
    results_lower = await es.search("python")
    results_upper = await es.search("PYTHON")
    assert len(results_lower) == len(results_upper) == 2


@pytest.mark.asyncio
async def test_search_with_feed_id_scope(db) -> None:
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    fs = FeedStore(db)
    feed1 = await fs.add("https://a.com/feed")
    feed2 = await fs.add("https://b.com/feed")
    es = EntryStore(db)
    await es.add(feed1.id, "s1", None, "Python in feed1", "s", "", None)
    await es.add(feed2.id, "s2", None, "Python in feed2", "s", "", None)
    results = await es.search("Python", feed_id=feed1.id)
    assert len(results) == 1
    assert results[0].feed_id == feed1.id


@pytest.mark.asyncio
async def test_search_excludes_deleted(db) -> None:
    _, es, entries = await _setup(db)
    await es.soft_delete(entries[0].id)  # 软删除 "Python Tutorial"
    results = await es.search("Python")
    titles = [r.title for r in results]
    assert "Python Tutorial" not in titles
    assert "Python Advanced" in titles


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(db) -> None:
    feed, es, entries = await _setup(db)
    results = await es.search("", feed_id=feed.id)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_search_pagination(db) -> None:
    _, es, _ = await _setup(db)
    page1 = await es.search("", limit=2, offset=0)
    page2 = await es.search("", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 1


# ── soft_delete ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_hides_from_list_by_feed(db) -> None:
    feed, es, entries = await _setup(db)
    await es.soft_delete(entries[0].id)
    items = await es.list_by_feed(feed.id, limit=100)
    ids = [i.id for i in items]
    assert entries[0].id not in ids


@pytest.mark.asyncio
async def test_soft_delete_hides_from_search(db) -> None:
    _, es, entries = await _setup(db)
    await es.soft_delete(entries[0].id)
    results = await es.search("Python")
    ids = [r.id for r in results]
    assert entries[0].id not in ids


@pytest.mark.asyncio
async def test_soft_delete_entry_still_retrievable_by_get(db) -> None:
    _, es, entries = await _setup(db)
    await es.soft_delete(entries[0].id)
    row = await es.get(entries[0].id)
    assert row is not None
    assert row.is_deleted is True


@pytest.mark.asyncio
async def test_entry_list_item_has_is_read_and_starred(db) -> None:
    feed, es, _ = await _setup(db)
    items = await es.list_by_feed(feed.id, limit=10)
    for item in items:
        assert isinstance(item.is_read, bool)
        assert isinstance(item.is_starred, bool)
