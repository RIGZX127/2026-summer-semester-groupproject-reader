# Merge 冲突报告

> 合并时间：2026-07-14
> 合并提交：`099bc7c` — A 的 Phase 2 + B 的 Agent 运行时
> 处理策略：Reader 管线文件使用 A 的版本（`git checkout --theirs`），Agent 文件无冲突直接保留

---

## 一、Git 层面冲突（已解决）

以下 5 个文件在 `git merge` 时产生 add/add 冲突，A 和 B 各自创建了同路径文件。
已采用 A 的版本（A 是后端架构负责人，且有测试覆盖 67/67 passed）。

| 文件 | A 的版本 | B 的版本 | 解决方案 |
|------|---------|---------|---------|
| `core/reader/cache.py` | A 有完整测试配套 | B 有代码审查修复 | 使用 A 的版本 |
| `core/reader/markdown.py` | A 有完整测试配套 | B 有代码审查修复 | 使用 A 的版本 |
| `core/reader/pipeline.py` | A 有完整测试配套 | B 有代码审查修复 | 使用 A 的版本 |
| `core/reader/readability.py` | A 有完整测试配套 | B 有代码审查修复 | 使用 A 的版本 |
| `store/content_store.py` | A 有完整测试配套 | B 有 upsert 优化 | 使用 A 的版本 |

---

## 二、RenderedContent 字段不一致（语义冲突）

### 问题

A 和 B 对 G2.1 接口的理解不一致：

| 字段 | A 定义 | B 期望(G2.1契约) | 状态 |
|------|--------|-----------------|------|
| `entry_id` | ✅ 存在 | ❌ 未定义 | A 新增，合理 |
| `html` | ✅ str | ✅ str | 一致 |
| `title` | ✅ str | ✅ str | 一致 |
| `byline` | ✅ str | ✅ str | 一致 |
| `markdown` | ❌ 缺失 | ✅ str（Agent 消费入口） | **关键缺失** |
| `from_cache` | ✅ bool | ✅ bool | 一致 |
| `request_id` | ✅ 存在 | ❌ 未定义 | A 新增，合理（用于过期请求过滤） |

### 影响

B 的 SummaryAgent 和 TranslationAgent 依赖 `RenderedContent.markdown` 获取文章正文进行 LLM 处理。当前 A 的版本缺少此字段，Agent 无法直接访问 Markdown 内容。

### 可能的解决路径

1. **A 在 RenderedContent 中补充 `markdown: str` 字段**（推荐 — 符合 G2.1 契约）
2. **Agent 绕过 RenderedContent，直接从 `ContentStore.get(entry_id).markdown` 读取**（绕过方案）

---

## 三、B 的代码审查发现（A 版本未采纳）

以下问题在 B 实现时被发现并修复，但合并时采用 A 的版本，这些修复未保留：

| # | 问题 | 文件:行 | 严重度 | 说明 |
|---|------|---------|--------|------|
| 1 | `asyncio.get_event_loop()` 应改为 `get_running_loop()` | `pipeline.py` | Important | Python 3.10+ 废弃，A 版本仍用旧 API |
| 2 | `run_in_executor` 调用缺少超时 | `pipeline.py` | Important | 如果 extract/markdown 挂起，线程永久阻塞 |
| 3 | `og:site_name` 误用作作者字段 | `readability.py` | Critical | 会将网站名当作作者返回 |
| 4 | 内容长度检查测量 HTML 而非纯文本 | `readability.py` | Important | 大量标记+少量文本可能错误通过检查 |
| 5 | upsert 方法每次写入两次数据库往返 | `content_store.py` | Important | 可通过 SQLite RETURNING 子句优化 |

---

## 四、Agent 代码无冲突

以下 B 的 Agent 运行时文件与 A 的 Phase 2 工作无任何冲突：

```
core/agent/providers.py         ✅
core/agent/runtime.py           ✅  [G3.1+G3.2]
core/agent/stream_buffer.py     ✅
core/agent/template_loader.py   ✅
store/agent_store.py            ✅
store/usage_store.py            ✅
resources/prompts/summary.default.yaml     ✅
resources/prompts/translation.default.yaml ✅
resources/prompts/tagging.default.yaml     ✅
docs/TASK_ASSIGNMENT.md         ✅
```

---

## 五、测试结果

```
67 passed, 0 failed（安装 mistune 后）
```

所有 A 的测试 + B 的测试均通过。但 Agent 运行时没有对应的测试文件（待 Task 16/17 实现 SummaryAgent/TranslationAgent 时补充）。

---

## 六、建议行动

| 优先级 | 行动 | 负责人 |
|--------|------|--------|
| 🔴 最急 | RenderedContent 增加 `markdown` 字段 | A |
| 🟡 高 | 评估 B 的代码审查修复(#1-#5)是否需要移植到 A 版本 | A+B |
| 🟢 中 | B 实现 SummaryAgent 时确认 markdown 获取路径可行 | B |
| 🟢 低 | 统一 INTERFACE.md 中的 G2.1 接口文档 | A |
