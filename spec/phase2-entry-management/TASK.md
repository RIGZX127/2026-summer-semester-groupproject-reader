# Mercury Phase 2.2 — 文章管理扩展 TASK

> 文件：`spec/phase2-entry-management/TASK.md`
> 执行人：成员 A（核心架构师）
> 状态说明：`[x]` 待完成 · `[x]` 已完成 · `[-]` 跳过/不适用
> **规则：每完成一个子任务，立即将 `[x]` 改为 `[x]`，并在行末记录完成时间。**

---

## 前置检查（开始前确认）

- [x] Phase 2.1 的 Reader 管线已完成（`content_store.py` 稳定）
- [x] `store/entry_store.py` Phase 1 版本的 4 个方法测试全绿
- [x] 确认 Phase 1 的 `EntryListItem` 是否已包含 `is_read` 和 `is_starred` 字段
  - [x] 若缺少：先补充这两个字段及对应的 SQL SELECT，再做后续任务

---

## T2.2.1 — EntryListItem 扩展

- [x] 在 `EntryListItem` dataclass 中补充 `is_read: bool` 字段（若 Phase 1 缺少）
- [x] 在 `EntryListItem` dataclass 中补充 `is_starred: bool` 字段（若 Phase 1 缺少）
- [x] 补充 `author: str` 字段（若 Phase 1 缺少）
- [x] 补充 `published_at: str | None` 字段（若 Phase 1 缺少）
- [x] 更新 `list_by_feed()` 的 SQL SELECT 语句包含上述字段
- [x] 更新 SQL 行到 `EntryListItem` 的映射函数（`bool(row["is_read"])`）

### 子验收节点 T2.2.1-AC
- [x] `test_entry_list_item_has_is_read_and_starred` 通过
- [x] 已有的 `test_list_by_feed_*` 测试仍然全部通过（非破坏性变更）

---

## T2.2.2 — mark_read / mark_unread

- [x] 实现 `async mark_read(self, entry_id: int) -> None`
  - [x] SQL：`UPDATE entries SET is_read = 1 WHERE id = ?`
  - [x] 用 `run_in_executor` 包装
  - [x] `entry_id` 不存在时静默忽略（rowcount == 0 不抛异常）
- [x] 实现 `async mark_unread(self, entry_id: int) -> None`
  - [x] SQL：`UPDATE entries SET is_read = 0 WHERE id = ?`
  - [x] 用 `run_in_executor` 包装

### 子验收节点 T2.2.2-AC
- [x] `test_mark_read_persists` 通过
- [x] `test_mark_unread_persists` 通过
- [x] `test_unread_count_decrements_after_mark_read` 通过（调 FeedStore.unread_count 验证）

---

## T2.2.3 — batch_mark_read

- [x] 实现 `async batch_mark_read(self, feed_id: int, only_before: str | None = None) -> int`
  - [x] 基础 SQL：`UPDATE entries SET is_read = 1 WHERE feed_id = ? AND is_deleted = 0 AND is_read = 0`
  - [x] `only_before` 不为 None 时追加 `AND published_at <= ?`
  - [x] 用 `with self._conn:` 事务 + `run_in_executor` 包装
  - [x] 返回 `cursor.rowcount`

### 子验收节点 T2.2.3-AC
- [x] `test_batch_mark_read_returns_correct_count` 通过（5 篇未读 → 返回 5）
- [x] `test_batch_mark_read_only_affects_target_feed` 通过
- [x] `test_batch_mark_read_excludes_deleted` 通过（软删除的文章不被标记）
- [x] `test_batch_mark_read_only_before_filters` 通过

---

## T2.2.4 — toggle_star

- [x] 实现 `async toggle_star(self, entry_id: int) -> bool`
  - [x] 先 `SELECT is_starred FROM entries WHERE id = ?` 取当前值
  - [x] `entry_id` 不存在时返回 `False`
  - [x] `UPDATE entries SET is_starred = ? WHERE id = ?`（new_value = 1 - current）
  - [x] 两步在同一 `run_in_executor` 的同步函数中完成
  - [x] 返回 `bool(new_value)`

