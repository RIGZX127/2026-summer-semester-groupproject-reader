# Mercury RSS Reader — Issue #5 需求 1/3/5 实现规范（0719 仓库）

**版本**: 1.0  
**日期**: 2026-07-19  
**目标仓库**: `2026-summer-semester-groupproject-reader-main0719/2026-summer-semester-groupproject-reader-main`  
**关联 Issue**: https://github.com/RIGZX127/2026-summer-semester-groupproject-reader/issues/5

## 0. 与 0718 改造版本的差异调查

0719 仓库相较上一版具有以下结构差异：

1. `app/app.py` 已注入更多 Phase 3 依赖：`TagStore`、`NoteStore`、`DigestController`、`OPMLController`。
2. `core/feed/opml_controller.py` 已存在，封装了 OPML 文件读写和 FeedStore 去重导入流程。
3. `ui/main_window.py` 已预留 `opml_controller` 成员，但尚未提供菜单入口和 QFileDialog 操作。
4. `EntryListWidget` 仍是单选/单篇右键操作，尚未提供多选批量工具条。
5. `SummaryPanel` 仍使用固定 CSS 行高，缺少行间距控制和折叠视觉优化。

因此本次不直接覆盖 0718 文件，而是在 0719 现有架构上做增量实现。

---

## 1. 需求 1：文章批量管理功能

### 1.1 目标

在文章列表中支持多选文章，并对选中文章批量执行：

- 标记为已读
- 标记为未读
- 批量软删除
- 取消选择

### 1.2 UI 设计

新增 `ui/bulk_action_bar.py`：

- `BulkActionBar` 组件，默认隐藏。
- 当选中文章数量 `>= 2` 时显示。
- 显示文本：`已选 N 篇`。
- 按钮：`全部已读`、`全部未读`、`批量删除`、`取消选择`。

### 1.3 EntryListWidget 改造

- `QListWidget` 启用 `ExtendedSelection`，支持 Ctrl/Shift 多选和 Ctrl+A。
- 新增信号：
  - `bulk_mark_read_requested = Signal(list)`
  - `bulk_mark_unread_requested = Signal(list)`
  - `bulk_delete_requested = Signal(list)`
- 新增方法：
  - `selected_entry_ids() -> list[int]`
  - `_on_selection_changed()`
  - `_emit_bulk_mark_read()` / `_emit_bulk_mark_unread()` / `_emit_bulk_delete()`

### 1.4 Store 改造

`EntryStore` 新增：

- `batch_mark_read_ids(entry_ids: list[int], value: int) -> int`
- `batch_soft_delete(entry_ids: list[int]) -> int`

不改数据库 schema，复用 `entries.is_read` 和 `entries.is_deleted`。

### 1.5 MainWindow 改造

新增：

- `bulk_mark_entries(entry_ids: list[int], read: bool)`
- `bulk_delete_entries(entry_ids: list[int])`
- `confirm_bulk_delete(count: int)`
- 对应 `@asyncSlot(list)` 信号槽

完成后刷新文章列表、订阅源未读计数，并在状态栏提示数量。

---

## 2. 需求 3：AI 摘要行间距调整及界面优化

### 2.1 目标

优化 `SummaryPanel` 视觉层级，并允许用户调整摘要文本行间距。

### 2.2 行间距档位

| 档位 | key | line-height |
|---|---|---|
| 紧凑 | `compact` | 1.4 |
| 标准 | `standard` | 1.7 |
| 宽松 | `loose` | 2.1 |

保存到 `QSettings`：`ui/summary_panel/line_height_preset`。

### 2.3 UI 改造

- Header 文案根据展开状态切换：`▶ AI 摘要` / `▼ AI 摘要`。
- Header 右侧增加行间距 `QComboBox`。
- 展开时显示水平分隔线 `SummarySeparator`。
- `_wrap_styles(html)` 改为按当前行间距生成 CSS。
- 摘要内容最小高度调整为 40px，内容区 spacing 缩小为 6。

---

## 3. 需求 5：OPML 文件导入、导出

### 3.1 现状

0719 已存在 `core/feed/opml_controller.py`，提供：

- `import_feeds_from_opml(path) -> ImportResult`
- `export_feeds_to_opml(path) -> str`

因此 UI 层只需补菜单入口和文件选择流程。

### 3.2 MainWindow 菜单

新增顶级菜单：`订阅`

- `导入 OPML…`：`Ctrl+Shift+I`
- `导出 OPML…`：`Ctrl+Shift+E`

### 3.3 导入流程

1. `QFileDialog.getOpenFileName` 选择 `.opml` / `.xml`。
2. 调用 `self._opml_controller.import_feeds_from_opml(path)`。
3. 导入完成后 `load_feeds()`。
4. 状态栏显示：新增、跳过、失败数量。
5. 异常时弹出 `QMessageBox.warning`。

### 3.4 导出流程

1. `QFileDialog.getSaveFileName` 选择保存路径。
2. 若用户未输入 `.opml` 后缀，自动补全。
3. 调用 `self._opml_controller.export_feeds_to_opml(path)`。
4. 状态栏显示保存位置。
5. 异常时弹出 `QMessageBox.warning`。

---

## 4. 变更文件清单

| 文件 | 操作 |
|---|---|
| `spec/SPEC_PHASE3_ISSUE5_0719.md` | 新增 spec 文档 |
| `ui/bulk_action_bar.py` | 新增批量操作工具条 |
| `ui/entry_list.py` | 增量改造多选和批量操作信号 |
| `store/entry_store.py` | 新增按 entry_id 列表批量更新方法 |
| `ui/main_window.py` | 新增订阅菜单、OPML UI 流程、批量操作逻辑 |
| `ui/reader/summary_panel.py` | 新增行间距控制和折叠视觉优化 |
| `ui/reader/reader_view.py` | 向 SummaryPanel 传递 QSettings |
| `app/styles.py` | 补充新增组件样式 |

---

## 5. 验收标准

- [ ] 可通过 Ctrl/Shift 多选文章，选中多篇时显示批量工具条。
- [ ] 批量已读/未读后列表和侧栏未读计数刷新。
- [ ] 批量删除前弹确认框，确认后选中文章从列表消失。
- [ ] 菜单栏出现 `订阅`，可导入/导出 OPML。
- [ ] OPML 导入重复源时不崩溃，并显示跳过数量。
- [ ] AI 摘要面板支持三档行间距，设置可跨文章保持。
- [ ] 所有修改的 Python 文件通过 `ast.parse` 语法检查。