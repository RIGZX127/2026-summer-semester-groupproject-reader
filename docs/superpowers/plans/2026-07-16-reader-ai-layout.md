# Mercury Reader AI 与自适应布局实施计划

> **Superseded for the current user-authorized scope.** 本计划包含 Core/Store 扩展，不执行。当前只执行 `docs/superpowers/plans/2026-07-16-reader-ui-only.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在成员 Phase 1/2 UI 基线上交付三栏/双栏/沉浸阅读、可用宽度充足的 Reader 原文对照，以及包含摘要、翻译和本地正文清洗的可折叠 AI 助手。

**Architecture:** 从成员压缩包只恢复 UI 与 UI 测试，从“近黑石墨蓝双主题”包恢复完整语义主题链，不覆盖当前分支已合入的 Core/Store。外层布局由独立 `LayoutController` 管理，Agent UI 通过 `ReaderAgentController` 消费共享 `AgentRuntime`，Reader 清洗通过带阶段事件的 `ReaderRefreshUseCase` 运行；View 只发射意图并展示事件。

**Tech Stack:** Python 3.11+、PySide6 6.5+、QWebEngineView、qasync、pytest、pytest-qt、pytest-asyncio、ruff。

## Global Constraints

- 仅使用 PySide6 `Signal`；Qt UI 只能在主线程更新。
- UI 不直接执行 SQL、HTTP、Reader 提取、缓存删除或 LLM 调用。
- Agent 事件更新前同时校验 `entry_id` 与 `run_id`；Reader 事件校验 `entry_id` 与 `request_id`。
- 正在运行的 Agent 只能由用户明确取消；切换文章仅废弃防抖定时器和忽略过期事件。
- 用户可见字符串默认中文并通过 `self.tr()` 或 `QCoreApplication.translate()` 创建。
- 主题偏好只允许 `system`、`light`、`dark`；组件不得自建局部色板。
- 控件采用 8 px 圆角、面板采用 12 px 圆角，图标按钮点击目标至少 36×36 px。
- 浅色使用暖现代语义色板；深色使用近黑石墨蓝语义色板。
- 测试不访问真实网络、真实数据库文件或 LLM，不使用 `time.sleep()`。
- 不引入 ORM、`requests` 或 `unittest.TestCase`。

---

## 文件结构

### 从成员交付恢复

- `app/styles.py`：全局语义 QSS。
- `ui/theme.py`：浅色/深色 `Palette`。
- `ui/theme_controller.py`：全局主题偏好与应用。
- `ui/sidebar.py`：订阅源导航。
- `ui/entry_list.py`：文章列表与页面状态。
- `ui/dialogs/add_feed_dialog.py`：添加订阅对话框。
- `ui/reader/theme.py`：Reader 字号与内容宽度值对象。
- `ui/reader/theme_manager.py`：Reader CSS 与偏好。
- `ui/reader/reader_toolbar.py`：阅读、布局、AI 与翻译显示控制。
- `ui/reader/reader_view.py`：Reader/Web/对照内容容器。
- `ui/main_window.py`：主窗口业务编排。

### 新建职责单一的组件

- `ui/layout_controller.py`：应用三种布局、尺寸持久化与 Reader 对照临时扩宽。
- `ui/reader/agent_controller.py`：共享 AgentRuntime 的 UI 桥接、过期事件过滤与自动摘要防抖。
- `ui/reader/summary_panel.py`：摘要展示与意图。
- `ui/reader/translation_panel.py`：翻译状态、进度与意图。
- `ui/reader/cleaning_panel.py`：本地 Reader 四阶段展示与重新清洗意图。
- `ui/reader/ai_assistant_panel.py`：三个页签与抽屉状态。
- `core/reader/events.py`：Reader 阶段事件 dataclass。
- `core/reader/use_cases.py`：重新清洗的缓存失效与管线执行。
- `app/services.py`：数据库、Reader、Runtime 与 Agent 的组合根。

### 测试

- `tests/test_ui/test_app_theme.py`
- `tests/test_ui/test_add_feed_dialog.py`
- `tests/test_ui/test_components.py`
- `tests/test_ui/test_main_window.py`
- `tests/test_ui/test_layout_controller.py`
- `tests/test_ui/test_reader_toolbar.py`
- `tests/test_ui/test_reader_view.py`
- `tests/test_ui/test_ai_assistant.py`
- `tests/test_ui/test_agent_controller.py`
- `tests/test_ui/test_cleaning_panel.py`
- `tests/test_reader/test_reader_events.py`
- `tests/test_reader/test_refresh_use_case.py`
- `tests/test_agent/test_translation.py`
- `tests/test_app/test_services.py`

---

### Task 1: 恢复可运行的成员 UI 与双主题基线

**Files:**
- Create: `app/styles.py`
- Create: `ui/theme.py`
- Create: `ui/theme_controller.py`
- Create: `ui/sidebar.py`
- Create: `ui/entry_list.py`
- Create: `ui/dialogs/add_feed_dialog.py`
- Create: `ui/reader/theme.py`
- Create: `ui/reader/theme_manager.py`
- Create: `ui/reader/reader_toolbar.py`
- Create: `ui/reader/reader_view.py`
- Create: `ui/main_window.py`
- Create: `tests/test_ui/test_app_theme.py`
- Create: `tests/test_ui/conftest.py`
- Create: `tests/test_ui/test_add_feed_dialog.py`
- Create: `tests/test_ui/test_components.py`
- Create: `tests/test_ui/test_main_window.py`
- Create: `tests/test_ui/test_reader_toolbar.py`
- Create: `tests/test_ui/test_reader_view.py`
- Create: `tests/test_ui/test_styles.py`
- Modify: `app/app.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: 当前分支 `FeedStore`、`EntryStore`、`SyncService`、`ReaderPipeline`。
- Produces: 可构造的 `MainWindow(feed_store, entry_store, sync_service, settings, reader_pipeline)` 与全局 `ThemeController`。

- [ ] **Step 1: 写基线导入与主题失败测试**

```python
# tests/test_ui/test_app_theme.py
from PySide6.QtCore import QSettings
from ui.theme import DARK_PALETTE, LIGHT_PALETTE
from ui.theme_controller import ThemeController


def test_theme_defaults_to_system_and_uses_semantic_palettes(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "theme.ini"), QSettings.Format.IniFormat)
    controller = ThemeController(settings, system_theme_reader=lambda: "dark")
    assert controller.preference == "system"
    assert controller.palette == DARK_PALETTE
    controller.set_preference("light")
    assert controller.palette == LIGHT_PALETTE
```

