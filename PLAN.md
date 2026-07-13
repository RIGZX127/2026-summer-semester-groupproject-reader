# Mercury 跨平台版 — 项目执行计划

本文档定义了将 Mercury RSS 阅读器复现为跨平台（Windows / macOS / Linux）Python + PySide6 应用的分阶段执行计划。

**指导原则**：每个任务产出一个可运行、可验收的增量。在每 2–3 个功能里程碑之后穿插一个重构里程碑，以控制代码复杂度（熵）的增长。

---

## 总览

| 阶段 | 名称 | 关键里程碑 |
|------|------|-----------|
| Phase 0 | 文档与架构 | INIT、AGENTS、PLAN |
| Phase 1 | 基础搭建 | 数据库 Schema、Feed 同步、基础 UI 脚手架 |
| Phase 2 | 核心 Reader | Reader 管线、文章管理、UI 打磨与重构 |
| Phase 3 | AI Agent | Agent 运行时、摘要、翻译 |
| Phase 4 | 标签系统 | 本地打标、标签 Agent、标签管理 UI |
| Phase 5 | 笔记与导出 | 笔记、Digest 导出、用量统计、国际化 |
| Phase 6 | 质量加固 | 跨平台 CI、最终重构、打包发布 |

---

## Phase 0 — 文档与架构 ✅

### 任务 0.1 — INIT.md（人类起草）
- **核心目标**：确立项目范围、技术栈和功能清单。
- **受影响文件**：`INIT.md`
- **验收标准**：人工审核确认所有主要功能和约束均已记录。

### 任务 0.2 — AGENTS.md（AI 生成，人工审核）
- **核心目标**：将所有架构决策、编码约定和硬性规则编码固化，供 AI Agent 在整个项目中遵守。
- **受影响文件**：`AGENTS.md`（新建）
- **验收标准**：人工审核确认 INIT.md 中的所有决策均已体现，无模糊规则。

### 任务 0.3 — PLAN.md（AI 生成，人工审核）
- **核心目标**：产出包含可验收任务的完整分阶段执行计划。
- **受影响文件**：`PLAN.md`（新建）
- **验收标准**：人工确认各阶段排序合理，每个任务有明确的验收标准。

---

## Phase 1 — 基础搭建

### 里程碑 1.1 — 项目脚手架

**核心目标**：建立可运行的项目骨架，包含正确的目录结构、依赖管理和程序入口。

**任务详情**：
- 创建 `pyproject.toml`，固定所有依赖版本（PySide6 ≥ 6.5、httpx、feedparser、beautifulsoup4、lxml、readability-lxml、markdownify、mistune、openai、jinja2、ruff、pytest、pytest-asyncio、pytest-qt、qasync）。
- 创建 `main.py` 作为程序入口（实例化 `QApplication`，加载 `MainWindow`，启动事件循环）。
- 按 `AGENTS.md §6` 的结构创建所有目录。
- 在 `app/state.py` 中添加初始 `AppState` dataclass（字段暂为空）。
- 在 `app/styles.py` 中建立集中式 QSS 与基础设计常量（字体、间距、圆角、状态样式），避免在各组件中散落内联样式。

**受影响文件**（均为新建）：
- `pyproject.toml`
- `main.py`
- `app/__init__.py`、`app/app.py`、`app/state.py`、`app/styles.py`
- 各模块目录下的所有 `__init__.py`

**关键设计**：
- 使用 `uv` 或 `pip` + `pyproject.toml` 进行依赖管理。
- `QApplication` 必须调用 `setOrganizationName("Mercury")` 和 `setApplicationName("Mercury")`，以正确限定 `QSettings` 的作用域。

**验收标准**：
- 在 Windows、macOS、Linux 上执行 `python main.py` 均可启动空窗口，无报错。
- `ruff check .` 报告零问题。
- `pytest` 报告零失败（此时尚无测试用例，仅验证收集阶段）。

---

### 里程碑 1.2 — 数据库 Schema 与迁移

**核心目标**：建立所有 Store 模块依赖的 SQLite Schema 和迁移系统。

**任务详情**：
- 实现 `store/db.py`：`DatabaseManager` 类，以 WAL 模式打开 SQLite 连接，在打开时执行迁移，暴露 `connection` 属性。
- 实现 `store/migrations.py`：版本化迁移器。每个迁移为一个标注版本整数的函数，`migrate(conn)` 按序执行所有未应用的迁移。
- 定义初始 Schema（迁移 v1）：
  - `feeds`：`id, url, title, description, favicon_url, created_at, updated_at`
  - `entries`：`id, feed_id, guid, url, title, summary, author, published_at, is_read, is_starred, is_deleted, created_at`
  - `content`：`id, entry_id, source_html, cleaned_html, markdown, reader_version, markdown_version, render_version, fetched_at`
  - `notes`：`id, entry_id, body, updated_at`
  - `tags`：`id, name, normalized_name, created_at`
  - `entry_tags`：`entry_id, tag_id`
  - `tag_aliases`：`alias, canonical_tag_id`
  - `agent_runs`：`id, entry_id, agent_type, status, result_json, error, started_at, finished_at`
  - `llm_usage`：`id, provider, model, agent_type, prompt_tokens, completion_tokens, created_at`
  - `app_settings`：`key, value`（用户偏好键值存储）
- 实现 `store/feed_store.py`、`store/entry_store.py`，包含基础 CRUD。

**受影响文件**（均为新建）：
- `store/db.py`
- `store/migrations.py`
- `store/feed_store.py`
- `store/entry_store.py`

