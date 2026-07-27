# Mercury Reader AI 与自适应布局设计

日期：2026-07-16

## 1. 背景

成员仓库压缩包已包含 Phase 1/2 的 PySide6 三栏界面、Reader/Web/原文对照模式与 UI 测试。当前分支已合入 `SummaryAgent`、`TranslationAgent`、共享 `AgentRuntime` 及对应核心测试，但尚未接入完整 UI。

现有 Reader 的原文对照模式嵌套在应用三栏布局内，Reader 可用宽度仍需再分成两半，导致正文和原网页都偏窄。本设计在保留现有选择、滚动位置与异步任务的前提下，加入应用级三种布局和 Reader 右侧 AI 助手抽屉。

## 2. 目标与非目标

### 2.1 目标

- 提供三栏、双栏和沉浸阅读三个可直接到达的应用布局。
- 解决 Reader 原文对照模式宽度不足的问题。
- 为摘要、翻译和正文清洗提供统一、可折叠的 Reader AI 助手区域。
- 对接现有 `AgentRuntime`，完整展示流式、排队、进度、取消、完成和错误状态。
- 保持浅色/深色主题、键盘操作、可访问性和状态持久化一致。

### 2.2 非目标

- 不新增 AI 正文重写或润色 Agent。
- 不修改 `SummaryAgent`、`TranslationAgent` 或 Reader 清洗算法的核心行为。
- 不在 View 中直接执行 SQL、HTTP、缓存删除或 LLM 调用。
- 不扩展标签、笔记、Digest 或设置页面的业务范围。

## 3. 已确认的产品决策

### 3.1 正文清洗

“正文清洗”指现有本地 Reader 管线：`Fetch → Extract（Readability）→ Convert（Markdown）→ Render`。它不使用 LLM、不产生 Token，也不称为 AI 清洗。AI 助手抽屉可以承载该入口，但必须明确展示“本地处理”。

### 3.2 应用布局

布局状态固定为：

- `three_columns`：订阅源 + 文章列表 + Reader。
- `two_columns`：隐藏订阅源，保留文章列表 + Reader。
- `immersive`：隐藏订阅源和文章列表，Reader 占满窗口。

Reader 工具栏右侧提供三个互斥按钮，用户一次点击即可直达目标布局。按钮必须显示当前选中状态，并提供中文 Tooltip、可访问名称和键盘焦点。

### 3.3 AI 助手位置

AI 助手是 Reader 右侧约 360 px 的可折叠抽屉。Reader 工具栏只保留一个 AI 助手开关；抽屉内部使用“摘要 / 翻译 / 正文清洗”三个页签。关闭抽屉只隐藏界面，不取消正在运行的任务。

## 4. 布局与宽度行为

### 4.1 外层布局控制

`MainWindow` 继续以水平 `QSplitter` 组织三个主栏。新增 UI 层布局控制器，集中负责：

- 显示或隐藏订阅源栏和文章列表栏。
- 保存每种布局最后一次有效的分栏尺寸。
- 在布局切换后恢复当前 Feed、文章、焦点与 Reader 状态。
- 将布局偏好与尺寸写入 `QSettings`。

不得通过删除并重建组件实现布局切换，以免丢失选择、滚动位置或异步状态。

### 4.2 Reader 原文对照模式

Reader 内部的 `reader / web / split` 是阅读内容模式，与应用级 `three_columns / two_columns / immersive` 分开管理。

进入 Reader `split` 时：

1. 如果应用当前是三栏，临时切换为应用双栏，给 Reader 释放订阅源栏宽度。
2. 记录进入前的应用布局。
3. Reader 与原网页默认按 50/50 分配，并恢复此前保存的有效比例。
4. 每一侧设置可读下限，禁止缩成不可操作的窄条。
5. 可用宽度不足时自动收起 AI 抽屉，但保留其中内容和任务状态。

退出 Reader `split` 时，仅在用户期间没有手动切换应用布局的情况下恢复进入前布局。用户手动选择始终优先。

### 4.3 AI 抽屉

抽屉与 Reader 内容通过内部布局容器组合。打开时优先使用保存宽度；窗口较窄时限制抽屉宽度并保证 Reader 最小可读宽度。抽屉关闭后 Reader 立即获取全部可用宽度。

## 5. AI 助手页签

### 5.1 摘要

- 空闲状态显示“生成摘要”。
- 支持手动触发；设置中启用自动摘要时，在文章内容加载完成后使用 1 秒防抖触发。
- 流式 chunk 追加到可选择、可复制的文本区，并进行适当节流以避免频繁重绘。
- 运行中显示状态和明确的取消入口。
- 失败或取消后保留已生成文本；错误状态提供重试。
- 缓存命中时直接展示结果，不模拟流式动画。

### 5.2 翻译

- 仅允许手动触发。
- 显示 `queued / running / done / error / cancelled`，运行中显示段落进度。
- 保留已经完成的段落；部分失败时提供“重试失败段落”。
- 完成后在 Reader 工具栏提供“原文 / 双语 / 仅译文”三种显示模式。
- 切换翻译显示模式时记录并恢复滚动位置。
- 再次打开文章时优先读取已持久化结果。

### 5.3 正文清洗