```python
# tests/test_ui/test_main_window.py
def test_main_window_has_member_three_column_baseline(main_window) -> None:
    assert main_window.splitter.count() == 3
    assert main_window.sidebar.objectName() == "Sidebar"
    assert main_window.reader_view.toolbar.reader_button.isChecked()
```

`tests/test_ui/conftest.py` 提供后续任务共用的无 I/O fixture：

```python
import pytest
from PySide6.QtCore import QSettings
from core.feed.sync import SyncSignals
from ui.main_window import MainWindow
from ui.reader.reader_view import ReaderView


class FakeFeedStore:
    async def list_all(self):
        return []

    async def unread_count(self, _feed_id: int) -> int:
        return 0


class FakeEntryStore:
    async def list_by_feed(self, _feed_id: int, limit: int = 50, offset: int = 0):
        return []

    async def get(self, _entry_id: int):
        return None


class FakeSyncService:
    def __init__(self) -> None:
        self.signals = SyncSignals()

    async def sync_feed(self, _feed_id: int) -> int:
        return 0


@pytest.fixture
def reader_view(tmp_path, qtbot):
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    view = ReaderView(settings=settings)
    qtbot.addWidget(view)
    return view


@pytest.fixture
def main_window(tmp_path, qtbot):
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    window = MainWindow(FakeFeedStore(), FakeEntryStore(), FakeSyncService(), settings)
    qtbot.addWidget(window)
    return window
```

- [ ] **Step 2: 运行测试并确认缺失模块失败**

Run: `pytest tests/test_ui/test_app_theme.py tests/test_ui/test_main_window.py -q`

Expected: collection FAIL，提示 `ui.theme` 或 `ui.main_window` 不存在。

- [ ] **Step 3: 选择性恢复成员文件，不覆盖 Core/Store**

以 `Mercury-UI-近黑石墨蓝双主题.zip` 为视觉与主题来源，恢复其 `app/styles.py`、`ui/theme.py`、`ui/theme_controller.py`、`ui/reader/*`；以 `2026-summer-semester-groupproject-reader-main (2).zip` 为三栏业务与 UI 测试来源，恢复 `ui/main_window.py`、`ui/sidebar.py`、`ui/entry_list.py`、`ui/dialogs/add_feed_dialog.py` 和测试。

恢复时保留这些确定接口：

```python
class ThemeController(QObject):
    theme_changed = Signal(str)
    SETTINGS_KEY = "ui/theme_preference"


class ReaderView(QWidget):
    retry_requested = Signal()
    VALID_MODES = frozenset({"reader", "web", "split"})


class MainWindow(QMainWindow):
    def __init__(
        self,
        feed_store: FeedStore,
        entry_store: EntryStore,
        sync_service: SyncService,
        settings: QSettings | None = None,
        reader_pipeline: ReaderPipeline | None = None,
    ) -> None:
        super().__init__()
```

不得整包解压到仓库；逐文件应用补丁，避免覆盖当前 `core/agent/`、`core/reader/`、`store/` 与已有文档。

- [ ] **Step 4: 修复组合根与缺失依赖**

`app/app.py` 必须构造真实窗口：

```python
window = MainWindow(
    feed_store=FeedStore(state.db),
    entry_store=EntryStore(state.db),
    sync_service=SyncService(state.db),
    reader_pipeline=ReaderPipeline(state.db),
)
```

在 `pyproject.toml` 的运行依赖中加入模板加载器实际使用的：

```toml
"PyYAML>=6.0",
```

- [ ] **Step 5: 运行基线 UI 与完整回归**

Run: `pytest tests/test_ui/test_app_theme.py tests/test_ui/test_add_feed_dialog.py tests/test_ui/test_components.py tests/test_ui/test_main_window.py tests/test_ui/test_reader_toolbar.py tests/test_ui/test_reader_view.py -q`

Expected: PASS；测试不打开网络页面或真实数据库文件。

Run: `pytest -q`

Expected: 当前完整套件 PASS。

- [ ] **Step 6: 提交基线**

```powershell
git add app/app.py app/styles.py pyproject.toml ui tests/test_ui
git commit -m "feat(ui): restore member reader interface baseline"
```

---

### Task 2: 实现应用三种布局状态与尺寸持久化

**Files:**
- Create: `ui/layout_controller.py`
- Create: `tests/test_ui/test_layout_controller.py`

**Interfaces:**
- Consumes: 外层 `QSplitter`、Sidebar、EntryList、ReaderView 与 `QSettings`。
- Produces: `LayoutController.layout`, `set_layout(value, user_initiated=True)`, `save()`, `layout_changed = Signal(str)`。

- [ ] **Step 1: 写三种布局与持久化失败测试**

```python
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QSplitter, QWidget
from ui.layout_controller import LayoutController


def test_layout_controller_switches_three_two_and_immersive(tmp_path, qtbot) -> None:
    splitter = QSplitter()
    sidebar, entries, reader = QWidget(), QWidget(), QWidget()
    for widget in (sidebar, entries, reader):
        splitter.addWidget(widget)
    settings = QSettings(str(tmp_path / "layout.ini"), QSettings.Format.IniFormat)
    controller = LayoutController(splitter, sidebar, entries, reader, settings)

    controller.set_layout("two_columns")
    assert sidebar.isHidden()
    assert not entries.isHidden()
    assert not reader.isHidden()

    controller.set_layout("immersive")
    assert sidebar.isHidden()
    assert entries.isHidden()
    assert not reader.isHidden()


def test_layout_controller_restores_each_layout_sizes(tmp_path, qtbot) -> None:
    splitter = QSplitter()
    sidebar, entries, reader = QWidget(), QWidget(), QWidget()
    for widget in (sidebar, entries, reader):
        splitter.addWidget(widget)
    settings = QSettings(str(tmp_path / "layout.ini"), QSettings.Format.IniFormat)
    controller = LayoutController(splitter, sidebar, entries, reader, settings)
    qtbot.addWidget(splitter)
    controller.set_layout("three_columns")
    controller.splitter.setSizes([240, 360, 680])
    controller.save()
    controller.set_layout("two_columns")
    controller.splitter.setSizes([0, 360, 920])
    controller.save()
    assert controller.sizes_for("three_columns") == [240, 360, 680]
    assert controller.sizes_for("two_columns") == [0, 360, 920]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_ui/test_layout_controller.py -q`

Expected: FAIL，提示 `ui.layout_controller` 不存在。

- [ ] **Step 3: 实现最小布局控制器**