**关键设计**：
- `DatabaseManager` 以数据库路径作为构造参数，测试时传入 `":memory:"`。
- 迁移版本通过 `PRAGMA user_version` 存储。
- 所有 Store 方法为 `async` 包装，使用 `asyncio.get_event_loop().run_in_executor()` 处理阻塞的 sqlite3 调用。

**验收标准**：
- `pytest tests/test_store/` 通过：迁移在新的内存数据库上干净运行，Feed/Entry 基础 CRUD（增删改查）均通过。
- 在三个平台上执行 `python -c "from store.db import DatabaseManager; ..."` 均可打开真实的磁盘数据库，无报错。

---

### 里程碑 1.3 — Feed 解析与同步

**核心目标**：解析 RSS/Atom/JSON Feed 并通过 GUID 去重将文章同步到数据库。

**任务详情**：
- 实现 `core/feed/parser.py`：异步 `parse_feed(url) -> FeedData`，基于 `feedparser`，返回包含 `title, url, entries[]` 的 `FeedData` dataclass。
- 实现 `core/feed/sync.py`：`SyncService`，包含 `async sync_feed(feed_id)` 和 `async sync_all(concurrency=5)`（使用 `asyncio.TaskGroup`），通过 `entry.guid` 实现增量去重。
- 实现 `core/feed/opml.py`：`import_opml(xml_str) -> list[FeedUrl]` 和 `export_opml(feeds) -> str`。
- 为 `SyncService` 配置 Qt 信号，用于上报同步进度和完成事件。

**受影响文件**（均为新建）：
- `core/feed/parser.py`
- `core/feed/sync.py`
- `core/feed/opml.py`

**关键设计**：
- `FeedData`、`EntryData` 为普通 `dataclasses.dataclass`（非数据库模型）。
- `SyncService` 接收 `DatabaseManager`，不自行持有连接。
- 并发限制通过 `asyncio.Semaphore` 实现。

**验收标准**：
- `pytest tests/test_feed/` 通过：解析真实/fixture RSS URL 返回非空文章列表；重复同步同一 Feed 后数据库中无重复 GUID。
- OPML 导入/导出往返测试通过。

---

### 里程碑 1.4 — 基础 UI 脚手架

**核心目标**：实现带侧边栏（Feed 列表）、文章列表和 Reader 面板的三栏布局，建立统一页面状态、交互反馈和界面状态恢复机制，使 Feed 的增删流程端到端可用。

**任务详情**：
- 先整理主窗口信息架构和交互状态矩阵，明确侧边栏、文章列表、Reader 的 `empty`、`loading`、`content`、`error`、`offline`、`disabled` 状态及其切换条件。
- 实现 `ui/main_window.py`：`QMainWindow`，使用 `QSplitter` 实现三栏布局；窗口尺寸、位置和分栏比例通过 `QSettings` 保存并恢复。
- 实现 `ui/sidebar.py`：基于 `QListWidget` 的 Feed 列表，显示 Feed 标题和未读数；长名称截断并提供 Tooltip。
- 实现 `ui/entry_list.py`：基于 `QListWidget` 的文章列表，提供明确的选中态、空状态和加载状态。
- 实现 `ui/reader/reader_view.py`：封装 `QWebEngineView`，初始显示引导型空状态而非空白区域。
- 实现 `ui/dialogs/add_feed_dialog.py`：URL 输入、格式校验、提交中状态、错误原因和重试入口。
- 打通链路：添加 Feed → 解析标题 → 持久化 → 刷新侧边栏 → 同步 → 填充文章列表；超过 200ms 的操作显示非阻塞加载反馈。
- 为图标按钮补充 Tooltip 和可访问名称，设置合理的键盘焦点顺序；所有用户可见字符串从首次实现起接入 `tr()`。

**受影响文件**（均为新建）：
- `ui/main_window.py`
- `ui/sidebar.py`
- `ui/entry_list.py`
- `ui/reader/reader_view.py`
- `ui/dialogs/add_feed_dialog.py`
- `app/app.py`（接线）
- `app/styles.py`（补充页面状态和基础控件样式）

**关键设计**：
- Phase 1 中侧边栏和文章列表使用 `QListWidget`（若 Phase 2 重构时发现性能问题，可迁移至 `QAbstractItemModel`）。
- UI 仅发送用户意图并展示结果，通过 UseCase、Controller 或明确接口获取数据，不直接执行数据库、网络或 Feed 解析逻辑。
- 异步结果通过 `PySide6.QtCore.Signal` 回传主线程；禁止使用 `pyqtSignal`，禁止在非主线程更新 UI。
- Feed 同步和文章加载事件携带 `feed_id`、`entry_id` 或 `request_id`，UI 更新前校验当前选择，忽略过期结果。
- `AppState.feeds: list[FeedRow]`，`AppState.selected_feed_id: int | None`。

**验收标准**：
- 人工验收：启动应用，未选择 Feed 时显示明确空状态；输入真实 RSS Feed URL 后显示提交中反馈，成功后侧边栏显示 Feed 标题和未读数，文章列表填充文章标题。
- 模拟无网络、无效 URL 和同步失败时，界面显示原因并提供重试入口，不出现空白区域或窗口假死。
- 重启应用后窗口尺寸和三栏比例正确恢复；鼠标和键盘均可完成 Feed 的添加、同步和选择。
- `pytest-qt` 覆盖主窗口启动、三栏布局、页面状态切换和过期请求过滤。
- 在三个平台上进行 Feed 的增加、同步、选择操作均无崩溃，关键控件无截断。

---

