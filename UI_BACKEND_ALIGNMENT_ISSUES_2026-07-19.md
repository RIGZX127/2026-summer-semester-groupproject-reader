# UI 与后端对齐待办 Issues

> 本文只记录跨模块阻塞，不修改对应成员代码。

## Issue 1：标签后端尚未注入 UI

### 现状

`TagStore`、`TagNormalizer`、`CooccurrenceEngine` 和 `TagAgent` 已存在，但
`MainWindow` / `ReaderView` 没有获得 TagStore 或标签 Controller。UI 目前只能触发
Tag Agent，无法可靠读取、应用、删除或筛选标签。

### UI 需要的接口

- 获取文章标签：`get_entry_tags(entry_id)`。
- 搜索或创建标签：`search(query)`、`create(name)`。
- 添加/移除文章标签。
- 按 Any/All 标签组合查询文章。
- Tag Agent 完成后返回可应用的建议，并提供确认写入接口。

### 后续布局

Reader 标题下方放置可换行标签徽章；最右侧使用 30×30“建议标签”按钮。侧栏增加可折叠
标签筛选区，最多显示 5 个活动标签并提供清除入口。批量栏增加批量打标按钮。

## Issue 2：笔记 Store 尚未注入 Reader

### 现状

`NoteStore` 已具备 `get/save/delete`，但应用创建 MainWindow 时没有注入 NoteStore 或
笔记 Controller。UI 直接从全局数据库构造 Store 会违反三层分离规范。

### UI 需要的接口

- `load_note(entry_id)`。
- `save_note(entry_id, body)`，结果携带 entry_id 防止切换文章后串写。
- 可选 `delete_note(entry_id)`。

### 后续布局

Reader 下方工作区使用“AI 摘要 / 笔记”两个标签页，共用现有可拖动分隔条。笔记页提供
Markdown 原文编辑、保存状态、5 秒自动保存和 `Ctrl+S`。

## Issue 3：Digest 导出缺少数据组装与文件适配器

### 现状

`DigestExporter` 已能渲染和写文件，但 UI 没有用于组装 `EntryDigest` 的 Controller，
项目中也缺少计划指定的 `platform/file_dialog.py`。UI 不能直接访问数据库或绕过平台
适配器操作文件。

### UI 需要的接口

- 按 entry_ids 组装包含正文、摘要、笔记和标签的 `EntryDigest`。
- 统一的目录选择接口。
- 单篇和多篇导出的异步包装及完成结果。

### 后续布局

单篇导出位于 Reader 更多操作菜单；多篇导出位于文章批量栏。对话框分为模板、文件名、
目录和预览四个区域，成功后显示文件位置。

## Issue 4：OPML 缺少文件对话框适配器和导入编排

### 现状

`import_opml()` / `export_opml()` 已存在，但没有 `platform/file_dialog.py`，也没有负责
逐项添加、去重、汇总成功/失败数量的导入 Controller。

### UI 需要的接口

- 跨平台打开/保存文件接口。
- `import_feeds_from_opml(path)` 返回成功、重复、失败明细。
- `export_feeds_to_opml(path)` 返回结果路径或错误。

### 后续布局

在侧栏同步菜单下方增加“导入 OPML / 导出 OPML”，不恢复顶部菜单栏。导入完成使用
轻量结果对话框展示统计与失败项。

## Issue 5：用量统计只有写入，没有查询接口

### 现状

`UsageStore` 目前只有 `record()`，没有按提供者、模型、Agent 类型和日期聚合查询方法。
UI 无法生成可信统计。

### UI 需要的接口

- 指定时间范围的总调用数、Prompt Token、Completion Token。
- 按 provider/model/agent_type 分组。
- 每日时间线查询。

### 后续布局

设置窗口新增“用量统计”页：顶部三个汇总卡片，下方使用分组表格与最近 30 天趋势。

## 验收边界

以上接口由相应成员完成并注入 MainWindow/ReaderView 后，UI 再实现真实交互。在接口齐备
前不增加无响应按钮、假数据或 UI 层数据库访问。