```python
from typing import Literal, cast
from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QSplitter, QWidget

AppLayout = Literal["three_columns", "two_columns", "immersive"]


class LayoutController(QObject):
    layout_changed = Signal(str)
    SETTINGS_KEY = "ui/main_window/layout"
    VALID_LAYOUTS = frozenset({"three_columns", "two_columns", "immersive"})
    DEFAULT_SIZES = {
        "three_columns": [240, 360, 680],
        "two_columns": [0, 360, 920],
        "immersive": [0, 0, 1280],
    }

    def __init__(
        self,
        splitter: QSplitter,
        sidebar: QWidget,
        entries: QWidget,
        reader: QWidget,
        settings: QSettings,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.splitter = splitter
        self._sidebar = sidebar
        self._entries = entries
        self._reader = reader
        self._settings = settings
        raw = str(settings.value(self.SETTINGS_KEY, "three_columns"))
        self._layout = cast(AppLayout, raw if raw in self.VALID_LAYOUTS else "three_columns")
        self.set_layout(self._layout, user_initiated=False)

    @property
    def layout(self) -> AppLayout:
        return self._layout

    def sizes_for(self, layout: AppLayout) -> list[int]:
        key = f"ui/main_window/layout_sizes/{layout}"
        raw = self._settings.value(key, self.DEFAULT_SIZES[layout])
        try:
            sizes = [int(value) for value in raw]
        except (TypeError, ValueError):
            return list(self.DEFAULT_SIZES[layout])
        visible = sizes if layout == "three_columns" else sizes[1:] if layout == "two_columns" else sizes[2:]
        if len(sizes) != 3 or any(value < 0 for value in sizes) or any(value == 0 for value in visible):
            return list(self.DEFAULT_SIZES[layout])
        return sizes

    def _save_current_sizes(self) -> None:
        sizes = self.splitter.sizes()
        if len(sizes) == 3 and sum(sizes) > 0:
            self._settings.setValue(f"ui/main_window/layout_sizes/{self._layout}", sizes)

    def save(self) -> None:
        self._save_current_sizes()
        self._settings.sync()

    def set_layout(self, value: str, *, user_initiated: bool = True) -> None:
        if value not in self.VALID_LAYOUTS:
            raise ValueError("Unsupported application layout")
        self._save_current_sizes()
        self._layout = cast(AppLayout, value)
        self._sidebar.setVisible(value == "three_columns")
        self._entries.setVisible(value != "immersive")
        self._reader.setVisible(True)
        self._splitter.setSizes(self.sizes_for(self._layout))
        self._settings.setValue(self.SETTINGS_KEY, value)
        self.layout_changed.emit(value)
```

尺寸解析必须拒绝长度不是 3、包含负值或可见栏为 0 的值，并回退到 `DEFAULT_SIZES`。

- [ ] **Step 4: 运行布局测试**

Run: `pytest tests/test_ui/test_layout_controller.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add ui/layout_controller.py tests/test_ui/test_layout_controller.py
git commit -m "feat(ui): add persistent application layouts"
```

---

### Task 3: 添加三个明确布局按钮并接入主窗口

**Files:**
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `ui/main_window.py`
- Modify: `tests/test_ui/test_reader_toolbar.py`
- Modify: `tests/test_ui/test_main_window.py`

**Interfaces:**
- Consumes: Task 2 `LayoutController`。
- Produces: `ReaderToolbar.layout_changed = Signal(str)` 与 `set_layout(value: str)`。

- [ ] **Step 1: 写工具栏与窗口接线失败测试**

```python
def test_toolbar_has_three_direct_layout_buttons(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)
    assert [button.property("layoutValue") for button in toolbar.layout_buttons] == [
        "three_columns", "two_columns", "immersive"
    ]
    for button in toolbar.layout_buttons:
        assert button.toolTip()
        assert button.accessibleName()
        assert button.minimumWidth() >= 36
        assert button.minimumHeight() >= 36


def test_window_layout_button_preserves_selected_entry(main_window) -> None:
    main_window._selected_entry_id = 42
    main_window.reader_view.toolbar.two_columns_button.click()
    assert main_window.layout_controller.layout == "two_columns"
    assert main_window._selected_entry_id == 42
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_ui/test_reader_toolbar.py tests/test_ui/test_main_window.py -q`

Expected: FAIL，布局按钮和 `layout_controller` 尚未接线。

- [ ] **Step 3: 添加互斥布局按钮**

```python
self.three_columns_button = self._layout_button(self.tr("三栏"), "three_columns")
self.two_columns_button = self._layout_button(self.tr("双栏"), "two_columns")
self.immersive_button = self._layout_button(self.tr("沉浸"), "immersive")
self.layout_buttons = (
    self.three_columns_button,
    self.two_columns_button,
    self.immersive_button,
)
```

`_layout_button()` 设置 `layoutValue`、Tooltip、accessibleName、36×36 最小尺寸和互斥 checked 状态，点击时发射 `layout_changed(value)`。

- [ ] **Step 4: 在 MainWindow 中接线并保存**

```python
self.layout_controller = LayoutController(
    self.splitter, self.sidebar, self.entry_list, self.reader_view, self._settings, self
)
self.reader_view.toolbar.layout_changed.connect(
    lambda value: self.layout_controller.set_layout(value, user_initiated=True)
)
self.layout_controller.layout_changed.connect(self.reader_view.toolbar.set_layout)
```

`save_ui_state()` 调用 `layout_controller.save()`；`restore_ui_state()` 不再用一个 splitter blob 覆盖三种布局各自尺寸。

- [ ] **Step 5: 运行并提交**

Run: `pytest tests/test_ui/test_reader_toolbar.py tests/test_ui/test_main_window.py tests/test_ui/test_layout_controller.py -q`

Expected: PASS。

```powershell
git add ui/reader/reader_toolbar.py ui/main_window.py tests/test_ui
git commit -m "feat(ui): add direct reader layout controls"
```

---

### Task 4: Reader 原文对照自动扩宽并正确恢复

**Files:**
- Modify: `ui/layout_controller.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/main_window.py`
- Modify: `tests/test_ui/test_layout_controller.py`
- Modify: `tests/test_ui/test_reader_view.py`

**Interfaces:**
- Consumes: Reader 模式 `reader | web | split`。
- Produces: `LayoutController.begin_reader_split()`, `end_reader_split()` 与 `ReaderView.reading_mode_changed = Signal(str)`。

- [ ] **Step 1: 写临时扩宽与手动优先失败测试**