## Phase 2 — 核心 Reader

### 里程碑 2.1 — Reader 管线（获取 + 提取 + 转换）

**核心目标**：点击文章后，Reader 面板加载并显示清洗后的 Markdown 内容。

**任务详情**：
- 实现 `core/reader/pipeline.py`：`ReaderPipeline`，包含 `async build(entry_id) -> RenderedContent`。阶段：Fetch（httpx）→ Extract（readability-lxml）→ Convert（markdownify）→ 缓存至 `content` 表。
- 实现 `core/reader/readability.py`：对 `readability.Document` 的薄封装，返回 `cleaned_html, title, byline`。
- 实现 `core/reader/markdown.py`：`html_to_markdown(html: str) -> str`，使用 `markdownify`。
- 实现 `core/reader/cache.py`：检查 `content` 表中的缓存版本，版本号递增时失效。
- 实现 `store/content_store.py`。
- 将 `reader_view.py` 与管线对接，通过 `setHtml()` 渲染；加载时显示占位层，失败时回退到 Feed 摘要或原始内容并提供重试。

**受影响文件**（均为新建）：
- `core/reader/pipeline.py`
- `core/reader/readability.py`
- `core/reader/markdown.py`
- `core/reader/cache.py`
- `store/content_store.py`

**关键设计**：
- `RenderedContent`：`dataclass(html: str, title: str, byline: str, from_cache: bool)`。
- 缓存键：`(entry_id, reader_version, markdown_version)`。版本常量定义在 `pipeline.py` 中。
- 管线为顺序执行，单篇文章加载过程中无并发。
- Reader 加载事件必须携带并校验 `entry_id` 和 `request_id`，切换文章后忽略过期结果。
- Reader 模式默认禁用 JavaScript 和本地文件访问；外部链接交由系统浏览器打开。

**验收标准**：
- `pytest tests/test_reader/` 通过：管线对 fixture HTML 字符串运行，产出非空 Markdown；缓存命中时重跑返回 `from_cache=True` 且不重新请求。
- 人工验收：点击文章后先显示加载占位，再显示格式化内容（而非原始 HTML）；快速切换文章时不得闪回上一篇内容。
- 模拟正文提取失败和离线状态时，Reader 显示回退内容、错误原因和重试入口；外部链接在系统浏览器中打开。

---

### 里程碑 2.2 — 文章管理（已读/收藏/搜索/删除）

**核心目标**：完整的文章状态管理：标记已读/未读（批量）、收藏/取消收藏、搜索、软删除。

**任务详情**：
- 在 `entry_store.py` 中新增方法：`mark_read`、`mark_unread`、`batch_mark_read`、`toggle_star`、`search(query, feed_id=None) -> list[EntryListItem]`、`soft_delete`。
- 新增 `EntryListItem` dataclass（轻量级：`id, title, summary_snippet, author, published_at, is_read, is_starred`）。
- 更新 `ui/entry_list.py`：显示已读/未读状态、收藏徽章，状态不得只依赖颜色表达；支持右键菜单（标记已读、收藏、删除）。
- 在文章列表上方添加搜索栏组件，明确显示当前 Feed、筛选条件和搜索范围；刷新结果时尽量保留选中项和滚动位置。
- 删除操作提供确认或撤销入口；成功反馈优先使用状态栏或界面内提示，避免无必要弹窗。

**受影响文件**：
- `store/entry_store.py`（扩展）
- `ui/entry_list.py`（扩展）
- `ui/main_window.py`（接入搜索栏）

**关键设计**：
- Phase 2 中搜索仅针对 `Entry.title` 和 `Entry.summary` 字段（不使用 FTS 全文索引）。
- 批量已读操作的作用范围为当前 Feed + 当前筛选条件，而非仅当前页。
- 软删除设置 `is_deleted=1`，所有查询默认排除已删除文章。

**验收标准**：
- `pytest tests/test_store/test_entry_store.py` 通过：标记已读持久化，批量标记已读影响范围正确，搜索仅返回匹配文章。
- 人工验收：批量标记多篇文章为已读后，侧边栏未读数正确更新；已读/收藏状态在灰度模式下仍可辨识。
- 搜索、筛选和刷新后尽量保留当前选中项及滚动位置；软删除操作有确认或撤销反馈。

---

### 里程碑 2.3 — UI 打磨 + 重构

**核心目标**：完善 Reader 主题与阅读体验、三种阅读模式（Reader/Web/双栏）、OPML 导入导出 UI，并完成第一轮跨平台、可访问性和性能重构。

**任务详情**：
- 实现 `ui/reader/theme.py`：`Theme` dataclass，包含 `font_family, font_size, line_height, content_width, background, text_color`。
- 实现 `ui/reader/theme_manager.py`：集中生成 Reader CSS，并通过 `QSettings` 保存字体、字号、行高、内容宽度和主题设置；修改后即时生效。
- 实现 `ui/reader/reader_toolbar.py`：模式切换（Reader/Web/双栏）、主题控制；纯图标按钮提供 Tooltip、可访问名称和键盘操作。
- Reader 正文适配图片、长链接、表格和代码块，避免撑破内容区域；建立清晰的标题、正文、引用和代码层级。
- Reader/Web/双栏模式切换时保留当前文章，并尽量保存与恢复滚动位置。
- 在“文件”菜单中通过 `ui/dialogs/` 添加 OPML 导入/导出功能，统一使用 `platform/file_dialog.py`，并提供处理中、成功、部分失败和错误反馈。
- 检查常见窗口尺寸、高 DPI、中文/英文混排和长标题场景，避免关键控件截断或不可操作。
- 重构：若 500 篇文章的列表渲染耗时超过 200ms，将文章列表迁移至 `QAbstractListModel`；大量数据刷新时保持主线程可交互。

