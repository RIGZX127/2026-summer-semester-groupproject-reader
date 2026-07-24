# Mercury 跨平台版 — AI 协作工程规范

本文件是 AI 编程 Agent 的参考手册，用于在整个代码库中保持一致的决策与约束。请保持本文件简洁、规定性强，聚焦于全仓库级别的规则。**每个重要里程碑后必须更新本文件。**

---

## 1. 项目目标

使用 Python + PySide6 构建一个跨平台（Windows / macOS / Linux）RSS 阅读器桌面应用，复现原始 Swift/macOS Mercury 项目的核心功能。应用遵循"本地优先、AI 增强、平台中立"的核心理念。

---

## 2. 架构原则

- **三层分离**：UI 层（`ui/`）↔ 核心逻辑层（`core/`）↔ 数据存储层（`store/`）。
- UI 仅负责展示、输入和交互状态，通过 UseCase、Controller 或明确接口获取数据；不得直接执行 SQL、HTTP、正文提取或 LLM 调用。
- UI 只能在 Qt 主线程更新；异步结果通过 PySide6 `Signal` 回传，耗时操作不得阻塞主线程。
- 文章加载、同步和 Agent 任务必须携带 `entry_id`、`run_id` 或 `request_id`，防止过期结果更新当前页面。
- AI Agent 任务必须经过共享的 AgentRuntime，禁止临时性的 async 直调。
- Reader 管线是严格的顺序管线：`Fetch → Extract（Readability）→ Convert（Markdown）→ Render（QWebEngineView）`，每个阶段独立版本化并缓存。
- 平台特定行为（文件对话框、剪贴板、路径、通知）必须隔离在 `platform/` 适配器中。Core 和 Store 模块不得包含任何平台特定代码。
- 所有跨模块通信使用有类型标注的 dataclass 或明确返回值。Store 层以外禁止使用可变的模块级全局变量。

---

## 3. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| UI 框架 | PySide6 (Qt 6) | 三平台原生渲染 |
| WebView | QWebEngineView | Chromium 内核，三平台一致 |
| 异步 I/O | asyncio + httpx + qasync | 所有网络请求和数据库读写；qasync 集成 asyncio 与 Qt 事件循环 |
| 数据库 | Python sqlite3（内建） | 不引入 ORM，使用原生 SQL + dataclass |
| Feed 解析 | feedparser | RSS / Atom / JSON Feed |
| HTML 解析 | beautifulsoup4 + lxml | lxml 底层为 C 实现的 libxml2 |
| 正文提取 | readability-lxml | Mozilla Readability 的 Python 移植版 |
| HTML → Markdown | markdownify | 清洗后 HTML 转为 Markdown |
| Markdown 渲染 | mistune | Markdown 渲染为 HTML，纯 Python，可扩展 |
| LLM 客户端 | openai (AsyncOpenAI) | 必须支持流式输出 |
| 提示词模板 | Jinja2 | Agent 提示词 + Digest 导出模板 |
| 代码格式化 | ruff | 替代 black + isort + flake8 |
| 测试框架 | pytest + pytest-asyncio + pytest-qt | 禁止使用 unittest.TestCase |
| Python 版本 | ≥ 3.11 | `tomllib`、`asyncio.TaskGroup` 所需 |
| Qt 版本 | ≥ 6.5 LTS | 稳定 QWebEngineView 所需 |

**禁止事项：**
- 禁止引入 ORM（SQLAlchemy、Django ORM、Peewee 等）
- 禁止直接使用 `threading.Thread` 进行 UI 更新，跨线程通信必须使用 Qt 信号/槽机制
- 禁止使用阻塞的 `requests` 库，改用异步的 `httpx`
- 禁止使用 `unittest.TestCase`，改用 pytest 普通函数形式

---

## 4. 平台目标

| 平台 | 最低版本 |
|------|---------|
| Windows | 10+ |
| macOS | 13+（Ventura） |
| Linux | Ubuntu 22.04+ |

所有功能必须在三个平台上通过，除非明确标注为平台特定功能。CI 必须覆盖三个平台。

---

## 5. 核心功能清单