```python
def test_reader_split_temporarily_hides_sidebar(layout_controller) -> None:
    layout_controller.set_layout("three_columns")
    layout_controller.begin_reader_split()
    assert layout_controller.layout == "two_columns"
    layout_controller.end_reader_split()
    assert layout_controller.layout == "three_columns"


def test_manual_layout_change_during_reader_split_is_not_overridden(layout_controller) -> None:
    layout_controller.set_layout("three_columns")
    layout_controller.begin_reader_split()
    layout_controller.set_layout("immersive", user_initiated=True)
    layout_controller.end_reader_split()
    assert layout_controller.layout == "immersive"


def test_reader_split_restores_saved_internal_ratio(reader_view) -> None:
    reader_view.resize(1200, 700)
    reader_view.show()
    reader_view.set_mode("split")
    reader_view.splitter.setSizes([600, 600])
    assert all(size >= 420 for size in reader_view.splitter.sizes())
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_ui/test_layout_controller.py tests/test_ui/test_reader_view.py -q`

Expected: FAIL，临时布局与内部比例尚未实现。

- [ ] **Step 3: 实现自动布局恢复规则**

```python
def begin_reader_split(self) -> None:
    self._split_origin = self._layout if self._layout == "three_columns" else None
    self._split_manual_override = False
    if self._split_origin is not None:
        self.set_layout("two_columns", user_initiated=False)


def end_reader_split(self) -> None:
    if self._split_origin is not None and not self._split_manual_override:
        self.set_layout(self._split_origin, user_initiated=False)
    self._split_origin = None
```

`set_layout(value, user_initiated=True)` 在 split 活动期间设置 `_split_manual_override = True`。

- [ ] **Step 4: 保存 Reader 内部 splitter 比例**

使用 `ui/reader/splitter_sizes` 保存两个整数。恢复时总可用宽度达到 840 px 才应用保存比例，否则使用当前可用宽度的 50/50；不得把任一可见侧恢复为小于 420 px。

- [ ] **Step 5: 接线、运行并提交**

`ReaderView.set_mode()` 发射 `reading_mode_changed(mode)`；`MainWindow` 在进入 `split` 时调用 `begin_reader_split()`，离开时调用 `end_reader_split()`。

Run: `pytest tests/test_ui/test_layout_controller.py tests/test_ui/test_reader_view.py tests/test_ui/test_main_window.py -q`

Expected: PASS。

```powershell
git add ui/layout_controller.py ui/reader/reader_view.py ui/main_window.py tests/test_ui
git commit -m "feat(reader): widen and restore split reading mode"
```

---

### Task 5: 构建 AI 助手抽屉及三个纯展示页签

**Files:**
- Create: `ui/reader/summary_panel.py`
- Create: `ui/reader/translation_panel.py`
- Create: `ui/reader/cleaning_panel.py`
- Create: `ui/reader/ai_assistant_panel.py`
- Create: `tests/test_ui/test_ai_assistant.py`
- Create: `tests/test_ui/test_cleaning_panel.py`
- Modify: `app/styles.py`

**Interfaces:**
- Produces: 三个 Panel 的请求信号、`set_entry()`、`set_state()`，以及抽屉 `set_open()`。
- Consumes: 纯数据字符串、进度值和 Reader 阶段事件；不持有 Runtime、Store 或 Pipeline。

- [ ] **Step 1: 写抽屉、状态与可访问性失败测试**

```python
def test_ai_assistant_has_summary_translation_and_local_cleaning_tabs(qtbot) -> None:
    panel = AIAssistantPanel()
    qtbot.addWidget(panel)
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == [
        "摘要", "翻译", "正文清洗"
    ]
    assert "不使用 AI" in panel.cleaning_panel.local_notice.text()


def test_closing_assistant_only_emits_visibility_intent(qtbot) -> None:
    panel = AIAssistantPanel()
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.open_changed, timeout=500) as signal:
        panel.set_open(False)
    assert signal.args == [False]


def test_cleaning_panel_displays_four_pipeline_stages(qtbot) -> None:
    panel = CleaningPanel()
    qtbot.addWidget(panel)
    assert list(panel.stage_labels) == ["fetch", "extract", "convert", "render"]
    assert panel.retry_button.accessibleName()
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_ui/test_ai_assistant.py tests/test_ui/test_cleaning_panel.py -q`

Expected: FAIL，Panel 模块不存在。

- [ ] **Step 3: 实现 Panel 信号与状态 API**

```python
from PySide6.QtGui import QTextCursor


class SummaryPanel(QWidget):
    generate_requested = Signal()
    cancel_requested = Signal()
    retry_requested = Signal()

    def append_chunk(self, chunk: str) -> None:
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(chunk)

    def set_state(self, status: str, *, text: str = "", error: str | None = None) -> None:
        if text:
            self.output.setPlainText(text)
        self.status_label.setText(error or status)
        self.cancel_button.setVisible(status in {"queued", "running"})


class TranslationPanel(QWidget):
    translate_requested = Signal()
    cancel_requested = Signal()
    retry_requested = Signal()

    def set_state(self, status: str, *, progress: float = 0.0, error: str | None = None) -> None:
        self.progress_bar.setValue(round(progress * 100))
        self.status_label.setText(error or status)
        self.cancel_button.setVisible(status in {"queued", "running"})


class CleaningPanel(QWidget):
    refresh_requested = Signal()

    def set_stage(self, stage: str, status: str, error: str | None = None) -> None:
        if stage not in self.stage_labels:
            raise ValueError("Unsupported Reader stage")
        self.stage_labels[stage].setText(error or status)
```

`SummaryPanel` 使用只读 `QPlainTextEdit` 保证文本可选择复制；错误或取消不清空内容。`TranslationPanel` 使用 `QProgressBar` 并同时显示百分比文字。未绑定文章时三个 Panel 进入 disabled 页面。

- [ ] **Step 4: 实现抽屉与集中样式**

```python
class AIAssistantPanel(QWidget):
    open_changed = Signal(bool)
    PREFERRED_WIDTH = 360

    def set_entry(self, entry_id: int | None) -> None:
        self.summary_panel.set_entry(entry_id)
        self.translation_panel.set_entry(entry_id)
        self.cleaning_panel.set_entry(entry_id)
```

QSS 只新增语义对象选择器：`QWidget#AIAssistantPanel`、`QTabWidget#AIAssistantTabs`、`QLabel[agentStatus]`、`QProgressBar`；颜色全部来自 `Palette`。

- [ ] **Step 5: 运行并提交**

Run: `pytest tests/test_ui/test_ai_assistant.py tests/test_ui/test_cleaning_panel.py tests/test_ui/test_styles.py -q`

Expected: PASS。

```powershell
git add ui/reader/*panel.py app/styles.py tests/test_ui
git commit -m "feat(ui): add accessible reader ai assistant"
```

---

### Task 6: 通过共享 AgentRuntime 桥接摘要与翻译 UI

