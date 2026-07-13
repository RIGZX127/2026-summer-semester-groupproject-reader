# Mercury Cross-Platform — 项目初始化文档

---

## 1. 项目概述

### 1.1 项目定位

跨平台 RSS 阅读器桌面应用。 *基于原 [Mercury](https://github.com/neolee/mercury)（macOS / SwiftUI）进行跨平台重写，继承其"本地优先 + AI 增强"的核心理念。*

### 1.2 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| UI 框架 | PySide6 (Qt 6) | 三平台原生渲染 |
| WebView | QWebEngineView | Chromium 内核，三平台一致 |
| 异步事件循环 | asyncio + qasync | 集成 Qt 与 asyncio |
| HTTP 请求 | httpx | Feed、网页正文和网络请求 |
| 数据库 | Python sqlite3（内建）| WAL 模式，通过 run_in_executor 异步包装，不引入 ORM |
| Feed 解析 | feedparser | RSS/Atom/JSON Feed |
| HTML 解析 | beautifulsoup4 + lxml | lxml 底层是 C 的 libxml2 |
| 正文提取 | readability-lxml | Node.js readability 的 Python 移植 |
| HTML → Markdown | markdownify | 将 Readability HTML 转换为 Markdown |
| Markdown → HTML | mistune | 将 Markdown 渲染成 Reader HTML |
| LLM 客户端 | openai (AsyncOpenAI) | 流式支持 |
| 模板引擎 | Jinja2 | 用于 Agent 提示词 + Digest 导出 |
| 代码格式化 | ruff | 替代 black + isort + flake8 |
| 测试 | pytest + pytest-asyncio + pytest-qt | 不用 unittest.TestCase |

### 1.3 平台目标

| 平台 | 最低版本 |
|------|---------|
| Windows | 10+ |
| macOS | 13+ |
| Linux | Ubuntu 22.04+ 及同类发行版 |


---

## 2. 功能特性

### 2.1 订阅源管理

- RSS/Atom/JSON Feed 的添加、编辑、删除
- 多 Feed 并发同步（可配置 2-10 并发）
- 增量更新（GUID 去重）
- 自动同步循环（15 分钟间隔）
- OPML 导入/导出
- 内置默认订阅源引导

### 2.2 文章阅读

- 三栏布局（侧边栏 / 文章列表 / 阅读详情）
- 三条内容管线：源获取 → Readability 正文提取 → Markdown 规范化 → 渲染
- 阅读模式：Reader / Web / 双栏
- 主题系统：预设主题 + 字号/行高/字体/内容宽度用户覆盖
- 版本化缓存：Markdown 版本 / Readability 版本 / 渲染版本独立失效

### 2.3 文章管理

- 已读/未读标记（含批量操作）
- 文章收藏（Star），全局收藏夹虚拟订阅源
- 搜索（标题 + 摘要字段，全源/当前源范围）
- 分页加载，按时间倒序
- 软删除

### 2.4 AI 智能助手

- **文章摘要**：流式生成、目标语言/详细程度可调、自动摘要（1 秒去抖、串行）、槽位存储
- **文章翻译**：按段落分段翻译、Reader 内双语渲染、纯手动触发、按段落并发翻译（asyncio.Semaphore 控制并发度，默认 3，范围 1–5）
- **智能标签**：LLM 按需建议、批量历史文章打标
- **运行时系统**：状态机、并发控制、超时策略、事件广播
- **提供者管理**：多 LLM 提供者/多模型配置、路由选择（主模型 + 回退模型）、连接测试
- **提示词模板**：YAML 格式、内置 + 沙盒覆盖、版本追溯
- **用量追踪**：按提供者/模型/Agent 类型维度的调用量统计

### 2.5 标签系统

- 扁平标签结构（无层级）
- 三层去重管线：规范化 → 严格匹配 → 别名解析
- 标签库管理（重命名、合并、删除）
- 多选标签筛选（最多 5 个标签，Any/All 模式）
- 共现推荐（基于共享标签的相关文章）
- 临时标签机制（非手动创建的标签达到使用阈值后自动提升）

### 2.6 笔记与导出

- 文章笔记（Markdown 编辑、5 秒自动保存）
- Export Digest：单篇 Markdown 文件导出（Hugo 兼容）
- Export Multiple Digest：多篇合并 Markdown 导出
- 模板驱动输出（Jinja2 语法）

---

## 3. 开发环境与工具

- Python ≥ 3.11
- Qt ≥ 6.5 LTS
- Git
