"""CollectionStore 单元测试。使用内存数据库 fixture。"""
from __future__ import annotations

import pytest
from store.collection_store import CollectionStore
from store.db import DatabaseManager


@pytest.fixture
def store():
    db = DatabaseManager(":memory:")
    # 插入占位 entries 以满足 FK 约束
    conn = db.connection
    conn.execute("INSERT INTO feeds (id, url) VALUES (1, 'http://test.local/rss')")
    conn.execute(
        "INSERT INTO entries (id, feed_id, guid) VALUES (1, 1, 'guid-1'), (2, 1, 'guid-2'), "
        "(42, 1, 'guid-42'), (99, 1, 'guid-99')"
    )
    return CollectionStore(db)


@pytest.mark.asyncio
async def test_create_collection(store):
    col = await store.create("技术参考")
    assert col.id > 0
    assert col.name == "技术参考"
    assert col.is_default is False


@pytest.mark.asyncio
async def test_create_default_collection(store):
    col = await store.create("默认", is_default=True)
    assert col.is_default is True
    # 默认收藏夹唯一
    col2 = await store.get_default()
    assert col2.id == col.id


@pytest.mark.asyncio
async def test_second_default_replaces_first(store):
    col1 = await store.create("默认1", is_default=True)
    col2 = await store.create("默认2", is_default=True)
    # col1 不再是默认
    c1 = await store.get(col1.id)
    assert c1.is_default is False
    # col2 是默认
    d = await store.get_default()
    assert d.id == col2.id


@pytest.mark.asyncio
async def test_list_all_ordered(store):
    await store.create("C", sort_order=0)
    await store.create("A", sort_order=0)
    await store.create("B", sort_order=1)
    all_cols = await store.list_all()
    names = [c.name for c in all_cols]
    assert names == ["A", "C", "B"]  # sort_order 优先，同 order 按 name


@pytest.mark.asyncio
async def test_update_collection(store):
    col = await store.create("原始名")
    updated = await store.update(col.id, name="新名", description="描述")
    assert updated.name == "新名"
    assert updated.description == "描述"


@pytest.mark.asyncio
async def test_delete_collection(store):
    col = await store.create("待删")
    await store.delete(col.id)
    assert await store.get(col.id) is None


@pytest.mark.asyncio
async def test_add_entry_to_collection(store):
    col = await store.create("测试夹")
    await store.add_entry(col.id, 42)
    assert await store.is_in_collection(col.id, 42) is True


@pytest.mark.asyncio
async def test_add_entry_idempotent(store):
    col = await store.create("测试夹")
    await store.add_entry(col.id, 42)
    await store.add_entry(col.id, 42)  # no error
    entries = await store.get_entries(col.id)
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_remove_entry(store):
    col = await store.create("测试夹")
    await store.add_entry(col.id, 42)
    await store.remove_entry(col.id, 42)
    assert await store.is_in_collection(col.id, 42) is False


@pytest.mark.asyncio
async def test_get_collections_for_entry(store):
    col1 = await store.create("夹1")
    col2 = await store.create("夹2")
    await store.add_entry(col1.id, 99)
    await store.add_entry(col2.id, 99)
    result = await store.get_collections_for_entry(99)
    assert len(result) == 2
    assert {c.name for c in result} == {"夹1", "夹2"}


@pytest.mark.asyncio
async def test_quick_star_creates_default(store):
    col = await store.quick_star(42)
    assert col.is_default is True
    assert col.name == "默认收藏夹"
    assert await store.is_in_collection(col.id, 42) is True


@pytest.mark.asyncio
async def test_quick_star_uses_existing_default(store):
    existing = await store.create("我的默认", is_default=True)
    col = await store.quick_star(42)
    assert col.id == existing.id


@pytest.mark.asyncio
async def test_quick_unstar(store):
    col = await store.quick_star(42)
    await store.quick_unstar(42)
    assert await store.is_in_collection(col.id, 42) is False


@pytest.mark.asyncio
async def test_quick_unstar_no_default_no_error(store):
    await store.quick_unstar(42)  # 无默认夹不报错


@pytest.mark.asyncio
async def test_search_in_collection(store):
    col = await store.create("搜索测试")
    # entry_ids 预置即可，CollectionStore 只查关联，不管理 Entry 内容
    # 这里测试 SQL 正确拼接
    entries = await store.get_entries(col.id, search="Python")
    assert entries == []


@pytest.mark.asyncio
async def test_delete_collection_cascades_entries(store):
    col = await store.create("夹")
    await store.add_entry(col.id, 1)
    await store.add_entry(col.id, 2)
    await store.delete(col.id)
    # 关联应级联删除
    entries = await store.get_entries(col.id)
    assert entries == []