1. **订阅源管理**：RSS/Atom/JSON Feed 的增删改，并发同步（2–10 路），增量更新（GUID 去重），15 分钟自动同步，OPML 导入/导出
2. **文章阅读**：三栏布局（侧边栏 / 文章列表 / 阅读详情），Reader/Web/双栏三种阅读模式，版本化内容管线缓存
3. **文章管理**：已读/未读（含批量），收藏/取消收藏，全文搜索（标题 + 摘要），软删除
4. **AI Agent**：摘要（流式、防抖自动触发），翻译（按段双语渲染），标签 Agent（LLM 建议），共享 AgentRuntime + 状态机
5. **标签系统**：扁平标签结构，三层去重管线（规范化 → 精确匹配 → 别名解析），共现推荐
6. **笔记与 Digest 导出**：文章 Markdown 笔记（5 秒自动保存），单篇/多篇导出（Hugo 兼容），Jinja2 模板驱动
7. **LLM 用量统计**：按提供者 / 模型 / Agent 类型维度的调用量与 Token 统计
8. **设置**：多 LLM 提供者/模型配置，连接测试，提示词模板自定义（内置 + 沙盒覆盖）
9. **国际化**：UI 字符串通过 Qt `tr()` / `QTranslator` 管理，内置中文和英文

---

## 6. 文件与模块结构

```
mercury-cross/
├── main.py                  # 程序入口
├── app/
│   ├── app.py               # QApplication 初始化，主窗口启动
│   ├── state.py             # AppState dataclass（全局状态唯一来源）
│   └── styles.py            # QSS 样式表，集中管理
├── ui/
│   ├── main_window.py       # QMainWindow，布局编排
│   ├── sidebar.py           # 订阅源侧边栏组件
│   ├── entry_list.py        # 文章列表组件
│   ├── reader/
│   │   ├── reader_view.py   # QWebEngineView 封装
│   │   ├── reader_toolbar.py
│   │   ├── html_renderer.py   # Markdown → HTML + QWebEngineView 渲染
│   │   ├── theme_manager.py   # Reader CSS 生成与主题设置持久化
│   │   └── theme.py         # Theme dataclass + CSS 生成
│   ├── settings/
│   │   ├── settings_dialog.py
│   │   ├── provider_panel.py
│   │   └── agent_panel.py
│   └── dialogs/             # OPML 导入导出、标签管理等对话框
├── core/
│   ├── feed/
│   │   ├── parser.py        # feedparser 封装
│   │   ├── sync.py          # 异步同步服务
│   │   └── opml.py          # OPML 导入/导出
│   ├── reader/
│   │   ├── pipeline.py      # Fetch → Extract → Convert 管线
│   │   ├── readability.py   # readability-lxml 封装
│   │   ├── markdown.py      # HTML → Markdown（markdownify）
│   │   └── cache.py         # 版本化管线缓存（存入数据库）
│   ├── agent/
│   │   ├── runtime.py       # AgentRuntime，状态机，任务队列
│   │   ├── summary.py       # SummaryAgent
│   │   ├── translation.py   # TranslationAgent（按段翻译）
│   │   ├── tagging.py       # TagAgent
│   │   └── providers.py     # LLM 提供者/模型路由（AsyncOpenAI）
│   └── tags/
│       └── normalizer.py    # 标签规范化 + 别名解析
├── store/
│   ├── db.py                # DatabaseManager（sqlite3，WAL 模式）
│   ├── migrations.py        # 版本化迁移管理器
│   ├── feed_store.py        # 订阅源 CRUD
│   ├── entry_store.py       # 文章 CRUD + 查询
│   ├── content_store.py     # Reader 管线缓存持久化
│   ├── tag_store.py         # 标签库 + 文章-标签映射
│   ├── agent_store.py       # Agent 运行状态持久化
│   ├── usage_store.py       # LLM 用量记录
│   └── note_store.py        # 文章笔记
├── platform/
│   ├── paths.py             # 平台特定数据/配置路径
│   ├── clipboard.py         # 跨平台剪贴板
│   └── file_dialog.py       # QFileDialog 封装
├── resources/
│   ├── prompts/             # *.default.yaml（Jinja2 提示词模板）
│   ├── templates/           # Digest 导出模板
│   └── i18n/                # Qt .ts 翻译文件
└── tests/
    ├── conftest.py
    ├── test_feed/
    ├── test_reader/
    ├── test_agent/
    ├── test_store/
    └── test_tags/
```