**受影响文件**：
- `ui/reader/theme.py`（新建）
- `ui/reader/theme_manager.py`（新建）
- `ui/reader/reader_toolbar.py`（新建）
- `ui/dialogs/opml_dialog.py`（新建）
- `ui/reader/reader_view.py`（扩展）
- `ui/entry_list.py`（可能重构）
- `ui/sidebar.py`（可能重构）
- `app/styles.py`（统一控件和状态样式）

**验收标准**：
- 人工验收：在 Reader/Web/双栏模式之间切换时当前文章不变，滚动位置尽量保持；修改字体、字号、行高和内容宽度后即时生效，重启应用后设置仍保留。
- 图片、长链接、表格和代码块在常见窗口宽度下不溢出；125%、150%、200% 缩放下关键控件无截断。
- 导入包含 20 个 Feed 的 OPML 文件时显示进度和结果摘要，所有成功导入的 Feed 均出现在侧边栏，失败项可查看原因。
- `pytest-qt` 覆盖主题更新、设置恢复、模式切换和中英文布局；500 篇文章列表渲染或刷新不导致界面明显卡死。

---

## Phase 3 — AI Agent

### 里程碑 3.1 — Agent 运行时 + 提供者设置

**核心目标**：建立共享的 Agent 运行时（状态机 + 任务队列）和 LLM 提供者/模型配置 UI。

**任务详情**：
- 实现 `core/agent/runtime.py`：`AgentRuntime` 单例，状态机覆盖 `idle → queued → running → done | error | cancelled`。等待槽位最多 1 个（最新替换），取消仅来自用户操作。通过 `PySide6 Signal` 广播 `AgentUIEvent`（`run_id, entry_id, agent_type, status, chunk, progress, error, result_json`），UI 更新前校验 `entry_id` + `run_id`。
- 实现 `core/agent/stream_buffer.py`：流式 chunk 缓冲器，80ms 合并窗口，合并后一次性发送信号避免高频重绘。各 Agent 不得绕过缓冲区直接发送 UI 信号。
- 实现 `core/agent/providers.py`：`ProviderConfig` dataclass，`LLMRouter` 执行主模型 → 回退模型路由（主模型连续 2 次失败后切换）。异步 `chat_stream()` 返回异步生成器。`api_key` 使用系统凭据存储（`keyring`），不存数据库或日志。每次调用后记录用量到 `llm_usage`。
- 实现 `core/agent/template_loader.py`：内置模板路径 `resources/prompts/*.default.yaml`，沙盒覆盖路径 `<用户数据目录>/prompts/*.yaml`。首次自定义从内置复制且不覆盖已有沙盒文件。模板格式 YAML（`version, model, system_prompt, user_prompt_template, config`），`user_prompt_template` 使用 Jinja2 语法。
- 实现 `store/agent_store.py`：持久化 Agent 运行状态和结果（`AgentRun` dataclass），提供缓存查询接口。
- 实现 `store/usage_store.py`：记录单次用量、按维度聚合查询、时间线查询。
- 实现 `ui/settings/provider_panel.py`：提供者增删改、非阻塞连接测试（调 `/v1/models` 获取模型列表）、密码掩码输入框。覆盖 `idle`/`testing`/`success`/`error` 状态。
- 实现 `ui/settings/agent_panel.py`：按 Agent 类型（摘要/翻译/标签）的提供者/模型选择、提示词模板编辑与恢复默认、摘要特有设置（语言、自动摘要开关、详细程度）、翻译特有设置（并发段落数 1–5）。

**受影响文件**（均为新建）：
- `core/agent/runtime.py`、`providers.py`、`template_loader.py`、`stream_buffer.py`
- `store/agent_store.py`、`usage_store.py`
- `ui/settings/provider_panel.py`、`agent_panel.py`
- `resources/prompts/summary.default.yaml`、`translation.default.yaml`、`tagging.default.yaml`

**关键设计**：
- `AgentRuntime` 为模块级单例，通过 `AppState.agent_runtime` 访问。
- Qt 信号统一使用 `PySide6.QtCore.Signal`；UI 统一识别 `idle`、`queued`、`running`、`done`、`error`、`cancelled` 状态，并在更新前校验 `entry_id` 与 `run_id`。
- 提示词模板 YAML 格式，内置与沙盒双层覆盖，版本追溯。
- 用量在每次 LLM 调用后由 `LLMRouter` 自动写入，失败调用也记录（`completion_tokens=0`）。

**验收标准**：
- `pytest tests/test_agent/` 通过：状态机全路径覆盖、mock LLM 流式 5 chunk、最新替换策略、取消正确广播、流式缓冲合并正确。
- 人工验收：添加 Ollama 提供者连接测试成功并显示模型列表；未配置 Provider 时显示设置入口；编辑提示词模板后沙盒生效，恢复默认后回退内置模板。

---

### 里程碑 3.2 — 摘要 Agent

**核心目标**：流式生成文章摘要并实时显示。支持手动触发和 1 秒防抖自动触发。

