# Digest 与标签 UI 设计

## 范围

- 单篇文章右键菜单增加“导出 Markdown…”。
- 批量文章菜单增加“导出 Digest…”。
- Reader 显示当前文章标签。
- 单篇文章右键菜单增加“管理标签…”与“AI 生成标签”。
- 手动标签使用逗号分隔输入，保存时创建缺失标签并原子替换文章标签。
- AI 标签完成后由用户确认，再写入文章标签。

## 数据流

`EntryListWidget` 只发出文章 ID 或文章 ID 列表。`MainWindow` 负责文件夹选择、输入确认、调用已注入的 `DigestController`、`TagStore` 和 `AgentRuntime`，并通过状态栏反馈结果。`ReaderView` 只展示标签文字。

## 错误与边界

- 未注入控制器或 Store 时隐藏或禁用对应入口。
- 未选择文章时批量导出不可触发。
- 导出失败、标签读写失败和 AI 失败均显示原因，不清空已有 Reader 内容。
- AI 结果只接受当前任务对应文章与 run_id，忽略过期事件。

## 验证

- pytest-qt 覆盖信号、导出控制器调用、标签加载与保存、AI 结果确认。
- Ruff 和 Python 编译检查覆盖修改文件。
- Qt 测试若被系统 EGL 依赖阻断，保留明确的阻塞证据并在 Windows 实机复测。