---

## 7. 编码约定

- **语言**：Python 3.11+。代码注释和 docstring 使用英文，与用户沟通使用中文。
- **类型标注**：所有公共函数和类属性必须有类型标注；数据结构使用 `dataclasses.dataclass`。
- **异步**：所有 I/O（网络、数据库读写、LLM 调用）必须是 `async`；并发任务使用 `asyncio.TaskGroup`。
- **Qt 线程安全**：禁止在非主线程调用 UI 方法；跨线程结果通过 PySide6 `Signal` 传回主线程。
- **全局状态**：应用级可变状态统一存放在 `AppState`，禁止模块级可变全局变量。
- **错误处理**：使用有类型的异常，不得静默吞错；Agent 和同步错误必须记录到调试面板。
- **文档规范**：注释和文档中禁止使用 emoji。
- **源语言策略**：代码中用户可见字符串默认使用中文原文。英文及其他语言通过 `resources/i18n/*.ts` 翻译文件提供，由 `QTranslator` 运行时加载。`core/` 和 `store/` 中的日志与异常消息使用英文（面向开发者），不纳入翻译范围。
- **命名规范**：
  - UI：`*Window`、`*View`、`*Widget`、`*Dialog`、`*Panel`
  - 存储：`*Store`
  - Agent：`*Agent`
  - 数据结构：普通 `dataclass`，不使用 `*Model`
  - Qt Model：`*ListModel`、`*TreeModel`

### UI 编码规范

- 自定义信号统一使用 `PySide6.QtCore.Signal`，不得使用 `pyqtSignal`。
- 用户可见字符串使用 `self.tr()` 或 `QCoreApplication.translate()`；样式由集中 QSS、设计常量和 `theme_manager.py` 管理。
- UI 事件仅收集输入、调用接口和更新状态，不得包含数据库、网络、LLM 或复杂业务逻辑。
- 禁止 `time.sleep()`、死循环或同步等待异步任务。
- 窗口、分栏、主题、字号和语言等界面状态使用 `QSettings` 保存。
- 成功反馈优先使用状态栏或界面内提示；高风险删除操作必须确认或支持撤销。
- 图标按钮必须提供 Tooltip 和可访问名称；控件应具备合理的键盘焦点顺序。

---

## 8. UI 与用户体验规范

### 8.1 布局与页面状态

- 主窗口采用 `QSplitter` 三栏布局：左侧 Feed/筛选，中间文章列表，右侧 Reader/Agent/笔记。
- 主要界面统一支持 `empty`、`loading`、`content`、`error`、`offline`、`disabled` 状态。
- 加载过程不得显示空白区域；应用重启后恢复窗口和分栏状态。

### 8.2 交互与反馈

- 超过 200ms 的操作显示加载反馈，不得锁死窗口。
- 同步结果显示新增数和失败数；错误说明原因并提供重试或恢复入口。
- 列表刷新尽量保留选中项和滚动位置；搜索与筛选应显示当前范围。
- 已读、收藏等状态不得只依赖颜色表达；大量文章优先使用 Qt Model/View。

### 8.3 阅读体验

- Reader 支持字体、字号、行高和内容宽度调整，并即时生效。
- 图片、长链接、表格和代码块不得撑破正文区域；内容层级应清晰。
- Reader、Web 和双栏模式切换时保留当前文章，并尽量保留滚动位置。

### 8.4 跨平台与可访问性

- 布局不得依赖固定像素或单一平台字体，应适配常见分辨率和高 DPI。
- Windows、macOS、Linux 上不得出现关键控件截断或不可操作。
- 主要操作应同时支持鼠标和键盘；纯图标控件必须有 Tooltip 与可访问名称。

---

## 9. 数据库规范

- 仅使用 SQLite。打开时启用 WAL 日志模式（`PRAGMA journal_mode=WAL`）。
- 不使用 ORM。所有查询为原生 SQL 字符串，通过 `sqlite3.Connection` 执行。
- 所有 Schema 变更必须通过 `store/migrations.py` 的版本化迁移器进行，禁止在迁移之外修改 Schema。
- Store 类接收 `DatabaseManager` 实例，不自行管理数据库连接。
- 行模型使用 `dataclasses.dataclass`（不使用 named tuple）。
- 测试必须使用内存数据库 fixture（`":memory:"`），禁止在测试中写入用户真实数据库。