**任务详情**：
- 实现 `core/agent/summary.py`：`SummaryAgent.generate(entry_id, triggered_by)`。流程：获取文章 Markdown → 查缓存（缓存键 `(entry_id, provider_id, model, prompt_version)`，四字段全匹配走缓存） → Jinja2 渲染提示词 → 流式调用 → 存 `agent_runs.result_json`。`triggered_by` 区分 `"manual"` | `"auto"`，`detail_level` 映射 `brief`（1–2 句）/ `standard`（3–5 句）/ `detailed`（要点式详细摘要）。
- 实现 `ui/reader/summary_panel.py`：位于 Reader 下方，可折叠。覆盖 6 个状态（`idle`/`queued`/`running`/`done`/`error`/`cancelled`），流式文本缓冲节流更新（追加而非全量替换）。自动/手动触发标记区分。
- 自动摘要：`QTimer.singleShot(1000)` 防抖，仅文章内容加载完成后且设置中开启时触发。快速切换文章取消前一定时器和排队任务。
- 摘要文本支持选中和复制，存储为 JSON：`{"summary": "...", "model": "...", "prompt_version": 1, "detail_level": "...", "language": "..."}`。

**受影响文件**（均为新建）：
- `core/agent/summary.py`
- `ui/reader/summary_panel.py`
- `resources/prompts/summary.default.yaml`

**关键设计**：
- 目标语言和详细程度可在设置中按提供者配置。
- 缓存命中时直接返回，不重新调用 LLM。`detail_level` 变更后缓存失效。
- `running` 状态提供取消入口；`error` 状态保留已生成内容并提供重试，不以弹窗打断阅读。

**验收标准**：
- `pytest tests/test_agent/test_summary.py` 通过：mock 流式 5 chunk 完整拼接；缓存命中不调 LLM；`detail_level` 变更后缓存失效。
- 人工验收：流式更新流畅、快速切换文章不污染当前面板、取消后已生成文本保留、自动摘要防抖生效、失败显示原因和重试。

---

### 里程碑 3.3 — 翻译 Agent

**核心目标**：按段翻译，在 Reader 中内联渲染双语对照内容。

**任务详情**：
- 实现 `core/agent/translation.py`：`TranslationAgent.translate(entry_id)`。使用 `beautifulsoup4` 将文章按 `p/ul/ol` 顶级块分割，以 `asyncio.Semaphore(degree)` 控制并发（默认 3，范围 1–5），逐段调用 LLM 翻译。每段上下文包含前一段原文+译文以提升连贯性。组装双语 HTML（原文与译文交错排列，译文缩进+浅色背景+斜体）。翻译为纯手动触发（不自动触发）。
- 扩展 `ui/reader/reader_toolbar.py`：翻译按钮状态同步（`idle`→翻译图标，`queued`→置灰+旋转，`running`→取消图标+进度%，`done`→翻译图标，`error`→⚠+重试）。
- 扩展 `ui/reader/reader_view.py`：原文/双语/仅译文三种模式切换，切换时保持滚动位置。翻译过程中渐进式渲染已完成段落（增量 `setHtml()` + 恢复滚动位置）。切换文章校验 `run_id` 丢弃过期结果。
- 翻译缓存：再次打开已翻译文章时从 `agent_store` 取缓存直接渲染双语视图。失败恢复粒度：段落级别，已完成段落保留，仅"重试失败段落"。

**受影响文件**（均为新建/扩展）：
- `core/agent/translation.py`（新建）
- `ui/reader/reader_toolbar.py`（扩展：翻译按钮与状态同步）
- `ui/reader/reader_view.py`（扩展：双语渲染、模式切换、滚动保持）
- `resources/prompts/translation.default.yaml`（新建）

**关键设计**：
- 分段契约严格锁定 `p`、`ul`、`ol` 顶级块。此设计已固定，若变更必须同步更新 `AGENTS.md`。
- 并发由 `asyncio.Semaphore(degree)` 控制，`degree` 在设置中可调（1–5）。
- 翻译为纯手动触发（与摘要的防抖自动触发不同）。渐进式渲染下保持滚动位置。
- 失败时保留已完成段落，标记失败段落并提供重试，不清空现有 Reader 内容。

**验收标准**：
- `pytest tests/test_agent/test_translation.py` 通过：5 段 HTML 分段正确、并发控制有效、双语 HTML 正确、失败段标记正确、取消后状态广播正确。
- 人工验收：双语对照清晰、三种模式切换流畅+滚动保持、取消后已翻段落保留、切换文章不污染、部分失败后"重试失败段落"不重复翻译成功段。

---

## Phase 4 — 标签系统

### 里程碑 4.1 — 标签系统核心

**核心目标**：扁平标签结构，支持三层去重管线、手动标签分配和按标签筛选。

**任务详情**：
- 实现 `core/tags/normalizer.py`：`normalize(tag) -> str`（去空白、CJK 感知大小写、全角转半角、空格压缩，幂等操作）；`resolve_alias(tag) -> canonical_tag`。CJK 字符检测：含 CJK 则跳过大小写转换。
- 实现 `core/tags/cooccurrence.py`：`get_cooccurring_tags(tag_ids, min_cooccurrence=2)`，查询与给定标签集共享 ≥2 篇文章的其他标签，排除已有标签，按共现数降序返回 Top 10。
- 实现 `store/tag_store.py`：`TagLibraryStore`（CRUD、重命名、合并、软删除，创建时幂等：同名规范化标签返回已有记录）、`TagBatchStore`（批量打标、按标签筛选 Any/All 模式）、`TemporaryTagManager`（临时标签计数，达到阈值默认 3 次后自动升级为正式标签。计数存 `app_settings`，正式升级后删除键值对）。
- 实现 `ui/dialogs/tag_manager_dialog.py`：标签列表+搜索、重命名（双击内联编辑）/合并/删除、标签详情面板（关联文章数、共现推荐）。
- 在文章详情视图添加标签徽章区域：可换行 `FlowLayout`、× 删除按钮（悬停显示）、+ 搜索/创建下拉框（实时搜索已有标签，无匹配时显示创建选项）。徽章颜色基于规范化名称 hash 映射到预设调色板，确保同标签同色。
- 扩展 `ui/sidebar.py`：标签筛选栏（多选最多 5 个，Any/All 模式切换按钮，高亮徽章+清除入口）。筛选激活时文章列表标题栏显示当前筛选条件和结果数。

