# Mercury Reader UI-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Every new UI behavior follows superpowers:test-driven-development.

**Goal:** 只使用现有成员交付和当前稳定接口，完成 Mercury 三种应用布局、Reader 对照扩宽、可折叠 AI 助手及摘要/翻译/正文清洗 UI。

**Architecture:** 从成员压缩包恢复 Phase 1/2 UI，从“近黑石墨蓝双主题”包恢复完整主题链。所有新增行为留在 `ui/`；MainWindow 只连接既有 Store、ReaderPipeline 和 AgentRuntime 接口，不修改 `core/` 或 `store/`。

**Tech Stack:** Python 3.11+、PySide6 6.5+、QWebEngineView、qasync、pytest-qt、ruff。

## Global Constraints

- 禁止修改 `core/`、`store/`、数据库迁移、ReaderPipeline 或 Agent 实现。
- 允许修改 `ui/`、`tests/test_ui/`、`app/app.py`、`app/styles.py`、`AGENTS.md`。
- 只使用 PySide6 `Signal`；用户可见文本使用 `self.tr()`。
- AI UI 只消费现有 `AgentRuntime.submit/cancel/signals` 与 `AgentUIEvent`。
- 更新 Agent UI 前同时校验 `entry_id` 和 `run_id`；切换文章不自动取消运行任务。
- 正文清洗是本地 Reader 管线说明，不称为 AI，不增加 LLM 调用。
- 当前接口没有失败段落重试时，翻译页只提供整篇重试，不伪造失败段落状态。
- 当前 ReaderPipeline 没有阶段回调时，清洗页展示固定四阶段说明和整体 loading/done/error，不伪造逐阶段实时进度。
- 主题只允许 `system/light/dark`，颜色来自集中语义 Palette。
- 图标按钮至少 36×36 px，并有 Tooltip、accessibleName、focus 与 checked 状态。
- 新行为必须先观察测试正确失败，再写最小实现。

---

### Task 1: 恢复可运行的成员 UI 与近黑石墨蓝双主题

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
- Create: `tests/test_ui/test_add_feed_dialog.py`
- Create: `tests/test_ui/test_components.py`
- Create: `tests/test_ui/test_main_window.py`
- Create: `tests/test_ui/test_styles.py`
- Modify: `app/app.py`

**Source mapping:**
- 主题链与 Reader 完整文件来自 `Mercury-UI-近黑石墨蓝双主题.zip`。
- MainWindow、Sidebar、EntryList、AddFeedDialog 与现有 UI 测试来自桌面成员压缩包。
- 不整包解压，不覆盖 `core/`、`store/`、`resources/` 或现有 Agent 测试。

**Acceptance:**
- `MainWindow` 可由 fake stores 构造，外层 splitter 有三栏。
- `ReaderView` 的 Reader/Web/双栏模式可构造。
- `application_stylesheet(LIGHT_PALETTE/DARK_PALETTE)` 可生成完整 QSS。
- `app/app.py` 使用既有 Store/Sync/ReaderPipeline 构造真实 MainWindow。

**Verification:**

```powershell
pytest tests/test_ui -q
ruff check app/styles.py ui tests/test_ui
```

**Commit:** `feat(ui): restore member reader interface baseline`

---

### Task 2: 测试驱动实现三栏、双栏和沉浸阅读

**Files:**
- Create: `ui/layout_controller.py`
- Create: `tests/test_ui/test_layout_controller.py`
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `ui/main_window.py`
- Modify: `tests/test_ui/test_main_window.py`

**Required public interface:**

```python
AppLayout = Literal["three_columns", "two_columns", "immersive"]

class LayoutController(QObject):
    layout_changed = Signal(str)
    @property
    def layout(self) -> AppLayout: ...
    def set_layout(self, value: str, *, user_initiated: bool = True) -> None: ...
    def sizes_for(self, value: AppLayout) -> list[int]: ...
    def save(self) -> None: ...
```

**RED tests:**
- three_columns 显示三栏。
- two_columns 隐藏 Sidebar，保留 EntryList + Reader。
- immersive 只显示 Reader。
- 三种布局分别保存和恢复尺寸，无效尺寸回退安全默认值。
- ReaderToolbar 有三个互斥直达按钮；每个按钮有 Tooltip、accessibleName 和 36×36 最小尺寸。
- 切换布局保持 `_selected_entry_id` 和 Reader 当前模式。