---

## 10. Agent 运行时契约

- 所有 AI Agent 任务（摘要、翻译、打标）必须通过 `core/agent/runtime.py` 中的 `AgentRuntime` 执行。
- `AgentRuntime` 负责 `asyncio` 事件循环集成、状态机（`idle → queued → running → done | error | cancelled`）和任务队列（等待槽位为最新替换策略）。
- 禁止自动取消正在执行的任务，取消操作只能来自用户的明确操作。
- LLM 调用必须使用流式模式（`stream=True`，通过 `AsyncOpenAI`）。每个 chunk 通过 Qt 信号更新 UI。
- 提示词模板：内置模板存放在 `resources/prompts/*.default.yaml`，用户数据目录下的沙盒覆盖文件优先级更高。首次自定义时从内置模板复制，且不覆盖已存在的沙盒文件。
- 提供者路由：主模型 → 回退模型。两者均失败时，通过 Reader 横幅（Reader 绑定任务）或批量面板（批量打标任务）上报错误。

### Agent UI 展示契约

UI 统一识别 `idle`、`queued`、`running`、`done`、`error`、`cancelled` 状态。传递给 UI 的事件至少包含：

```python
@dataclass(frozen=True)
class AgentUIEvent:
    run_id: str
    entry_id: int
    agent_type: str
    status: str
    chunk: str = ""
    progress: float = 0.0
    error: str | None = None
    result_json: str | None = None
```

- UI 更新前必须校验 `entry_id` 和 `run_id`，忽略过期事件。
- `running` 显示进度与取消入口；`error` 保留已有内容并提供重试；未配置 Provider 时提供设置入口。
- 高频流式 chunk 应缓冲或节流，避免频繁重绘。

---

## 11. Reader 管线契约

管线各阶段（每阶段独立版本化，缓存于 `content_store`）：
1. **Fetch**：`httpx.AsyncClient` GET 请求，跟随重定向，超时 15 秒
2. **Extract**：`readability-lxml` → 清洗后的 HTML + 标题 + 作者署名
3. **Convert**：清洗后的 HTML → Markdown（通过 `markdownify`）
4. Render：`html_renderer.py` 使用 Mistune 将 Markdown 渲染为 HTML，注入由 `theme_manager.py` 生成的 Reader CSS，再交给 `QWebEngineView.setHtml()` 显示。

### Reader UI 安全与交互规则

- Reader 模式仅显示处理后的内容，默认禁用 JavaScript，并禁止访问本地文件。
- 外部链接使用系统浏览器打开；Web 模式与 Reader 模式使用独立显示设置。
- 加载期间显示占位层；失败时回退到 Feed 摘要或原始内容，并提供重试。
- 切换文章时清理临时加载状态，不得误删缓存或显示上一篇文章的结果。

缓存失效：每个阶段在数据库中维护一个 `version` 整数，修改逻辑时递增该版本常量，管线只重新执行已失效的阶段。

---

## 12. 测试规范

- 使用 `pytest`，采用普通测试函数形式（不使用 `unittest.TestCase`）。
- 所有 store 测试使用内存 SQLite fixture（见 `tests/conftest.py`）。
- 所有 Agent 测试 mock `AsyncOpenAI` 客户端，单元测试中不发起真实 LLM 调用。
- 测试命名描述行为，而非实现：`test_entry_marked_read_persists`，而非 `test_store_method`。
- 禁止在测试中使用 `time.sleep`，异步测试使用 `asyncio` + `pytest-asyncio`。
- 所有新测试必须能在三个平台（Windows、macOS、Linux）的 CI 中通过。

### UI 测试规范

- UI 测试使用 `pytest-qt`，以假数据和 mock UseCase/Controller 驱动，不访问真实网络、数据库文件或 LLM。
- 异步等待使用 `qtbot.waitSignal()`、`QSignalSpy` 或条件等待，禁止 `time.sleep()`。
- 至少覆盖：主窗口与三栏布局、Feed/文章切换、页面状态转换、错误重试、已读/收藏显示、过期 Agent 事件过滤、主题更新、设置恢复和中英文布局。
- `QWebEngineView` 的完整渲染效果放入集成测试或人工验收，不做普通无头像素级测试。

---