**受影响文件**（均为新建）：
- `core/tags/normalizer.py`、`cooccurrence.py`
- `store/tag_store.py`
- `ui/dialogs/tag_manager_dialog.py`
- `ui/reader/reader_view.py`（扩展：标签徽章区域）
- `ui/sidebar.py`（扩展：标签筛选栏）

**关键设计**：
- 标签为扁平结构（无层级）。`tags.name`（显示名）与 `tags.normalized_name`（去重匹配）分离存储。
- 三层去重顺序固定：输入 → `normalize()` → `tags.normalized_name` → `tag_aliases` → canonical tag。规范化操作幂等。
- 临时标签由 Tag Agent 或手动输入触发，达到使用阈值（默认 3 次，可在设置中调整）后自动升级为正式标签，历史文章关联回填。
- 标签筛选与 Feed 筛选叠加时取交集（Feed 范围 ∩ 标签范围）。

**验收标准**：
- `pytest tests/test_tags/` 通过：规范化幂等、CJK 不转小写、别名解析正确、幂等创建、合并迁移正确、Any/All 筛选正确、临时标签升级（3 次后自动正式化）、共现推荐。
- 人工验收："Python"和"python"归一为同一标签；5 个多选标签不挤压关键控件；Any/All 切换后筛选结果立即变化；标签合并后源标签删除、目标标签关联数正确；同标签同色。

---

### 里程碑 4.2 — 标签 Agent

**核心目标**：LLM 驱动的文章标签建议功能。

**任务详情**：
- 实现 `core/agent/tagging.py`：`TagAgent.suggest_tags(entry_id)`，获取文章内容 → 注入 `existing_tags`（用户已有标签库，用于避免语义重复） → 流式调用 LLM → 解析标签列表（期望 JSON 数组，回退按行分割提取） → 经三层去重管线 → 过滤已有标签 → 返回建议列表。`TagAgent.batch_tag(entry_ids)` 串行逐篇执行，广播进度，返回成功/失败/跳过统计。跳过内容为空的文章。
- 在文章详情标签徽章区域添加”建议标签”按钮：`running`→旋转动画，`done`→下拉面板显示建议列表（+ 一键添加 / ✕ 忽略），`error`→失败提示+重试。切换文章关闭面板并重置状态。
- 实现 `ui/dialogs/batch_tag_dialog.py`：文章列表+状态图标（⏳/🔄/✅/❌/⏭）、总进度条+百分比、成功/失败/跳过计数、当前处理文章标题、失败详情展开。取消确认（已完成保留），处理中不可关闭对话框。

**受影响文件**（均为新建）：
- `core/agent/tagging.py`
- `ui/dialogs/batch_tag_dialog.py`
- `ui/reader/reader_view.py`（扩展：建议标签按钮和下拉面板）
- `resources/prompts/tagging.default.yaml`

**关键设计**：
- Tag Agent 与本地标签共用同一去重管线，LLM 返回的标签同样经 `normalize()` → 精确匹配 → `resolve_alias()`。
- `existing_tags` 注入提示词指示 LLM 避免建议语义重复或过于宽泛的标签。
- 批量打标串行执行（避免 LLM 限流）。用户手动创建标签立即正式化，Agent 建议标签走临时标签升级机制。
- LLM 返回非 JSON 文本时回退按行解析。

**验收标准**：
- `pytest tests/test_agent/test_tagging.py` 通过：mock 返回 3 标签解析正确、去重管线正确、已有标签过滤、批量串行+进度正确、非 JSON 回退解析有效。
- 人工验收：单篇建议 3–5 秒返回、+ 一键添加、批量 10 篇显示实时进度、取消后已完成保留、建议不与已有标签重复。

---

## Phase 5 — 笔记、导出、用量统计与国际化

### 里程碑 5.1 — 笔记

**核心目标**：支持 5 秒自动保存的文章 Markdown 笔记。

**任务详情**：
- 实现 `store/note_store.py`：`get_note/save_note/delete_note`，async 方法通过 `run_in_executor` 包装阻塞调用，`asyncio.Lock` 防止连续保存的竞态条件。
- 实现 `ui/reader/note_editor.py`：`QPlainTextEdit` 编辑器位于 Reader 下方（`QSplitter` 分隔），状态栏显示 5 种保存状态（未修改/待保存/保存中/已保存/保存失败），配圆点颜色（灰/黄/蓝/绿/红）。`QTimer(5000)` 防抖自动保存，`textChanged` 重置计时器，`Ctrl+S` 立即保存。切换文章时若 dirty 先紧急保存并校验 `entry_id` 防止写入错误文章。无笔记时显示引导占位文字。

**受影响文件**（均为新建）：
- `store/note_store.py`
- `ui/reader/note_editor.py`
- `ui/reader/reader_view.py`（扩展集成）

**关键设计**：
- 笔记为纯文本（Markdown 原文存储），不做实时 Markdown 预览。自动/手动/切换文章三种触发共用 `save_note`。
- 保存操作为异步（`run_in_executor`），不阻塞 UI 主线程。保存结果按 `entry_id` 校验。