**GREEN behavior:**
- 默认尺寸 `[240, 360, 680]`、`[0, 360, 920]`、`[0, 0, 1280]`。
- QSettings keys：`ui/main_window/layout` 与 `ui/main_window/layout_sizes/<layout>`。
- 只隐藏现有 QWidget，不删除或重建栏。

**Verification:**

```powershell
pytest tests/test_ui/test_layout_controller.py tests/test_ui/test_main_window.py -q
```

**Commit:** `feat(ui): add persistent application layouts`

---

### Task 3: 测试驱动修复 Reader 原文对照宽度

**Files:**
- Modify: `ui/layout_controller.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/main_window.py`
- Modify: `tests/test_ui/test_layout_controller.py`
- Modify: `tests/test_ui/test_components.py`

**Required behavior:**
- ReaderView 发射 `reading_mode_changed = Signal(str)`。
- 从 three_columns 进入 Reader `split` 时临时切换应用 two_columns。
- 离开 Reader `split` 时恢复进入前布局。
- split 期间用户手动选择布局后，不再自动覆盖用户选择。
- Reader/Web 内部 splitter 默认 50/50，保存 key 为 `ui/reader/splitter_sizes`。
- 在可用宽度允许时每侧目标下限 420 px；不足时仍保持两侧可操作，不恢复成 1 px 窄条。

**RED tests:**
- `begin_reader_split()` 从 three_columns 进入 two_columns，`end_reader_split()` 恢复。
- split 期间手动 immersive 后退出仍为 immersive。
- 保存 `[540, 540]` 后重建 ReaderView 能恢复比例。
- 保存 `[1, 1079]` 时回退 50/50。

**Verification:**

```powershell
pytest tests/test_ui/test_layout_controller.py tests/test_ui/test_components.py tests/test_ui/test_main_window.py -q
```

**Commit:** `feat(reader): widen split reading mode`

---

### Task 4: 测试驱动构建可折叠 AI 助手纯 UI

**Files:**
- Create: `ui/reader/summary_panel.py`
- Create: `ui/reader/translation_panel.py`
- Create: `ui/reader/cleaning_panel.py`
- Create: `ui/reader/ai_assistant_panel.py`
- Create: `tests/test_ui/test_ai_assistant.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `app/styles.py`

**Required presentation interfaces:**

```python
class SummaryPanel(QWidget):
    generate_requested = Signal()
    cancel_requested = Signal()
    retry_requested = Signal()
    def set_entry(self, entry_id: int | None) -> None: ...
    def append_chunk(self, text: str) -> None: ...
    def set_state(self, status: str, error: str | None = None) -> None: ...

class TranslationPanel(QWidget):
    translate_requested = Signal()
    cancel_requested = Signal()
    retry_requested = Signal()
    def set_entry(self, entry_id: int | None) -> None: ...
    def set_state(self, status: str, progress: float = 0.0, error: str | None = None) -> None: ...

class CleaningPanel(QWidget):
    retry_requested = Signal()
    def set_entry(self, entry_id: int | None) -> None: ...
    def set_state(self, status: str, error: str | None = None) -> None: ...
```

**RED tests:**
- 抽屉包含“摘要 / 翻译 / 正文清洗”三个页签。
- 正文清洗明确显示“本地处理，不使用 AI”和四阶段名称。
- Summary 输出可选择复制，error/cancelled 不清空已有内容。
- Translation running 同时显示进度条和百分比文字；重试表示整篇重试。
- 未选择文章时三个页签 disabled 且不留空白。
- AI 按钮关闭抽屉只隐藏 QWidget，不发射取消请求。
- 抽屉 open 与约 360 px 宽度通过 QSettings 恢复。

**GREEN behavior:**
- ReaderView 使用内部水平 QSplitter 组合内容与 AI 面板。
- keys：`ui/reader/ai_assistant_open`、`ui/reader/ai_assistant_width`。
- Reader 可用宽度小于 900 px 且进入 split 时自动收起抽屉，已有文本保留。
- 所有颜色通过 `Palette` 进入 QSS。

**Verification:**

```powershell
pytest tests/test_ui/test_ai_assistant.py tests/test_ui/test_components.py tests/test_ui/test_styles.py -q
```

**Commit:** `feat(ui): add reader ai assistant drawer`

---

### Task 5: 使用现有 AgentRuntime 接口接入摘要与翻译 UI

**Files:**
- Create: `ui/reader/agent_controller.py`
- Create: `tests/test_ui/test_agent_controller.py`
- Modify: `ui/main_window.py`
- Modify: `ui/reader/ai_assistant_panel.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `tests/test_ui/test_ai_assistant.py`
- Modify: `tests/test_ui/test_main_window.py`