**Files:**
- Create: `ui/reader/agent_controller.py`
- Create: `tests/test_ui/test_agent_controller.py`
- Modify: `ui/reader/ai_assistant_panel.py`

**Interfaces:**
- Consumes: `AgentRuntime.submit(entry_id, agent_type) -> str`、`cancel(run_id)`、`AgentUIEvent`。
- Produces: `ReaderAgentController.event_received = Signal(object)`、`set_entry()`、`request_summary()`、`request_translation()`、`cancel()`、`set_auto_summary()`、`content_ready()`。

- [ ] **Step 1: 写提交、过滤、取消与防抖失败测试**

```python
class FakeRuntime:
    def __init__(self) -> None:
        self.signals = AgentSignals()
        self.submitted: list[tuple[int, str]] = []
        self.cancelled: list[str] = []

    def submit(self, entry_id: int, agent_type: str) -> str:
        self.submitted.append((entry_id, agent_type))
        return f"{agent_type}-{entry_id}"

    def cancel(self, run_id: str) -> None:
        self.cancelled.append(run_id)


def test_controller_ignores_wrong_entry_and_run_events(qtbot) -> None:
    runtime = FakeRuntime()
    controller = ReaderAgentController(runtime)
    controller.set_entry(7)
    run_id = controller.request_summary()
    spy = QSignalSpy(controller.event_received)
    runtime.signals.chunk_received.emit(
        AgentUIEvent("old", 6, "summary", "running", chunk="stale")
    )
    runtime.signals.chunk_received.emit(
        AgentUIEvent(run_id, 7, "summary", "running", chunk="fresh")
    )
    assert spy.count() == 1
    assert spy.at(0)[0].chunk == "fresh"


def test_switching_entry_does_not_cancel_running_agent(qtbot) -> None:
    runtime = FakeRuntime()
    controller = ReaderAgentController(runtime)
    controller.set_entry(7)
    controller.request_translation()
    controller.set_entry(8)
    assert runtime.cancelled == []


def test_auto_summary_waits_one_second_and_uses_latest_entry(qtbot) -> None:
    runtime = FakeRuntime()
    controller = ReaderAgentController(runtime)
    controller.set_auto_summary(True)
    controller.content_ready(7)
    controller.content_ready(8)
    qtbot.wait(1050)
    assert runtime.submitted == [(8, "summary")]
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_ui/test_agent_controller.py -q`

Expected: FAIL，Controller 不存在。

- [ ] **Step 3: 实现 Runtime 桥接**

```python
from PySide6.QtCore import QObject, QTimer, Signal
from core.agent.runtime import AgentRuntime, AgentUIEvent


class ReaderAgentController(QObject):
    event_received = Signal(object)

    def __init__(self, runtime: AgentRuntime, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self._entry_id: int | None = None
        self._run_ids: dict[str, str] = {}
        self._auto_summary = False
        self._summary_timer = QTimer(self)
        self._summary_timer.setSingleShot(True)
        self._summary_timer.setInterval(1000)
        self._summary_timer.timeout.connect(self.request_summary)
        runtime.signals.state_changed.connect(self._forward_if_current)
        runtime.signals.chunk_received.connect(self._forward_if_current)

    def set_entry(self, entry_id: int | None) -> None:
        self._summary_timer.stop()
        self._entry_id = entry_id
        self._run_ids.clear()

    def set_auto_summary(self, enabled: bool) -> None:
        self._auto_summary = enabled
        if not enabled:
            self._summary_timer.stop()

    def content_ready(self, entry_id: int) -> None:
        if self._auto_summary and entry_id == self._entry_id:
            self._summary_timer.start()

    def _submit(self, agent_type: str) -> str:
        if self._entry_id is None:
            raise RuntimeError("No Reader entry is selected")
        run_id = self._runtime.submit(self._entry_id, agent_type)
        self._run_ids[agent_type] = run_id
        return run_id

    def request_summary(self) -> str:
        return self._submit("summary")

    def request_translation(self) -> str:
        return self._submit("translation")

    def cancel(self, agent_type: str) -> None:
        run_id = self._run_ids.get(agent_type)
        if run_id is not None:
            self._runtime.cancel(run_id)

    def _accept(self, event: AgentUIEvent) -> bool:
        return (
            event.entry_id == self._entry_id
            and self._run_ids.get(event.agent_type) == event.run_id
        )

    def _forward_if_current(self, event: AgentUIEvent) -> None:
        if self._accept(event):
            self.event_received.emit(event)
```

自动摘要使用 single-shot `QTimer`，间隔精确为 1000 ms；`set_entry()` 停止未触发 timer，但不调用 Runtime.cancel。

- [ ] **Step 4: 将事件映射到 Panel**

`AIAssistantPanel.apply_agent_event(event)` 根据 `agent_type` 路由。Summary chunk 追加文本；translation progress 更新进度；error/cancelled 保留内容；done 解析 `result_json`。

- [ ] **Step 5: 运行并提交**

Run: `pytest tests/test_ui/test_agent_controller.py tests/test_ui/test_ai_assistant.py -q`

Expected: PASS。

```powershell
git add ui/reader/agent_controller.py ui/reader/ai_assistant_panel.py tests/test_ui
git commit -m "feat(ui): bridge reader panels to agent runtime"
```

---

### Task 7: 完成翻译持久化、失败段落重试与三种 Reader 显示模式

**Files:**
- Modify: `core/agent/translation.py`
- Modify: `tests/test_agent/test_translation.py`
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/reader/translation_panel.py`
- Modify: `tests/test_ui/test_reader_toolbar.py`
- Modify: `tests/test_ui/test_reader_view.py`
- Modify: `tests/test_ui/test_ai_assistant.py`

**Interfaces:**
- Consumes: `AgentStore` 与 Task 6 Controller。
- Produces: TranslationAgent 缓存结果中的 `segments`、`failed_indices`，Reader `translation_display_changed = Signal(str)`。

- [ ] **Step 1: 写翻译缓存和失败段落重试失败测试**

```python
@pytest.mark.asyncio
async def test_translation_persists_segments_and_retries_only_failures(
    db, entry_id, mock_pipeline, mock_router, mock_templates
) -> None:
    from unittest.mock import AsyncMock

    store = AgentStore(db)
    agent = TranslationAgent(mock_pipeline, mock_router, mock_templates, store)
    attempts: dict[int, int] = {}

    async def flaky_translate(segment, *_args) -> None:
        attempts[segment.index] = attempts.get(segment.index, 0) + 1
        if segment.index == 1 and attempts[segment.index] <= 3:
            raise RuntimeError("segment failed")
        segment.translation = f"translated-{segment.index}"

    agent._translate_segment = AsyncMock(side_effect=flaky_translate)
    first = await agent.translate(entry_id, "run-1")
    assert "segments" in first
    assert first["failed_indices"] == [1]

    calls_before_retry = agent._translate_segment.call_count
    second = await agent.translate(entry_id, "run-2")
    assert agent._translate_segment.call_count == calls_before_retry + 1
    assert second["failed_indices"] == []
