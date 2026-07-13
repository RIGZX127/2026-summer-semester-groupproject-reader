# Mercury Phase 2.2 — 文章管理扩展 SPEC

> 文件：`spec/phase2-entry-management/SPEC.md`
> 对应 PLAN.md：里程碑 2.2 — 文章管理（已读/收藏/搜索/删除）
> 执行人：成员 A（核心架构师）
> 依赖前置：Phase 1 `store/entry_store.py` 基础版本（`add/get/list_by_feed/guid_exists`）已完成
> 输出给：成员 C（`entry_list.py` 的右键菜单、搜索栏、状态显示均需调用本模块新增方法）

---

## 1. 这个任务要解决什么问题

Phase 1 的 `EntryStore` 只能"存文章、查文章"，但用户实际需要：
- 把文章标记为已读（单篇 / 批量一键全读）
- 收藏某篇文章
- 搜索文章标题和摘要
- 删除不想要的文章（软删除，不真正从数据库移除）

这些操作的数据层全部由成员 A 在本里程碑实现，成员 C 只需调用接口更新 UI。

---

## 2. 文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `store/entry_store.py` | **扩展** | 新增 6 个 async 方法 + 扩展 `EntryListItem` dataclass |

---

## 3. EntryListItem 扩展

Phase 1 的 `EntryListItem` 只有基础字段，Phase 2.2 需要补全供 UI 使用的所有字段：

```python
@dataclass
class EntryListItem:
    id: int
    feed_id: int
    title: str
    summary_snippet: str    # 摘要前 120 字符，已在 Phase 1 实现
    author: str
    published_at: str | None   # ISO 8601，可为 None（Phase 1 可能已有）
    is_read: bool              # ← Phase 2.2 新增
    is_starred: bool           # ← Phase 2.2 新增
```

> ⚠️ **与成员 C 的约定**：`is_read` 和 `is_starred` 为 `bool`（不是 `int`），
> 由 `EntryStore` 在查询时转换（`bool(row["is_read"])`）。
> 成员 C 无需自行转换。

---

## 4. 新增方法规格

### 4.1 mark_read / mark_unread

```python
async def mark_read(self, entry_id: int) -> None:
    """将单篇文章标记为已读（is_read = 1）。"""

async def mark_unread(self, entry_id: int) -> None:
    """将单篇文章标记为未读（is_read = 0）。"""
```

- 均用 `run_in_executor` 包装
- `entry_id` 不存在时静默忽略（不抛异常）

---

### 4.2 batch_mark_read

```python
async def batch_mark_read(
    self,
    feed_id: int,
    only_before: str | None = None,
) -> int:
    """
    将 feed_id 下的所有未读且未删除文章标记为已读。
    only_before：若提供，仅标记 published_at <= only_before 的文章。
    返回：实际被标记的文章数量（int）。
    """
```

- 批量操作在单个 SQL `UPDATE` 中完成（不逐篇循环）
- 返回 `cursor.rowcount`
- 用 `run_in_executor` 包装

---

### 4.3 toggle_star

```python
async def toggle_star(self, entry_id: int) -> bool:
    """
    切换收藏状态：已收藏 → 取消收藏，未收藏 → 收藏。
    返回：操作后的新状态（True = 已收藏，False = 未收藏）。
    entry_id 不存在时返回 False（不抛异常）。
    """
```

- 先查当前 `is_starred` 值，再取反更新
- 两步操作在同一 `run_in_executor` 调用中完成（原子性）

---

### 4.4 search

```python
async def search(
    self,
    query: str,
    feed_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EntryListItem]:
    """
    在文章标题和摘要中搜索关键词（SQL LIKE，不区分大小写）。
    feed_id 为 None 时搜索全部订阅源；不为 None 时限定在该 Feed 内。
    自动排除 is_deleted=1 的文章。
    按 published_at DESC 排序。
    支持分页（limit + offset）。
    """
```

- SQL 实现：`WHERE (title LIKE ? OR summary LIKE ?) AND is_deleted = 0`
- 参数：`f"%{query}%"`（前后通配）
- `query` 为空字符串时，行为等同于 `list_by_feed()`（返回全部文章）
- Phase 2 中不使用 FTS 全文索引（PLAN.md 明确说明，Phase 2 仅 LIKE 搜索）