**验收标准**：
- `pytest tests/test_store/test_note_store.py` 通过：CRUD 正确，`updated_at` 更新，5 秒自动保存触发。
- `pytest-qt`：5 秒防抖、`Ctrl+S` 立即保存、切换文章前紧急保存、保存失败重试。
- 人工验收：输入不卡顿、切换文章笔记不丢失、无笔记显示引导占位、保存失败保留编辑内容并提供重试。

---

### 里程碑 5.2 — Digest 导出

**核心目标**：通过 Jinja2 模板将单篇或多篇文章导出为 Markdown 文件（Hugo 兼容格式）。

**任务详情**：
- 实现 `core/digest/exporter.py`：`DigestExporter` 类，单篇/多篇导出、模板列表、预览（前 500 字符截断）。模板变量：`title, url, author, published_at, feed_title, summary, notes, tags, content_markdown`。多篇导出时按 `published_at` 降序排列。默认文件名 `{date}_{title_slug}.md`。模板自动发现（`resources/templates/*.j2` + 用户模板目录）。
- 创建内置模板：`single.md.j2`（Hugo 兼容 frontmatter + 正文 + 笔记区域）、`multi.md.j2`（目录 + 分隔线 + 各篇文章）。
- 实现 `ui/dialogs/export_dialog.py`：导出范围摘要、模板选择+预览区（只读 `QTextEdit`，切换模板自动刷新）、保存路径选择（`platform/file_dialog.py`，路径通过 `QSettings` 记忆）。导出状态覆盖 `idle`/`exporting`/`success`（可点击路径定位文件）/`error`（原因+重试）。

**受影响文件**（均为新建）：
- `core/digest/exporter.py`
- `ui/dialogs/export_dialog.py`
- `ui/reader/reader_toolbar.py`（扩展：导出按钮）
- `ui/entry_list.py`（扩展：右键菜单导出选项）
- `resources/templates/single.md.j2`、`multi.md.j2`

**关键设计**：
- 模板引擎 Jinja2（与 Agent 提示词共用）。导出不修改数据库，仅读取并渲染。Hugo 兼容 frontmatter（YAML，`---` 分隔）。
- 多篇导出文章按 `published_at` 降序。导出文件名可用户覆盖。

**验收标准**：
- `pytest tests/test_digest/` 通过：单篇 frontmatter + 内容正确、多篇数量+分隔正确、变量缺失不报错。
- 人工验收：导出含笔记和标签的文章正确；多篇导出含目录；模板预览实时刷新；无写入权限时显示错误不崩溃；导出成功可点击定位文件。

---

### 里程碑 5.3 — 用量统计 UI

**核心目标**：展示按提供者 / 模型 / Agent 类型分组的 LLM 用量统计（调用次数 + Token 数）。

**任务详情**：
- 扩展 `store/usage_store.py`：按维度聚合查询（`group_by` + 日期范围）、时间线查询（按天/周/月）、清除历史数据（需确认操作，不可撤销）。
- 实现 `ui/settings/usage_panel.py`：顶部汇总卡片行（总调用次数/总 Prompt Token/总 Completion Token/估算费用，含环比变化%）、`QTableView` 分组表格（热力渐变着色、列排序、`Ctrl+C` 复制 TSV）、日期范围筛选（预设 + 自定义 `QDateEdit`）、趋势图（`QChart` 柱状图，若不可用退到纯表格）。覆盖 `empty`/`loading`/`content`/`error` 状态。

**受影响文件**（均为新建/扩展）：
- `store/usage_store.py`（扩展：聚合查询方法）
- `ui/settings/usage_panel.py`（新建）
- `ui/settings/settings_dialog.py`（扩展：用量统计标签页）

**关键设计**：
- 用量数据由 `LLMRouter` 在每次调用后自动写入，`usage_panel` 仅读取展示。
- 价格表存 `app_settings`（`key=pricing:<model_name>`），内置常见模型默认价格，用户可自定义。费用实时估算不存库（避免价格变更后历史费用不准）。
- 表格支持 `Ctrl+C` 复制选中行到剪贴板（TSV 格式，可粘贴到 Excel）。

**验收标准**：
- `pytest tests/test_store/test_usage_store.py` 通过：聚合分组正确、日期筛选边界、清除历史。
- 人工验收：5 次摘要+1 次翻译+10 篇批量打标后，汇总卡片显示 16 次调用 + Token 总数正确；按 Agent 类型分组正确；日期筛选生效；无数据时显示引导；清除历史弹确认。

---

### 里程碑 5.4 — 国际化（中文 + 英文）

**核心目标**：完整的 UI 字符串外化，支持中文和英文。

**任务详情**：
- 字符串外化审查：所有 `ui/` 目录中的用户可见字符串使用 `self.tr()` / `QCoreApplication.translate()`，禁止硬编码。动态拼接字符串尽量模板化。
- 源语言策略：代码中默认中文原文（项目团队以中文沟通、初期目标用户为中文用户），英文通过 `.ts` 翻译文件提供。使用 `pyside6-lupdate`（PySide6 对应工具）提取可翻译字符串，生成 `resources/i18n/mercury_zh.ts` 和 `mercury_en.ts`，再通过 `lrelease` 编译为 `.qm` 供运行时加载。`.qm` 不提交 Git（CI 自动生成），仅提交 `.ts` 源文件。
- 运行时切换：`app/app.py` 启动时检测 `QLocale.system().name()` + `app_settings` 覆盖 + `QSettings` 持久化语言偏好。利用 `QEvent.LanguageChange` + `retranslateUi()` 自动刷新所有组件文字，切换时保持当前页面状态。
- 布局验证：英文文本通常较长，使用弹性布局+截断（`QFontMetrics.elidedText()`）+Tooltip。在 Windows（100%/125%/150% DPI）、macOS（Retina）、Linux（GNOME 常见缩放）上验证中英文均无控件截断或重叠。