```

```python
def test_reader_translation_modes_preserve_original_fragment(reader_view) -> None:
    reader_view.show_content("<p>Original</p>", "https://example.com")
    reader_view.set_translation_html(
        '<div class="mercury-trans-block"><div class="mercury-original">Original</div>'
        '<div class="mercury-translated">译文</div></div>'
    )
    reader_view.set_translation_display("translated")
    assert "译文" in reader_view.last_html
    assert "mercury-original{display:none" in reader_view.last_html.replace(" ", "")
    reader_view.set_translation_display("original")
    assert "<p>Original</p>" in reader_view.last_html
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_agent/test_translation.py tests/test_ui/test_reader_view.py -q`

Expected: FAIL，TranslationAgent 尚未持久化 segments，Reader 尚无显示模式。

- [ ] **Step 3: 扩展 TranslationAgent 的最小持久化合同**

构造函数改为：

```python
def __init__(
    self,
    pipeline: ReaderPipeline,
    router: LLMRouter,
    templates: TemplateLoader,
    agent_store: AgentStore,
) -> None:
    self._pipeline = pipeline
    self._router = router
    self._templates = templates
    self._agent_store = agent_store
```

结果 JSON 固定包含：

```python
{
    "html": bilingual_html,
    "segments": [
        {"index": s.index, "original_html": s.html, "translation": s.translation, "error": s.error}
        for s in segments
    ],
    "failed_indices": [s.index for s in segments if s.error],
    "paragraphs_total": total,
    "paragraphs_success": success_count,
    "paragraphs_failed": len(failed_segments),
    "target_language": self.target_language,
}
```

`translate()` 开始时先读取 `AgentStore.get_latest(entry_id, "translation")`，再创建本次运行记录。缓存结果没有失败段时将缓存复制到本次记录并返回；存在 `failed_indices` 时重建 segments，只重试这些索引，再完成本次记录。不得重译成功段落。读取必须发生在 `AgentStore.create()` 之前，避免刚创建的 running 记录遮住缓存；取消和异常分别调用 `AgentStore.cancel(run_id)` 与 `AgentStore.complete(run_id, None, error=message)`。

- [ ] **Step 4: 删除 Core 中的硬编码翻译色板**

将 `_BLOCK_HTML` 改为仅含语义 class：

```python
_BLOCK_HTML = """<div class="mercury-trans-block">
<div class="mercury-original">{original}</div>
<div class="mercury-translated">{translation}</div>
</div>"""
```

颜色、缩进、斜体和边框由 `ThemeManager.reader_css()` 使用当前 `Palette` 生成。

- [ ] **Step 5: 添加原文/双语/仅译文按钮与本地重渲染**

```python
self.translation_display_combo.addItem(self.tr("原文"), "original")
self.translation_display_combo.addItem(self.tr("双语"), "bilingual")
self.translation_display_combo.addItem(self.tr("仅译文"), "translated")
```

ReaderView 保存 `_content_fragment` 和 `_translation_html`。切换只调用本地 `_rerender_reader()`，不得调用 ReaderPipeline 或网络；重渲染前后通过 `runJavaScript("window.scrollY")` 与 `scrollTo()` 尽量恢复滚动位置。

- [ ] **Step 6: 运行并提交**

Run: `pytest tests/test_agent/test_translation.py tests/test_ui/test_reader_toolbar.py tests/test_ui/test_reader_view.py tests/test_ui/test_ai_assistant.py -q`

Expected: PASS。

```powershell
git add core/agent/translation.py ui/reader tests/test_agent/test_translation.py tests/test_ui
git commit -m "feat(reader): persist and render bilingual translations"
```

---

### Task 8: 为 Reader 管线增加阶段事件和重新清洗 UseCase

**Files:**
- Create: `core/reader/events.py`
- Create: `core/reader/use_cases.py`
- Create: `tests/test_reader/test_reader_events.py`
- Create: `tests/test_reader/test_refresh_use_case.py`
- Modify: `core/reader/pipeline.py`
- Modify: `ui/main_window.py`
- Modify: `ui/reader/cleaning_panel.py`
- Modify: `tests/test_ui/test_cleaning_panel.py`

**Interfaces:**
- Produces: `ReaderStageEvent`、`ReaderPipeline.build(entry_id, request_id=None, stage_callback=None)`、`ReaderRefreshUseCase.refresh()`。
- Consumes: `ContentStore.delete_by_entry()` 与既有 ReaderPipeline。

- [ ] **Step 1: 写阶段顺序与重新清洗失败测试**

```python
@pytest.mark.asyncio
async def test_pipeline_reports_ordered_stages(db) -> None:
    from unittest.mock import patch
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    from tests.test_reader.test_pipeline import _mock_http

    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-events", "https://example.com/article",
        "Article", "Summary", "Author", None,
    )
    events = []
    pipeline = ReaderPipeline(db)
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=_mock_http()):
        await pipeline.build(entry.id, request_id="req-1", stage_callback=events.append)
    assert [(event.stage, event.status) for event in events] == [
        ("fetch", "running"), ("fetch", "done"),
        ("extract", "running"), ("extract", "done"),
        ("convert", "running"), ("convert", "done"),
        ("render", "running"), ("render", "done"),
    ]
    assert all(event.request_id == "req-1" for event in events)


@pytest.mark.asyncio
async def test_refresh_use_case_deletes_only_requested_entry_cache() -> None:
    content_store = FakeContentStore()
    pipeline = FakePipeline()
    use_case = ReaderRefreshUseCase(content_store, pipeline)
    await use_case.refresh(9, "req-9", lambda _event: None)
    assert content_store.deleted == [9]
    assert pipeline.built == [(9, "req-9")]
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_reader/test_reader_events.py tests/test_reader/test_refresh_use_case.py -q`

Expected: FAIL，事件和 UseCase 不存在。

- [ ] **Step 3: 定义稳定 Reader 事件**

```python
from dataclasses import dataclass
from typing import Literal

ReaderStage = Literal["fetch", "extract", "convert", "render"]
ReaderStageStatus = Literal["running", "done", "error", "cached"]


