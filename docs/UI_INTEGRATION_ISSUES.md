# UI 集成问题清单

本文记录 UI 推进过程中发现的跨成员文件、接口和职责冲突。UI 实现不得通过修改其他成员负责的 `core/` 或 `store/` 来绕过问题。

## 状态说明

- `open`：当前 UI 无法独立解决，需要成员接口或用户决策。
- `ui-workaround`：UI 可在不修改 Core/Store 的前提下降级处理。
- `resolved`：已通过明确来源或接口完成解决。

## Issues

### UI-001：成员仓库压缩包缺少 Reader 依赖文件

- 状态：`resolved`
- 现象：桌面成员压缩包中的 `ui/reader/reader_view.py` 引用了 `reader_toolbar.py`、`theme_manager.py`、`ui/theme.py` 和 `ui/theme_controller.py`，但压缩包未包含这些文件。
- 处理：使用仓库内 `Mercury-UI-近黑石墨蓝双主题.zip` 补齐主题链与 Reader 依赖；业务 MainWindow、Sidebar、EntryList 和 Dialog 仍以成员仓库压缩包为基线。
- 边界：不覆盖任何 Core/Store 文件。

### UI-002：旧 UI 测试与新语义主题接口不一致

- 状态：`ui-workaround`
- 现象：成员压缩包的 `test_styles.py` 仍断言旧 `COLORS` 常量和旧圆角值；近黑石墨蓝主题已经改为 `Palette` 和 8/12 px 圆角。
- 处理：只更新 `tests/test_ui/` 以验证当前已确认的语义 Palette；不回退新主题，不修改其他成员测试。

### UI-003：当前 app/app.py 仍是 Phase 1 空窗口桩

- 状态：`ui-workaround`
- 现象：当前分支 `app/app.py` 创建占位 MainWindow，而成员压缩包已有真实三栏 `ui/main_window.py`。
- 处理：仅更新应用 UI 组合，将既有 Store、SyncService 和 ReaderPipeline 注入真实 MainWindow；不修改这些服务的实现。

### UI-004：TranslationAgent 未暴露“仅重试失败段落”UI 接口

- 状态：`open`
- 现象：当前 TranslationAgent 只接受整篇 `runtime.submit(entry_id, "translation")`，结果只提供双语 HTML 和成功/失败数量，没有失败段落标识或仅重试失败段落接口。
- 当前 UI：显示翻译进度、失败数量和“重试翻译”；重试按当前接口重新提交整篇任务。
- 需要其他成员提供：稳定的失败段落标识与 Runtime 可调用的失败段落重试接口。

### UI-005：ReaderPipeline 未暴露四阶段实时事件

- 状态：`open`
- 现象：当前 `ReaderPipeline.build()` 只返回最终 `RenderedContent` 或抛出异常，没有 Fetch/Extract/Convert/Render 阶段回调。
- 当前 UI：展示四阶段固定说明，并将现有 Reader 请求映射为整体 loading/done/error；不会伪造逐阶段实时进度。
- 需要其他成员提供：带 `entry_id`、`request_id`、stage、status 的稳定阶段事件接口。

### UI-006：接口进度文档与实际交付状态不一致

- 状态：`ui-workaround`
- 现象：`docs/TASK_ASSIGNMENT.md` 仍将 G2.2 标记为待成员 A 完成，但 `INTERFACE.md` Phase 2、`docs/phase2-acceptance-report.md` 和当前 `EntryStore` 已包含并验证已读、收藏、搜索与软删除接口。另一方面，`ProviderConfig` 和 `LLMRouter` 虽已存在于代码中，G3.3 在任务分配表中仍是待成员 B 确认，尚无冻结接口说明。
- 对 UI 的影响：文章管理 UI 可以按已冻结的 G2.2 契约继续；Provider 设置面板若直接依赖当前实现，可能在接口确认时返工。
- 当前处理：UI 只接入已有文档契约和验收证据支持的 G2.2；G3.3 未正式冻结前不实现 Provider 设置面板，也不修改 `core/agent/providers.py`。
- 需要的接口或决策：成员 A 更新任务分配表中的 G2.2 状态；成员 B 在文档中冻结 G3.3 的配置持久化、密钥处理和连接测试接口。

## 新问题记录模板

### UI-NNN：标题

- 状态：`open | ui-workaround | resolved`
- 现象：
- 对 UI 的影响：
- 当前处理：
- 需要的接口或决策：