- 明确标注“本地处理，不使用 AI”。
- 展示获取、正文提取、Markdown 规范化和渲染四阶段状态。
- 展示当前内容是否来自缓存，以及失败后的回退来源。
- “重新清洗”仅发射带 `entry_id` 和 `request_id` 的 UI 意图；Controller/UseCase 负责使对应缓存失效并重新运行 Reader 管线。
- 清洗失败时保留 Feed 摘要或已有内容，并提供发生阶段、原因和重试入口。

## 6. 状态、事件与数据流

### 6.1 Agent 事件

UI 直接消费既有 `AgentUIEvent`，支持：

`idle → queued → running → done | error | cancelled`

每个面板记录当前 `entry_id` 和 `run_id`。处理 `state_changed`、`chunk_received` 或进度事件前必须同时校验两者；不匹配的事件直接忽略。切换文章只废弃尚未触发的自动摘要防抖计时器；运行时等待槽继续遵循“最新替换”策略，已经运行的任务绝不自动取消。

### 6.2 UI 边界

View 只负责：

- 收集布局、抽屉、摘要、翻译、取消、重试和重新清洗意图。
- 展示状态、内容、进度与错误。
- 保存纯界面偏好。

Controller/UseCase 负责：

- 调用 `AgentRuntime.submit()` 和 `cancel()`。
- 将 Reader 管线与重新清洗请求关联到 `entry_id`、`request_id`。
- 将 Agent 与 Reader 结果路由回当前 View。

## 7. 持久化

通过 `QSettings` 保存：

- 当前应用布局。
- 三种应用布局各自最后的外层分栏尺寸。
- Reader/Web 对照分栏比例。
- AI 抽屉开关与宽度。

不在 `QSettings` 中保存 Agent 内容或运行状态；这些继续由 `AgentStore` 管理。恢复无效或越界尺寸时使用安全默认值，不允许恢复为零宽度可见栏。

## 8. 视觉与可访问性

- 复用 Mercury 语义色板与集中 QSS，不在组件文件中加入十六进制颜色。
- 浅色使用暖现代体系，深色使用近黑石墨蓝体系。
- 布局按钮和 AI 按钮至少 36×36 px，具有 normal、hover、pressed、checked、focus 和 disabled 状态。
- 页签、进度、错误、取消和选中状态必须结合文字或图标表达，不能只依赖颜色。
- 长中文和英文文本可换行或省略，并通过 Tooltip 提供完整内容。
- 主题切换不重新抓取正文，不改变布局、选择、滚动或待处理内容。

## 9. 错误与边界情况

- 未选文章时 AI 页签进入 disabled 状态并显示操作指引。
- 未配置 Provider 时摘要和翻译提供设置入口；正文清洗仍可用。
- Agent 错误保留已有输出，显示原因和重试。
- Reader 管线错误保留回退内容，正文区域不留空白。
- 快速切换文章时，旧 Reader 与 Agent 结果不得更新当前文章。
- 窄窗口和 100%/150%/200% 缩放下，布局按钮、页签和取消入口不得截断或不可操作。

## 10. 测试策略

使用 `pytest-qt`、假 Controller 和假 Runtime，先写失败测试，再实现 UI。测试至少覆盖：

- 三种应用布局的栏可见性、选中按钮和尺寸恢复。
- Reader `split` 自动临时扩宽、退出恢复和用户手动布局优先级。
- AI 抽屉开关不取消任务，窄宽度下自动收起但保留内容。
- 摘要流式更新、取消后内容保留、错误重试与缓存展示。
- 翻译进度、三种显示模式、部分失败重试和滚动保持请求。
- 正文清洗四阶段、本地处理说明、回退与重新清洗意图。
- `entry_id + run_id` 过期 Agent 事件过滤及 Reader `request_id` 过滤。
- QSettings 恢复、两套主题、键盘操作、Tooltip 和可访问名称。

实现完成后的验证命令：

```powershell
ruff check app/styles.py ui tests/test_ui
ruff format --check app/styles.py ui tests/test_ui
pytest tests/test_ui -q
pytest -q
```

此外需要在浅色和深色主题下人工检查三栏、双栏、沉浸阅读、Reader 原文对照和 AI 抽屉。

## 11. 合并与实施范围

实施首先从成员压缩包恢复并核对 Phase 1/2 UI 基线，再将当前分支的摘要和翻译能力接入。成员核心模块不做无关重构；冲突以当前分支已合入的 Core/Store 实现和稳定接口为准。

预计 UI 文件范围：

- `ui/main_window.py`
- `ui/reader/reader_view.py`
- `ui/reader/reader_toolbar.py`
- `ui/reader/summary_panel.py`
- 新增 AI 助手抽屉与正文清洗状态组件
- 对应 `tests/test_ui/`
- 必要的集中主题/QSS 文件

若重新清洗缺少已锁定的 Controller/UseCase 接口，实施计划必须先定义一个最小、带类型的接口，不能让 View 直接访问 Store 或 ReaderPipeline。

## 12. 验收标准

- 用户可一次点击切换三栏、双栏或沉浸阅读。
- Reader 原文对照模式在常见 1280 px 窗口下不再出现明显不可读窄栏。
- AI 助手可折叠，包含摘要、翻译和本地正文清洗三个明确页签。
- 摘要与翻译完整遵守 AgentRuntime 状态和过期事件保护。
- 关闭抽屉、切换布局或主题不会取消任务或丢失已有内容。
- 两套主题、键盘操作、可访问信息、状态恢复和完整测试均通过。