@dataclass(frozen=True)
class ReaderStageEvent:
    entry_id: int
    request_id: str
    stage: ReaderStage
    status: ReaderStageStatus
    error: str | None = None
    fallback: str | None = None
```

`ReaderPipeline.build()` 接收 `stage_callback: Callable[[ReaderStageEvent], None] | None = None`，每一阶段进入和完成时同步调用 callback；异常时对当前阶段发送 error 后重抛。缓存命中发送四个 `cached` 事件，不伪装网络执行。

- [ ] **Step 4: 实现重新清洗 UseCase**

```python
class ReaderRefreshUseCase:
    def __init__(self, content_store: ContentStore, pipeline: ReaderPipeline) -> None:
        self._content_store = content_store
        self._pipeline = pipeline

    async def refresh(
        self,
        entry_id: int,
        request_id: str,
        stage_callback: Callable[[ReaderStageEvent], None],
    ) -> RenderedContent:
        await self._content_store.delete_by_entry(entry_id)
        return await self._pipeline.build(
            entry_id, request_id=request_id, stage_callback=stage_callback
        )
```

- [ ] **Step 5: UI 只消费匹配事件**

MainWindow 为正常加载和重新清洗生成新 request_id，将事件通过 Qt Signal 送给 `CleaningPanel`。Panel 仅在 `entry_id` 和 `request_id` 同时匹配时更新四阶段；失败保留当前 Reader 内容并显示 fallback 来源。

- [ ] **Step 6: 运行并提交**

Run: `pytest tests/test_reader/test_reader_events.py tests/test_reader/test_refresh_use_case.py tests/test_ui/test_cleaning_panel.py tests/test_ui/test_main_window.py -q`

Expected: PASS。

```powershell
git add core/reader/events.py core/reader/use_cases.py core/reader/pipeline.py ui tests/test_reader tests/test_ui
git commit -m "feat(reader): expose local cleaning pipeline states"
```

---

### Task 9: 组合 Agent、抽屉与 Reader，并持久化抽屉状态

**Files:**
- Create: `app/services.py`
- Create: `tests/test_app/__init__.py`
- Create: `tests/test_app/test_services.py`
- Modify: `app/app.py`
- Modify: `app/state.py`
- Modify: `ui/main_window.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `tests/test_ui/test_main_window.py`
- Modify: `tests/test_ui/test_reader_view.py`

**Interfaces:**
- Produces: `AppServices` 组合根、ReaderView AI 抽屉开关与宽度持久化。
- Consumes: Tasks 5–8 的 Panel、Controller、Agent 与 RefreshUseCase。

- [ ] **Step 1: 写组合与抽屉行为失败测试**

```python
def test_services_register_summary_and_translation_handlers(db, tmp_path) -> None:
    services = build_services(db, prompt_sandbox=tmp_path / "prompts")
    assert "summary" in services.agent_runtime._handlers
    assert "translation" in services.agent_runtime._handlers


def test_ai_drawer_close_does_not_cancel_active_run(main_window) -> None:
    from unittest.mock import patch

    main_window.reader_agent_controller.set_entry(4)
    main_window.reader_agent_controller.request_summary()
    with patch.object(main_window.reader_agent_controller, "cancel") as cancel:
        main_window.reader_view.set_ai_assistant_open(False)
    cancel.assert_not_called()


def test_entering_split_closes_narrow_ai_drawer_without_losing_text(reader_view) -> None:
    reader_view.ai_assistant.summary_panel.append_chunk("保留内容")
    reader_view.resize(900, 700)
    reader_view.set_mode("split")
    assert not reader_view.ai_assistant_open
    assert "保留内容" in reader_view.ai_assistant.summary_panel.output.toPlainText()


def test_ai_drawer_visibility_and_width_restore(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "drawer.ini"), QSettings.Format.IniFormat)
    first = ReaderView(settings=settings)
    qtbot.addWidget(first)
    first.set_ai_assistant_open(True)
    first.assistant_splitter.setSizes([840, 360])
    first.save_ui_state()

    restored = ReaderView(settings=settings)
    qtbot.addWidget(restored)
    assert restored.ai_assistant_open
    assert restored.ai_assistant_width == 360
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_app/test_services.py tests/test_ui/test_main_window.py tests/test_ui/test_reader_view.py -q`

Expected: FAIL，组合根和抽屉接线不存在。

- [ ] **Step 3: 创建应用服务组合根**

```python
@dataclass(frozen=True)
class AppServices:
    feed_store: FeedStore
    entry_store: EntryStore
    sync_service: SyncService
    reader_pipeline: ReaderPipeline
    reader_refresh: ReaderRefreshUseCase
    agent_runtime: AgentRuntime


def build_services(db: DatabaseManager, prompt_sandbox: Path | None = None) -> AppServices:
    pipeline = ReaderPipeline(db)
    runtime = AgentRuntime()
    router = LLMRouter(ProviderConfig(
        name="Local",
        base_url="http://localhost:11434/v1",
        model="qwen3",
    ))
    project_root = Path(__file__).resolve().parents[1]
    templates = TemplateLoader(
        str(project_root / "resources/prompts"),
        str(prompt_sandbox or Path.home() / ".mercury/prompts"),
    )
    agent_store = AgentStore(db)
    SummaryAgent(pipeline, router, templates, agent_store).register(runtime)
    TranslationAgent(pipeline, router, templates, agent_store).register(runtime)
    return AppServices(
        FeedStore(db), EntryStore(db), SyncService(db), pipeline,
        ReaderRefreshUseCase(ContentStore(db), pipeline), runtime,
    )
```

测试必须注入临时 prompt 目录和 fake Provider；不得访问 keyring、Ollama 或网络。

- [ ] **Step 4: 将抽屉嵌入 Reader**

ReaderView 使用水平容器组合现有内容区与 `AIAssistantPanel`，保存：

```python
AI_OPEN_KEY = "ui/reader/ai_assistant_open"
AI_WIDTH_KEY = "ui/reader/ai_assistant_width"
AI_PREFERRED_WIDTH = 360
MIN_READER_WIDTH = 620
```

并公开只读状态：

```python
@property
def ai_assistant_open(self) -> bool:
    return not self.ai_assistant.isHidden()

@property
def ai_assistant_width(self) -> int:
    return int(self._settings.value(self.AI_WIDTH_KEY, self.AI_PREFERRED_WIDTH))

def save_ui_state(self) -> None:
    sizes = self.assistant_splitter.sizes()
    if len(sizes) == 2 and sizes[1] > 0:
        self._settings.setValue(self.AI_WIDTH_KEY, sizes[1])
    self._settings.setValue(self.AI_OPEN_KEY, self.ai_assistant_open)
    self._settings.sync()
```