**Required interface:**

```python
class ReaderAgentController(QObject):
    event_received = Signal(object)
    def __init__(self, runtime: AgentRuntime, parent: QObject | None = None) -> None: ...
    def set_entry(self, entry_id: int | None) -> None: ...
    def request_summary(self) -> str: ...
    def request_translation(self) -> str: ...
    def cancel(self, agent_type: str) -> None: ...
```

**RED tests with FakeRuntime:**
- 生成摘要提交 `(entry_id, "summary")`。
- 翻译提交 `(entry_id, "translation")`。
- 只转发匹配当前 entry_id 与该 agent_type 当前 run_id 的事件。
- 切换文章不调用 Runtime.cancel。
- 用户点击取消才调用 Runtime.cancel(run_id)。
- summary chunk 追加到 SummaryPanel。
- translation progress 更新 TranslationPanel。
- translation done 的现有 `result_json["html"]` 传给 ReaderView。
- error/cancelled 保留已有 UI 内容并显示重试。

**Scope rule:**
- MainWindow 构造函数接受可选 `agent_runtime`；未配置时 AI 摘要/翻译页显示“尚未配置”，正文清洗页仍可用。
- 不在 UI 中实例化 Provider、SummaryAgent 或 TranslationAgent。
- 不修改 Runtime、AgentStore 或 TranslationAgent。

**Verification:**

```powershell
pytest tests/test_ui/test_agent_controller.py tests/test_ui/test_ai_assistant.py tests/test_ui/test_main_window.py -q
```

**Commit:** `feat(ui): connect reader assistant to agent runtime`

---

### Task 6: Reader 翻译显示、正文清洗状态与最终 UI 验证

**Files:**
- Modify: `ui/reader/reader_toolbar.py`
- Modify: `ui/reader/reader_view.py`
- Modify: `ui/main_window.py`
- Modify: `ui/reader/theme_manager.py`
- Modify: `app/styles.py`
- Modify: `tests/test_ui/test_components.py`
- Modify: `tests/test_ui/test_main_window.py`
- Modify: `tests/test_ui/test_styles.py`
- Modify: `AGENTS.md`

**RED tests:**
- 翻译结果可切换“原文 / 双语 / 仅译文”，切换只重渲染本地 HTML。
- 原文 fragment 始终保留；主题变化不丢失翻译或摘要内容。
- MainWindow Reader loading/content/error 映射到 CleaningPanel 整体状态。
- 清洗重试按钮复用现有 Reader retry 请求，不删除缓存、不访问 Store。
- 三种应用布局、Reader 模式、抽屉状态和当前文章在主题切换后保持。
- 两套 Palette 覆盖 AI Panel、Tabs、ProgressBar 与按钮六种状态。
- 所有纯图标按钮具有 Tooltip、accessibleName 和 36×36 目标。

**GREEN behavior:**
- “仅译文”通过 Reader CSS 隐藏 `.mercury-original`；“双语”显示现有 Agent HTML；“原文”显示原始 fragment。
- 不解析或修改 TranslationAgent 的内部段落结构。
- CleaningPanel 的整体状态只反映现有 Reader 请求：loading、done/cached、error。

**Verification:**

```powershell
ruff format --check app/styles.py ui tests/test_ui
ruff check app/styles.py ui tests/test_ui
pytest tests/test_ui -q
pytest -q
git diff --check
```

仅在以上全部通过后更新 AGENTS.md 的 UI 里程碑；不得把未修改的核心 Agent 或 Reader 管线标记为本次完成。

**Commit:** `feat(ui): complete adaptive reader experience`

## Final Review

- 每个 Task 必须经过独立规格/质量审查。
- 最终审查重点确认没有 `core/` 或 `store/` diff。
- 人工检查浅色/深色、三栏/双栏/沉浸、Reader 对照和 AI 抽屉。
- 每次发现跨成员冲突，先追加到 `docs/UI_INTEGRATION_ISSUES.md` 并在用户进度更新中说明；不得静默绕过。