## 13. 当前状态

| 模块 | 状态 | 备注 |
|------|------|------|
| 项目文档（INIT、AGENTS、PLAN） | ✅ 已完成 | INIT.md、AGENTS.md、PLAN.md |
| 数据库 Schema + 迁移 | 🔲 待开始 | Phase 1 |
| Feed 解析 + 同步 | 🔲 待开始 | Phase 1 |
| UI/UX 规范 | 🔲 待开始 | 页面、状态、反馈与接口 |
| 基础 UI | 🔲 待开始 | 三栏布局、Feed、文章列表 |
| Reader 与主题 UI | 🔲 待开始 | 阅读区、模式与主题 |
| 功能面板 UI | 🟡 进行中 | 摘要、翻译、收藏夹、笔记、标签与 Digest 已接入；AI 设置与 OPML 导入导出已统一到侧栏图标区 |
| 国际化与跨平台体验 | 🔲 待开始 | 中文、英文及三平台验收 |
| Reader 管线 | 🔲 待开始 | Phase 2 |
| AI Agent 运行时 | 🔲 待开始 | Phase 3 |
| 摘要 Agent | 🔲 待开始 | Phase 3 |
| 翻译 Agent | 🔲 待开始 | Phase 3 |
| 标签系统 | 🟡 进行中 | Store 已完成，文章标签显示与手动管理已接入 |
| 标签 Agent | 🟡 进行中 | AI 生成与用户确认入口已接入，待跨平台实机验收 |
| 笔记 + Digest 导出 | 🟡 进行中 | 笔记自动保存、单篇 Markdown 与批量 Digest 已接入；笔记编辑器与标签页已补齐明暗主题对比度 |
| 用量统计 | 🔲 待开始 | Phase 5 |
| 国际化（i18n） | 🔲 待开始 | Phase 5 |
| 跨平台 CI | 🔲 待开始 | Phase 6 |

---

## 14. 关键设计决策

- **不使用 ORM**：原生 sqlite3 保持依赖轻量，避免迁移复杂度。
- **asyncio + Qt 集成**：Qt 事件循环运行在主线程；asyncio 任务通过 `qasync` 或手动 `QThreadPool` + 信号桥接方式运行。所有 UI 更新必须通过 Qt 信号传递。
- **readability-lxml 而非 JS 方案**：Python 移植版避免了在三个平台上引入 Node.js 运行时依赖。
- **mistune 而非 cmark**：纯 Python 实现避免了 Windows/Linux CI 上的原生编译问题。
- **Jinja2 统一模板引擎**：LLM 提示词和 Digest 导出共用同一模板引擎。
- **platform/ 平台适配器**：将 `QFileDialog`、路径逻辑和剪贴板隔离到适配器，确保核心模块可在无显示器环境下进行单元测试。
- **WAL 模式**：在所有平台上支持读写并发访问。
- **UI 边界明确**：View 只发送用户意图并展示结果；异步更新前校验 `entry_id`、`run_id` 或 `request_id`。
- **布局与状态持久化**：三栏使用 `QSplitter`，界面状态通过 `QSettings` 恢复。
- **统一体验规范**：页面状态显式管理，Qt 控件样式集中到 QSS，Reader 样式由 `theme_manager.py` 管理。
- **国际化前置**：用户可见字符串从首次编写时即接入 Qt 翻译机制。

---

## 15. 已知问题

- `QWebEngineView` 需要硬件渲染环境；完整 HTML 渲染应作为集成测试，加载期间需显示占位层。
- `readability-lxml` 在大量使用 JavaScript 渲染的页面上可能失败，回退方案为使用 Feed 原始内容。
- `AsyncOpenAI` 流式输出与 `qasync` 在 Windows 上的兼容性需要专项测试。
- 跨平台字体、控件尺寸和高 DPI 可能导致截断或图标模糊，需覆盖常见缩放比例。
- 长标题、超长 Feed 名称和中英文混排应使用截断与 Tooltip。
- 流式输出和阅读模式切换可能导致卡顿或滚动位置丢失，需要节流与专项测试。

---

## 16. 本地开发默认配置

LLM 集成默认配置（本地 Ollama 或 LMStudio）：

- `base_url`：`http://localhost:11434/v1`
- `api_key`：`local`
- `model`：`qwen3`