Task 9 同时将 `MainWindow.__init__` 扩展为接收 `agent_runtime: AgentRuntime` 和 `reader_refresh: ReaderRefreshUseCase`，测试通过 fake 实例注入；View 不自行创建 Runtime 或 UseCase。

工具栏 AI 按钮为 checkable，至少 36×36，Tooltip 与 accessibleName 均为“显示或隐藏 AI 助手”。关闭只调用 `setVisible(False)`，不触发 Controller.cancel。

- [ ] **Step 5: 主窗口绑定文章、内容完成与 Panel 意图**

文章选择后先调用 `reader_agent_controller.set_entry(entry_id)` 和 `ai_assistant.set_entry(entry_id)`；Reader 内容成功显示后调用 `reader_agent_controller.content_ready(entry_id)`。Panel 的生成、翻译、取消、重试和重新清洗信号分别连接 Controller/UseCase。

- [ ] **Step 6: 运行并提交**

Run: `pytest tests/test_app/test_services.py tests/test_ui/test_main_window.py tests/test_ui/test_reader_view.py tests/test_ui/test_ai_assistant.py -q`

Expected: PASS。

```powershell
git add app ui tests/test_app tests/test_ui
git commit -m "feat(app): integrate reader agents and assistant drawer"
```

---

### Task 10: 完成视觉、可访问性、回归验证和里程碑文档

**Files:**
- Modify: `app/styles.py`
- Modify: `ui/reader/theme_manager.py`
- Modify: `tests/test_ui/test_styles.py`
- Modify: `tests/test_ui/test_components.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: Tasks 1–9 全部 UI。
- Produces: 两套完整主题、无硬编码局部色板、最终测试与里程碑记录。

- [ ] **Step 1: 写主题覆盖与控件状态失败测试**

```python
@pytest.mark.parametrize("palette", [LIGHT_PALETTE, DARK_PALETTE])
def test_stylesheet_covers_ai_and_all_button_states(palette) -> None:
    qss = application_stylesheet(palette)
    for selector in (
        "QWidget#AIAssistantPanel",
        "QTabWidget#AIAssistantTabs",
        "QPushButton:hover",
        "QPushButton:pressed",
        "QPushButton:checked",
        "QPushButton:focus",
        "QPushButton:disabled",
        "QProgressBar",
    ):
        assert selector in qss


def test_every_icon_button_has_accessible_metadata(main_window) -> None:
    for button in main_window.findChildren(QPushButton):
        if not button.text():
            assert button.toolTip()
            assert button.accessibleName()
            assert button.minimumWidth() >= 36
            assert button.minimumHeight() >= 36


def test_theme_change_preserves_layout_article_and_agent_output(main_window) -> None:
    main_window._selected_entry_id = 42
    main_window.layout_controller.set_layout("immersive")
    main_window.reader_view.ai_assistant.summary_panel.append_chunk("已有摘要")
    main_window.reader_view.app_theme_controller.set_preference("dark")
    assert main_window._selected_entry_id == 42
    assert main_window.layout_controller.layout == "immersive"
    assert "已有摘要" in main_window.reader_view.ai_assistant.summary_panel.output.toPlainText()
```

- [ ] **Step 2: 运行并确认失败**

Run: `pytest tests/test_ui/test_styles.py tests/test_ui/test_components.py -q`

Expected: FAIL，指出未覆盖的控件状态或元数据。

- [ ] **Step 3: 完成语义 QSS 与 Reader CSS**

`application_stylesheet(palette)` 覆盖窗口、Sidebar、列表、ReaderToolbar、AI Panel、Tabs、进度条、菜单、对话框、状态栏和滚动条。`ThemeManager.reader_css()` 增加：

```css
.mercury-translated {
  margin-left: 1.6em;
  padding: 8px 12px;
  color: PALETTE_TEXT;
  background: PALETTE_ACCENT_SOFT;
  border-left: 3px solid PALETTE_ACCENT;
  border-radius: 8px;
  font-style: italic;
}
body.translation-translated .mercury-original { display: none; }
```

代码中使用实际 `Palette` f-string 字段，不保留大写占位词或组件内十六进制颜色。

- [ ] **Step 4: 运行格式、Lint 和测试**

Run: `ruff format --check app ui core/reader core/agent/translation.py tests/test_ui tests/test_reader tests/test_agent/test_translation.py`

Expected: exit 0。

Run: `ruff check app ui core/reader core/agent/translation.py tests/test_ui tests/test_reader tests/test_agent/test_translation.py`

Expected: exit 0。

Run: `pytest tests/test_ui -q`

Expected: PASS。

Run: `pytest -q`

Expected: PASS，且无真实网络或 LLM 调用。

- [ ] **Step 5: 完成浅色/深色人工检查**

在 Windows 100%、150%、200% 缩放下分别检查：

1. 三栏、双栏、沉浸阅读一次点击可达，重启后恢复。
2. Reader 原文对照在 1280 px 窗口下两侧可读，退出后布局恢复。
3. AI 抽屉约 360 px，关闭不取消任务，窄窗口进入对照时内容保留。
4. 摘要流式、翻译进度、原文/双语/仅译文和正文清洗四阶段均可见。
5. 两套主题无纯白/纯黑主阅读面，无局部第二色板。
6. Tooltip、键盘焦点、可访问名称和长中英文文案可用。

- [ ] **Step 6: 更新里程碑文档**

仅在完整验证通过后更新 `AGENTS.md`：

- “基础 UI”标记完成。
- “Reader 与主题 UI”标记完成。
- “功能面板 UI”备注摘要、翻译与正文清洗已完成，其他面板仍待后续。
- “AI Agent 运行时 / 摘要 Agent / 翻译 Agent”按当前实际测试状态更新。
- 记录 Reader 原文对照自动临时扩宽与布局恢复规则。

- [ ] **Step 7: 调用完成前验证技能并提交**

在声明完成前读取并执行 `superpowers:verification-before-completion`，重新确认最后一次命令输出。

```powershell
git add app ui core/reader core/agent/translation.py tests AGENTS.md pyproject.toml
git commit -m "feat(ui): complete adaptive reader ai experience"
```

## 最终完成门槛

- 对照 `docs/superpowers/specs/2026-07-16-reader-ai-layout-design.md` 的每一条验收要求逐项核验。
- `git diff --check` 无输出。
- `ruff format --check`、`ruff check`、`pytest tests/test_ui -q` 和 `pytest -q` 全部 exit 0。
- 人工视觉验收未完成时，只能报告自动化验证结果，不能宣称界面全部完成。
