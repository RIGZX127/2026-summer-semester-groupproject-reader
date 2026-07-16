# Phase 2 UI 接入设计

## 目标

在不修改成员 A 已锁定 Store 接口和数据库 Schema 的前提下，将 Phase 2 已完成的 ReaderPipeline 与文章管理接口接入现有三栏 PySide6 UI，并补齐 Reader、Web、双栏阅读模式及阅读偏好控制。

## 范围

本次包含：

- ReaderPipeline 正文接入、加载状态、错误回退、重试和过期请求过滤。
- 当前 Feed 范围的标题与摘要搜索。
- 已读/未读展示与切换、打开文章自动标记已读。
- 收藏/取消收藏按钮和列表标识。
- 文章列表右键菜单。
- 软删除前确认、删除成功反馈和列表/未读数刷新。
- Reader、Web、双栏三种模式。
- 字号、浅色/深色主题、内容宽度控制与 QSettings 持久化。

本次不包含：

- 修改 EntryStore、ReaderPipeline 或数据库 Schema。
- 删除后的恢复接口和撤销按钮。
- 全文索引、跨 Feed 全局搜索、批量选择 UI。
- Phase 3 的摘要、翻译和其他 Agent UI。

## 架构

采用渐进式扩展，保留现有 `QListWidget`、`MainWindow`、`ReaderView` 和三栏 `QSplitter`。View 仅发送用户意图和显示结果；异步 Store 与 Pipeline 调用仍由 `MainWindow` 协调。新增的 Reader 工具栏、主题值对象和主题管理器保持独立，避免把显示设置和 HTML/CSS 逻辑堆入主窗口。

依赖注入扩展为：`app/app.py` 构造 `ReaderPipeline(state.db)`，并与现有 Store、SyncService 一起注入 `MainWindow`。UI 不直接执行 SQL、HTTP 或正文提取。

## 组件设计

### EntryListWidget

- 顶部增加搜索框，placeholder 明确为“搜索当前订阅源”。
- 发射 `search_requested(str)`，清空输入时发射空字符串以恢复当前 Feed 列表。
- 每个条目保存 `entry_id`、`is_read`、`is_starred`，并以文字/符号共同表达状态。
- 发射 `mark_read_requested(int, bool)`、`star_requested(int)`、`delete_requested(int)`。
- 右键菜单根据当前状态显示“标记已读/未读”和“收藏/取消收藏”。
- 刷新结果时尽量按 `entry_id` 恢复选择项和滚动位置。

### MainWindow

- 维护当前 `entry_id`、当前搜索词和 Reader `request_id`。
- Feed 切换后根据当前搜索词调用 `list_by_feed()` 或 `search(query, feed_id)`。
- 选择文章后先调用 `mark_read(entry_id)`，更新列表与侧栏未读数，再调用 `ReaderPipeline.build(entry_id, request_id)`。
- Pipeline 返回后同时校验 `entry_id` 和 `request_id`；不匹配则丢弃结果。
- `ReaderFetchError` 或其他加载错误时，将 EntryRow 的 Feed 摘要交给 ReaderView 作为回退，并显示可重试提示。
- 删除使用 `QMessageBox` 确认；确认后调用 `soft_delete()`，刷新当前结果、侧栏未读数，并在状态栏提示成功。
- 收藏和已读操作成功后刷新当前结果，并尽量保留选择。

### ReaderToolbar

- 单行布局。
- 左侧为互斥模式按钮：Reader、Web、双栏。
- 右侧为字号、主题、内容宽度控制。
- 所有图标或短标签按钮设置 Tooltip、accessibleName，并支持键盘焦点。
- 发射带类型值的模式和设置变更信号。

### Theme 与 ThemeManager

- `Theme` 为不可变 dataclass，包含字号、内容宽度、背景色、文字色和辅助色。
- 预设浅色与深色主题；字号限制在 14–24 px；内容宽度预设为 640、760、920 px。
- ThemeManager 从 QSettings 读取和保存设置，并生成只作用于 Reader HTML 的 CSS。
- 图片、表格、代码块和长链接不得撑破正文区域。

### ReaderView

- Reader WebView 保持 JavaScript 和本地文件访问禁用。
- Web 模式使用独立 QWebEngineView 加载 EntryRow.url；不复用 Reader 的安全配置和 HTML。
- 双栏使用水平 QSplitter 同时展示 Reader 与 Web。
- 维护当前文章 URL 和 Reader HTML，模式切换不重新选择文章。
- Reader HTML 注入 ThemeManager CSS 后显示。
- 外部链接交给系统浏览器打开。
- 空、加载、内容、错误/回退状态均有明确页面，不显示空白区域。

## 数据流

1. 用户选择 Feed，MainWindow 加载或搜索该 Feed 的 EntryListItem。
2. 用户选择文章，MainWindow 生成 request_id 并显示加载状态。
3. MainWindow 获取 EntryRow、标记已读，再调用 ReaderPipeline。
4. Pipeline 返回 RenderedContent；MainWindow 校验 entry_id 与 request_id。
5. ReaderView 保存正文 HTML 和原文 URL，并按当前模式显示。
6. 用户修改模式或阅读设置时只更新 ReaderView，不重新请求文章。

## 错误处理

- 搜索、收藏、已读和删除失败：保留现有列表，在状态栏显示原因。
- Reader 网络失败：显示 Feed 摘要回退、错误说明和重试按钮。
- 原文 URL 为空：Web 区显示“该文章没有原文链接”，Reader 仍可用。
- 快速切换文章：旧请求允许完成，但结果因 request_id 不匹配而不更新 UI。
- 删除：仅在确认后执行；取消确认不产生任何 Store 调用。

## 测试与验收

- pytest-qt 测试搜索信号、清空搜索、已读/收藏标识和右键菜单动作。
- pytest-qt 测试删除确认的确认与取消路径。
- 使用假 Store/Pipeline 测试 MainWindow 的接口调用、错误反馈和过期请求过滤。
- 测试 Reader/Web/双栏切换保持当前文章。
- 测试字号、主题和内容宽度即时生效并能从 QSettings 恢复。
- QWebEngineView 不做像素级单元测试；完整正文、Web 加载、高 DPI 和中英文混排进行人工验收。
- 全量运行现有测试，确保 Phase 1、Phase 2 后端测试无回归。

## 完成标准

- 点击文章显示 ReaderPipeline 正文而非仅 Feed 摘要。
- 搜索、已读、收藏和软删除均通过稳定接口持久化。
- 删除前必须确认，不提供无效撤销按钮。
- 三种阅读模式保持当前文章。
- 阅读设置即时生效且重启后恢复。
- 新增测试和全量测试通过，ruff 检查无新增问题。
