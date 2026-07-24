# 收藏夹与笔记 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 `CollectionStore` 和 `NoteStore` 完整接入 Mercury 三栏 UI。

**Architecture:** 新增独立的 `CollectionsWidget` 和 `NoteEditor`，组件只发出用户意图；`MainWindow` 负责调用异步 Store 并把结果回写组件。ReaderView 只负责承载“AI 摘要 / 笔记”标签页和暴露笔记组件，不直接访问 Store。

**Tech Stack:** Python 3.11+、PySide6 6.5+、qasync、pytest、pytest-qt、ruff

## Global Constraints

- 只修改 `ui/`、UI 测试和本设计文档，不修改 Store、Core 或数据库迁移。
- 用户可见字符串通过 `self.tr()`，代码注释和 docstring 使用英文。
- 自定义信号使用 `PySide6.QtCore.Signal`。
- 图标按钮必须有 Tooltip 和可访问名称。
- 数据库调用留在 MainWindow 接线层，组件不得执行 SQL。

---

### Task 1: 收藏夹导航组件

**Files:**
- Create: `ui/collections_widget.py`
- Modify: `ui/sidebar.py`
- Test: `tests/test_ui/test_collections_notes_ui.py`

**Interfaces:**
- Consumes: `CollectionRow`
- Produces: `collection_selected(int)`、`create_requested(str)`、`rename_requested(int, str)`、`delete_requested(int)` 与 `set_collections(list[CollectionRow])`

- [ ] **Step 1: Write the failing test**

```python
def test_collections_widget_lists_rows_and_emits_selection(qtbot):
    widget = CollectionsWidget()
    widget.set_collections([_collection(3, "课程资料")])
    with qtbot.waitSignal(widget.collection_selected) as signal:
        widget.collection_list.setCurrentRow(0)
    assert signal.args == [3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: FAIL because `ui.collections_widget` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a widget with a heading, compact add button, list, and rename/delete context menu. Embed it below `Sidebar.feed_list` and expose it as `sidebar.collections`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: collection component tests PASS.

### Task 2: 文章菜单与收藏夹接线

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `ui/main_window.py`
- Test: `tests/test_ui/test_collections_notes_ui.py`

**Interfaces:**
- Consumes: `CollectionStore.list_all()`、`get_entries()`、`add_entry()`、`create()`、`update()`、`delete()`、`quick_star()`、`quick_unstar()`；`EntryStore.get(int)`
- Produces: `EntryListWidget.add_to_collection_requested(int)`；MainWindow 收藏夹加载、筛选和管理方法

- [ ] **Step 1: Write failing tests**

```python
def test_entry_context_action_emits_add_to_collection(qtbot):
    view = EntryListWidget()
    view.set_entries([_entry(1)])
    with qtbot.waitSignal(view.add_to_collection_requested) as signal:
        view._emit_add_to_collection_for_item(view.entry_list.item(0))
    assert signal.args == [1]

def test_main_window_loads_collection_entries(tmp_path, qtbot):
    window = _window_with_feature_stores(tmp_path, qtbot)
    asyncio.run(window.load_collections())
    asyncio.run(window.select_collection(7))
    assert window._collection_store.entry_queries == [7]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: FAIL because the signal and MainWindow methods are missing.

- [ ] **Step 3: Write minimal implementation**

Add the article context action and connect all collection signals in MainWindow. Resolve collection entry IDs with `CollectionStore.get_entries()`, fetch rows through `EntryStore.get()`, and pass `EntryListItem` values to the existing list.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: collection integration tests PASS.

### Task 3: 笔记编辑器与 5 秒自动保存

**Files:**
- Create: `ui/reader/note_editor.py`
- Modify: `ui/reader/reader_view.py`
- Test: `tests/test_ui/test_collections_notes_ui.py`

**Interfaces:**
- Produces: `save_requested(int, str)`、`set_entry(int | None, str)`、`set_save_state(str)`

- [ ] **Step 1: Write failing tests**

```python
def test_note_editor_emits_save_after_five_seconds(qtbot):
    editor = NoteEditor()
    editor.set_entry(9, "")
    with qtbot.waitSignal(editor.save_requested, timeout=5500) as signal:
        editor.text_edit.setPlainText("重点")
    assert signal.args == [9, "重点"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: FAIL because `NoteEditor` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a plain-text Markdown editor with a single-shot 5000 ms timer and save-status label. Replace the Reader lower panel with a `QTabWidget` containing the existing summary panel and new editor.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: note component tests PASS.

### Task 4: 笔记 Store 接线与最终验证

**Files:**
- Modify: `ui/main_window.py`
- Test: `tests/test_ui/test_collections_notes_ui.py`

**Interfaces:**
- Consumes: `NoteStore.get(int)`、`save(int, str)`
- Produces: `load_note(int)`、`save_note(int, str)` with stale-entry protection

- [ ] **Step 1: Write failing integration tests**

```python
def test_select_entry_loads_note_and_save_updates_store(tmp_path, qtbot):
    window = _window_with_feature_stores(tmp_path, qtbot)
    asyncio.run(window.select_entry(5))
    assert window.reader_view.note_editor.text_edit.toPlainText() == "已有笔记"
    asyncio.run(window.save_note(5, "更新"))
    assert window._note_store.saved == [(5, "更新")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui/test_collections_notes_ui.py -v`
Expected: FAIL because note Store wiring is missing.

- [ ] **Step 3: Write minimal implementation**

Load notes after the selected entry is validated, connect `save_requested` to an async slot, discard stale loads, and flush dirty notes during entry switches and window close.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
pytest tests/test_ui/test_collections_notes_ui.py -v
pytest tests/test_ui -v
pytest tests/test_store -v
ruff check ui tests/test_ui
```

Expected: all newly added tests pass; pre-existing environment or migration failures, if any, are reported separately with exact output.