---

### 4.5 soft_delete

```python
async def soft_delete(self, entry_id: int) -> None:
    """
    软删除：将 is_deleted 设为 1。
    物理数据保留，所有查询方法默认排除 is_deleted=1 的文章。
    entry_id 不存在时静默忽略。
    """
```

---

## 5. 已有方法的确认（Phase 1 遗留，需检查）

以下方法在 Phase 1 已实现，Phase 2.2 只需确认其行为符合预期：

| 方法 | 期望行为 | 需要修改？ |
|------|---------|------------|
| `list_by_feed(feed_id, limit, offset)` | 返回包含 `is_read`、`is_starred` 的 `EntryListItem` | ⚠️ 可能需要在 SELECT 中补充这两个字段 |
| `get(entry_id)` | 返回完整 `EntryRow`，含 `is_read, is_starred, is_deleted` | 通常 Phase 1 已包含 |

> 如果 Phase 1 的 `list_by_feed` 的 `EntryListItem` 没有 `is_read` 和 `is_starred`，
> 在 Phase 2.2 开始时一并补充，属于扩展而非破坏性变更。

---

## 6. 测试规格

测试文件：`tests/test_store/test_entry_store.py`（扩展，在 Phase 1 文件中追加）

### 核心测试用例

| 测试名 | 验证内容 |
|--------|---------|
| `test_mark_read_persists` | `mark_read(id)` 后 `get(id).is_read == True` |
| `test_mark_unread_persists` | `mark_unread(id)` 后 `get(id).is_read == False` |
| `test_batch_mark_read_returns_count` | 5 篇未读 → `batch_mark_read()` 返回 5 |
| `test_batch_mark_read_only_affects_target_feed` | 两个 Feed，`batch_mark_read(feed_id=1)` 不影响 Feed 2 的文章 |
| `test_batch_mark_read_only_before_filters_correctly` | `only_before` 参数只标记该时间前的文章 |
| `test_toggle_star_true_to_false` | 已收藏 → `toggle_star()` 返回 `False`，数据库确认 |
| `test_toggle_star_false_to_true` | 未收藏 → `toggle_star()` 返回 `True`，数据库确认 |
| `test_search_returns_matching_entries` | 搜索 "Python"，只返回标题/摘要含 "python" 的文章（不区分大小写）|
| `test_search_with_feed_id_filters_scope` | `search("x", feed_id=1)` 不返回 Feed 2 的结果 |
| `test_search_excludes_deleted` | 软删除的文章不出现在搜索结果 |
| `test_search_empty_query_returns_all` | 空字符串搜索等价于 `list_by_feed()` |
| `test_soft_delete_hides_from_list` | `soft_delete(id)` 后 `list_by_feed()` 不含该文章 |
| `test_soft_delete_entry_still_in_db` | 软删除后 `get(id)` 仍能查到（`is_deleted=1`） |
| `test_entry_list_item_has_is_read_and_starred` | `list_by_feed()` 返回的 `EntryListItem` 含 `is_read` 和 `is_starred` |
| `test_unread_count_decrements_after_mark_read` | `mark_read` 后 `FeedStore.unread_count()` 减少 |

---

## 7. 与成员 C 的接口约定

**成员 A 保证（完成后通知 C）：**

```python
# 成员 C 需要的接口（全部 async）
entry_store.mark_read(entry_id)
entry_store.mark_unread(entry_id)
entry_store.batch_mark_read(feed_id, only_before=None)  # 返回 int
entry_store.toggle_star(entry_id)                       # 返回 bool（新状态）
entry_store.search(query, feed_id=None, limit=50, offset=0)  # 返回 list[EntryListItem]
entry_store.soft_delete(entry_id)

# EntryListItem 保证包含以下字段（bool 类型）
item.is_read    # bool
item.is_starred # bool
```

**成员 C 注意：**
- `batch_mark_read` 操作完成后，需要重新调用 `feed_store.unread_count(feed_id)` 刷新侧边栏角标
- `toggle_star` 返回新状态（`True/False`），UI 可直接用这个值更新图标，无需再次查数据库

---

## 8. 实际偏差记录（开发中填写）

> 开发完成后在此记录与本 SPEC 的实际偏差，供后续 Phase 参考。