**受影响文件**：
- 全部 `ui/` 文件（`tr()` 审查与修复）
- `resources/i18n/mercury_zh.ts`、`mercury_en.ts`（新建）
- `app/app.py`（扩展：语言加载与 `changeEvent` 切换逻辑）
- `ui/settings/settings_dialog.py`（扩展：语言选择下拉框）
- `platform/paths.py`（扩展：语言环境检测）

**关键设计**：
- 翻译仅覆盖 UI 层用户可见字符串。`core/` 和 `store/` 中的错误日志和异常消息使用英文（面向开发者），不纳入翻译。
- 翻译文件命名遵循 Qt 惯例：`<appname>_<language>.ts`，新增语言（如日语 `mercury_ja.ts`）无需修改代码。
- 源语言策略在 `AGENTS.md` 中明确记录。

**验收标准**：
- `pytest tests/test_i18n/` 通过：两 `.ts` 文件存在且格式有效，翻译键集合一致，`lrelease` 编译无错误。
- `pytest-qt`：中英文布局控件可见性+最小尺寸检查通过、语言切换后文字正确更新、语言偏好通过 `QSettings` 持久化。
- 人工验收：中英文切换即时生效、英文界面不截断、长名称截断+Tooltip 展示全文、三平台 125%/150% 缩放无控件重叠、设置面板自身文字同步切换。

---

## Phase 6 — 质量加固、CI 与打包

### 里程碑 6.1 — 跨平台 CI

**核心目标**：建立在 `ubuntu-latest`、`windows-latest`、`macos-latest` 三个平台上运行的 GitHub Actions CI 矩阵。

**任务详情**：
- 编写 `.github/workflows/ci.yml`：矩阵覆盖 `[ubuntu-latest, windows-latest, macos-latest]`。
- 每个 Job：`pip install`、`ruff check`、`pytest tests/`（无头模式，不需要显示设备）。
- 独立 Job 用于需要显示设备的 `pytest-qt` 与 `QWebEngineView` 集成测试（Linux 使用 `xvfb-run`）。

**受影响文件**（均为新建）：
- `.github/workflows/ci.yml`

**验收标准**：
- 向主分支推送代码后，三个平台的 CI Job 全部通过。
- UI 测试至少覆盖：主窗口与三栏布局、Feed/文章切换、页面状态转换、错误重试、已读/收藏显示、过期 Agent 事件过滤、主题更新、设置恢复和中英文布局。

---

### 里程碑 6.2 — 最终重构与代码清理

**核心目标**：解决累积的技术债务：命名一致性、死代码清除、模块边界违规、性能问题。

**任务详情**：
- 执行 `ruff check --select ALL`，修复所有未豁免的问题。
- 审查所有模块是否存在边界违规（如 UI 层直接导入 Store 等）。
- 对 500 篇文章的文章列表进行性能分析，必要时迁移至 `QAbstractListModel`。
- 完成 Windows、macOS、Linux 的 UI/UX 人工巡检：常见分辨率、高 DPI、键盘导航、焦点顺序、Tooltip、可访问名称、空/加载/错误/离线状态和长文本布局。
- 检查 Reader/Web/双栏切换、流式输出、快速切换文章时的滚动位置、卡顿和过期结果问题。
- 更新 `AGENTS.md` 的最终状态和任何新发现的设计决策。

**验收标准**：
- `ruff check .` 报告零问题。
- `pytest` 在三个平台上 100% 通过。
- 人工审核确认无模块边界违规。
- 三个平台上关键流程无控件截断、窗口假死、仅靠颜色表达状态或键盘不可操作问题。

---

### 里程碑 6.3 — 打包发布

**核心目标**：生成适用于 Windows 的 `.exe` 安装包和 macOS 的 `.app` 应用包。Linux AppImage 为可选项。

**任务详情**：
- 使用 `PyInstaller`（或 `cx_Freeze`）打包 Python + PySide6 + 所有资源文件。
- 编写 `scripts/build_windows.ps1`、`scripts/build_macos.sh`。
- 将 `resources/prompts/`、`resources/templates/`、`resources/i18n/` 打包进发布包。

**受影响文件**（均为新建）：
- `mercury.spec`（PyInstaller 配置文件）
- `scripts/build_windows.ps1`
- `scripts/build_macos.sh`

**验收标准**：
- Windows：双击安装包，应用启动，在未安装 Python 的环境下 Feed 的增加/同步/阅读基础流程可用，窗口状态与主题设置可保存并恢复。
- macOS：打开 `.app` 包，完成同样的冒烟测试，检查菜单、文件对话框、高 DPI 和系统浏览器外链行为。
- Linux（若发布 AppImage）：完成同等 UI 冒烟测试，关键控件无截断且 Reader 可正常显示。

---

## 附录：更新协议

- **每个里程碑完成后**：更新 `AGENTS.md` 中"当前状态"章节。
- **每个 Phase 完成后**：为 Git 提交打上 `phase-N-done` 标签。
- **每当产生新的设计决策后**：添加到 `AGENTS.md` 中"关键设计决策"章节。
- **每当发现新问题或临时解决方案后**：添加到 `AGENTS.md` 中"已知问题"章节。