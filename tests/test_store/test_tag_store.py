"""Tests for TagStore — tag CRUD, entry associations, aliases."""
from __future__ import annotations

import pytest

from store.tag_store import TagStore


@pytest.fixture
def tag_store(db) -> TagStore:
    _seed_entries(db)
    return TagStore(db)


def _seed_entries(db) -> None:
    """Insert minimal test data so FK constraints pass."""
    conn = db.connection
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO feeds (id, url, title) VALUES (1, 'http://test/feed', 'Test Feed')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO entries (id, feed_id, guid, title) VALUES "
            "(1, 1, 'guid-1', 'Entry 1'), (2, 1, 'guid-2', 'Entry 2'), (3, 1, 'guid-3', 'Entry 3')"
        )


class TestTagCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get(self, tag_store) -> None:
        tag = await tag_store.create("Python", "python")
        assert tag.id > 0
        assert tag.name == "Python"
        assert tag.normalized_name == "python"

        fetched = await tag_store.get(tag.id)
        assert fetched is not None
        assert fetched.name == "Python"

    @pytest.mark.asyncio
    async def test_create_duplicate_ignored(self, tag_store) -> None:
        t1 = await tag_store.create("Rust", "rust")
        t2 = await tag_store.create("Rust", "rust")
        assert t1.id == t2.id

    @pytest.mark.asyncio
    async def test_get_by_name(self, tag_store) -> None:
        await tag_store.create("AI", "ai")
        tag = await tag_store.get_by_name("ai")
        assert tag is not None
        assert tag.name == "AI"

    @pytest.mark.asyncio
    async def test_get_by_name_nonexistent(self, tag_store) -> None:
        tag = await tag_store.get_by_name("nonexistent")
        assert tag is None

    @pytest.mark.asyncio
    async def test_list_all(self, tag_store) -> None:
        await tag_store.create("Tag A", "tag a")
        await tag_store.create("Tag B", "tag b")
        tags = await tag_store.list_all()
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_search(self, tag_store) -> None:
        await tag_store.create("Python", "python")
        await tag_store.create("JavaScript", "javascript")
        results = await tag_store.search("py")
        assert len(results) == 1
        assert results[0].name == "Python"

    @pytest.mark.asyncio
    async def test_delete(self, tag_store) -> None:
        tag = await tag_store.create("Temp", "temp")
        deleted = await tag_store.delete(tag.id)
        assert deleted is True
        assert await tag_store.get(tag.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, tag_store) -> None:
        assert await tag_store.delete(999) is False


class TestEntryTags:
    @pytest.mark.asyncio
    async def test_add_and_get_entry_tags(self, tag_store) -> None:
        tag1 = await tag_store.create("Python", "python")
        tag2 = await tag_store.create("AI", "ai")

        await tag_store.add_to_entry(1, tag1.id)
        await tag_store.add_to_entry(1, tag2.id)

        tags = await tag_store.get_entry_tags(1)
        assert len(tags) == 2
        assert {t.tag_name for t in tags} == {"Python", "AI"}

    @pytest.mark.asyncio
    async def test_remove_from_entry(self, tag_store) -> None:
        tag = await tag_store.create("Rust", "rust")
        await tag_store.add_to_entry(1, tag.id)
        await tag_store.remove_from_entry(1, tag.id)
        tags = await tag_store.get_entry_tags(1)
        assert len(tags) == 0

    @pytest.mark.asyncio
    async def test_set_entry_tags_atomic(self, tag_store) -> None:
        t1 = await tag_store.create("A", "a")
        t2 = await tag_store.create("B", "b")
        t3 = await tag_store.create("C", "c")

        # Add initial tags
        await tag_store.add_to_entry(1, t1.id)
        await tag_store.add_to_entry(1, t2.id)

        # Replace with [t2, t3]
        await tag_store.set_entry_tags(1, [t2.id, t3.id])

        tags = await tag_store.get_entry_tags(1)
        assert {t.tag_id for t in tags} == {t2.id, t3.id}

    @pytest.mark.asyncio
    async def test_get_entries_by_tag(self, tag_store) -> None:
        tag = await tag_store.create("Shared", "shared")
        await tag_store.add_to_entry(1, tag.id)
        await tag_store.add_to_entry(2, tag.id)

        entries = await tag_store.get_entries_by_tag(tag.id)
        assert len(entries) == 2
        assert 1 in entries
        assert 2 in entries

    @pytest.mark.asyncio
    async def test_batch_tag(self, tag_store) -> None:
        results = await tag_store.batch_tag([1, 2], ["batch1", "batch2"])
        assert "batch1" in results
        assert "batch2" in results

        tags_1 = await tag_store.get_entry_tags(1)
        tags_2 = await tag_store.get_entry_tags(2)
        assert len(tags_1) == 2
        assert len(tags_2) == 2


class TestAliases:
    @pytest.mark.asyncio
    async def test_add_and_list_aliases(self, tag_store) -> None:
        tag = await tag_store.create("Machine Learning", "machine learning")
        await tag_store.add_alias("ml", tag.id)

        aliases = await tag_store.list_aliases()
        assert len(aliases) == 1
        assert aliases[0].alias == "ml"
        assert aliases[0].canonical_name == "Machine Learning"

    @pytest.mark.asyncio
    async def test_remove_alias(self, tag_store) -> None:
        tag = await tag_store.create("AI", "ai")
        await tag_store.add_alias("artificial intelligence", tag.id)
        await tag_store.remove_alias("artificial intelligence")

        aliases = await tag_store.list_aliases()
        assert len(aliases) == 0

    @pytest.mark.asyncio
    async def test_alias_map(self, tag_store) -> None:
        tag = await tag_store.create("JavaScript", "javascript")
        await tag_store.add_alias("js", tag.id)

        alias_map = await tag_store.get_alias_map()
        assert alias_map["js"] == "javascript"


class TestTempTags:
    @pytest.mark.asyncio
    async def test_add_temp_tags(self, tag_store) -> None:
        tags = await tag_store.add_temp_tags(1, ["temp1", "temp2"])
        assert len(tags) == 2

        entry_tags = await tag_store.get_entry_tags(1)
        assert len(entry_tags) == 2