### 子验收节点 T2.2.4-AC
- [x] `test_toggle_star_false_to_true` 通过
- [x] `test_toggle_star_true_to_false` 通过
- [x] `test_toggle_star_nonexistent_entry_returns_false` 通过

---

## T2.2.5 — search

- [x] 实现 `async search(self, query: str, feed_id: int | None = None, limit: int = 50, offset: int = 0) -> list[EntryListItem]`
  - [x] `query` 为空字符串时：直接走 `list_by_feed(feed_id, limit, offset)`（若 feed_id 不为 None）或返回全部文章
  - [x] `query` 非空时：`WHERE (title LIKE ? OR summary LIKE ?) AND is_deleted = 0`
  - [x] 参数值：`f"%{query}%"`（SQLite LIKE 不区分大小写，ASCII 范围内）
  - [x] `feed_id` 不为 None 时追加 `AND feed_id = ?`
  - [x] 按 `published_at DESC` 排序
  - [x] 支持 `limit` + `offset` 分页
  - [x] 用 `run_in_executor` 包装
  - [x] 结果映射到 `EntryListItem`（复用 `list_by_feed` 的映射函数）

### 子验收节点 T2.2.5-AC
- [x] `test_search_returns_matching_by_title` 通过
- [x] `test_search_returns_matching_by_summary` 通过
- [x] `test_search_case_insensitive` 通过（搜 "python" 找到 "Python"）
- [x] `test_search_with_feed_id_scope` 通过
- [x] `test_search_excludes_deleted` 通过
- [x] `test_search_empty_query_returns_all` 通过
- [x] `test_search_pagination` 通过（offset 正确跳过）

---

## T2.2.6 — soft_delete

- [x] 实现 `async soft_delete(self, entry_id: int) -> None`
  - [x] SQL：`UPDATE entries SET is_deleted = 1 WHERE id = ?`
  - [x] 用 `run_in_executor` 包装
  - [x] `entry_id` 不存在时静默忽略

### 子验收节点 T2.2.6-AC
- [x] `test_soft_delete_hides_from_list_by_feed` 通过
- [x] `test_soft_delete_hides_from_search` 通过
- [x] `test_soft_delete_entry_still_retrievable_by_get` 通过（`get(id)` 仍返回，`is_deleted=True`）

---

## T2.2.7 — 测试文件更新

- [x] 在 `tests/test_store/test_entry_store.py` 中追加 Phase 2.2 的所有测试用例（约 15 个）
- [x] 确认 Phase 1 的 10+ 个已有测试仍全部通过（无破坏性回归）
- [x] 在 `tests/conftest.py` 中确认 `entry_store` fixture 无需修改（复用即可）

---

## M2.2 里程碑整体验收

- [x] `pytest tests/test_store/test_entry_store.py -v` 全部通过（含 Phase 1 + Phase 2.2 用例，零失败）
- [x] `ruff check store/entry_store.py` 零问题
- [x] 通知成员 C：`EntryStore` 新增 6 个方法接口已稳定，可对接文章列表 UI
- [x] 更新 `INTERFACE.md`，在 EntryStore 章节补充 Phase 2.2 新增的 6 个方法说明

---

## Phase 2 成员 A 总验收（M2.1 + M2.2 全部完成后）

- [x] `pytest tests/test_reader/ tests/test_store/ -v` 全部通过（零失败）
- [x] `ruff check core/reader/ store/content_store.py store/entry_store.py` 零问题
- [x] `INTERFACE.md` 已更新，包含 Phase 2 全部新增接口
- [x] 提交 Git，message 格式：`feat(phase2): complete M2.1 reader pipeline + M2.2 entry management`
- [x] 在 spec 目录记录实际偏差（如有）

