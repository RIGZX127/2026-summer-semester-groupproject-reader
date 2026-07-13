# Mercury 跨平台版 — 文档冲突订正方案

本文档基于 2026-07-12 对仓库四份文件（`AGENTS.md`、`INIT.md`、`PLAN.md`、`任务分配表.xlsx`）的全面审查，列出所有已发现的冲突及其订正方案。按优先级排序，先解决严重冲突，后处理轻微不一致。

---

## 订正原则

1. **技术正确性优先**：当技术事实与文档描述冲突时，以技术事实为准。
2. **AGENTS.md 权威优先**：作为 AI 协作工程规范，AGENTS.md 是架构与编码约定的唯一权威来源。任务分配表和 INIT.md 处于下游，应向上游对齐。
3. **最小化变更范围**：每次修改只解决一类问题，便于 Review 追溯。
4. **修改后交叉校验**：每完成一项订正，在对应行打 ✅ 标记。

---

## 🔴 A 类 — 严重冲突（阻塞开发，必须最先解决）

### A-1. HTML→Markdown 转换工具统一 [冲突 #1, #6]

**现状**：

| 文件 | 指定工具 | 是否可行 |
|------|---------|---------|
| INIT.md §1.2 | `markdownify` | ✅ 正确（HTML→Markdown 反向转换） |
| AGENTS.md §3 / §11 step 3 | `mistune` | ❌ 错误（mistune 只能 Markdown→HTML） |
| PLAN.md §2.1 | `mistune` | ❌ 同上 |

**订正方案**：三份文档统一使用两阶段管线——

| 阶段 | 工具 | 方向 | 所在文件 |
|------|------|------|---------|
| Convert | **`markdownify`** | HTML → Markdown | `core/reader/markdown.py` |
| Render | **`mistune`** | Markdown → HTML | `ui/reader/reader_view.py`（配合 `html_renderer.py`） |

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **AGENTS.md** | §3 技术栈表格 | `Markdown 渲染 \| mistune` → 拆为两行：`HTML→Markdown \| markdownify` 和 `Markdown→HTML \| mistune` |
| **AGENTS.md** | §11 step 3 | `通过 mistune` → `通过 markdownify` |
| **AGENTS.md** | §11 step 4 | 保持不变（mistune 渲染为 HTML，方向正确） |
| **PLAN.md** | §2.1 任务详情第 3 条 | `使用 mistune` → `使用 markdownify` |
| **PLAN.md** | §2.1 受影响文件 `core/reader/markdown.py` 描述 | `使用 mistune` → `使用 markdownify` |
| **INIT.md** | §1.2 | 保持不变（已使用 markdownify，方向正确） |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §3 技术栈表格 (原行 38) | `old: "| Markdown 渲染 | mistune | 纯 Python，可扩展 |"` → `new: 拆为 markdownify + mistune 两行` |
| 2 | `AGENTS.md` | §11 step 3 (原行 251) | `old: "通过 mistune"` → `new: "通过 markdownify"` |
| 3 | `PLAN.md` | 里程碑 1.1 任务详情 (行 49) | `old: 依赖列表中仅有 mistune` → `new: 增加 markdownify` |
| 4 | `PLAN.md` | 里程碑 2.1 任务详情 (行 181) | `old: "Convert（mistune）"` → `new: "Convert（markdownify）"` |
| 5 | `PLAN.md` | 里程碑 2.1 任务详情 (行 183) | `old: "使用 mistune"` → `new: "使用 markdownify"` |
| 6 | `AGENTS.md` | §6 文件结构 `core/reader/markdown.py` 注释 (行 112) | `old: "# HTML → Markdown（mistune）"` → `new: "# HTML → Markdown（markdownify）"` |

---

### A-2. 项目目录结构统一 [冲突 #7, #10]

**现状**：任务分配表使用按功能分组的扁平顶层结构（`feed/`、`agent/`、`reader/`、`views/` 等），AGENTS.md §6 使用严格三层架构（`ui/` / `core/` / `store/` / `platform/` / `resources/`）。两套结构不可兼容。

**订正方案**：**以 AGENTS.md §6 的目录结构为唯一基准**，将任务分配表中的所有文件路径重映射。PLAN.md 各里程碑的"受影响文件"列表也需与此对齐。

**任务分配表 → AGENTS.md 路径映射表**：

| 任务分配表原路径 | 订正后路径 (AGENTS.md) | 所属层级 |
|-----------------|----------------------|---------|
| `core/database.py` | `store/db.py` | Store |
| `core/task_queue.py` | **删除**（AgentRuntime 内置状态机覆盖此职责） | — |
| `core/http_client.py` | **删除**（直接使用 httpx.AsyncClient） | — |
| `feed/feed_store.py` | `store/feed_store.py` | Store |
| `feed/sync_usecase.py` | `core/feed/sync.py` | Core |
| `feed/opml_importer.py` | `core/feed/opml.py`（合并） | Core |
| `feed/opml_exporter.py` | `core/feed/opml.py`（合并） | Core |
| `app/app_model.py` | `app/state.py` | App |
| `agent/runtime/` | `core/agent/runtime.py` | Core |
| `agent/provider/` | `core/agent/providers.py` | Core |
| `agent/summary/` | `core/agent/summary.py` | Core |
| `agent/translation/` | `core/agent/translation.py` | Core |
| `agent/tagging/` | `core/agent/tagging.py` | Core |
| `digest/note_store.py` | `store/note_store.py` | Store |
| `digest/digest_composer.py` | `core/digest/exporter.py` | Core |
| `core/i18n.py` | **删除**（i18n 走 Qt 原生 `resources/i18n/` + `tr()`，不需要 core 模块） | — |
| `app/main_window.py` | `ui/main_window.py` | UI |
| `reader/html_renderer.py` | `ui/reader/html_renderer.py` | UI |
| `reader/theme_manager.py` | `ui/reader/theme_manager.py` | UI |
| `reader/readability_pipeline.py` | `core/reader/pipeline.py`（拆为 pipeline / readability / markdown / cache 四个文件） | Core |
| `views/` | `ui/` 目录（ui/sidebar.py, ui/entry_list.py, ui/reader/） | UI |
| `tags/` | `ui/dialogs/tag_manager_dialog.py` | UI |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `任务分配表.xlsx` | Sheet "任务分配表", 行 2 (成员 A), 列 D | 全部文件路径按上表映射替换；回退需恢复此单元格原值（见原始 Excel 或 git `f63b6ab` 版本） |
| 2 | `任务分配表.xlsx` | Sheet "任务分配表", 行 3 (成员 B), 列 D | 全部文件路径按上表映射替换；删除了 `core/i18n.py`（已转入 Qt 原生 i18n 机制） |
| 3 | `任务分配表.xlsx` | Sheet "任务分配表", 行 4 (成员 C), 列 D | 全部文件路径按上表映射替换；`reader/readability_pipeline.py` 拆入 `core/reader/`（由成员 A 配合） |

**⚠ 注意事项**：
- 成员 A 的 `core/task_queue.py` 已删除（AgentRuntime 的状态机覆盖此职责）
- 成员 A 的 `core/http_client.py` 已删除（直接使用 httpx.AsyncClient，无需封装层）
- 成员 B 的 `core/i18n.py` 已删除（i18n 走 Qt `tr()` + `QTranslator`，见 B-4）
- 成员 C 的 `reader/readability_pipeline.py` 拆为 `core/reader/` 下四个文件（pipeline/readability/markdown/cache），需成员 A 配合实现核心逻辑

**具体操作**：

| 文件 | 修改内容 |
|------|---------|
| **任务分配表.xlsx** | 将"具体文件/任务"列的所有路径按上表替换；同步更新 AGENTS.md §13 中项目文档状态为"✅ 已对齐" |
| **AGENTS.md §6** | 确认文件结构无需修改（已为正确版本） |
| **PLAN.md** | 逐个里程碑核对"受影响文件"列表是否与 AGENTS.md §6 一致，不一致的予以修正 |

---

## 🟡 B 类 — 中等冲突（逻辑与语义矛盾）

### B-1. 补充 AGENTS.md §6 缺失的 `html_renderer.py` 和 `theme_manager.py` [冲突 #2, #8]

**问题**：AGENTS.md §11 引用了这两个文件，但 §6 文件结构中没有定义它们。PLAN.md §2.3 明确将其放在 `ui/reader/` 下。

**订正方案**：在 AGENTS.md §6 的 `ui/reader/` 目录下补充这两个文件的条目。

**具体操作**：

```diff
  ├── ui/
  │   ├── reader/
  │   │   ├── reader_view.py
  │   │   ├── reader_toolbar.py
+ │   │   ├── html_renderer.py    # Markdown → HTML + QWebEngineView 渲染
+ │   │   ├── theme_manager.py    # Reader CSS 生成与主题设置持久化
  │   │   └── theme.py
```

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §6 文件结构 `ui/reader/` (原行 93–96) | `old: reader_view.py, reader_toolbar.py, theme.py 三行` → `new: 增加 html_renderer.py 和 theme_manager.py 两行` |

---

### B-2. 补充 qasync 到 AGENTS.md 技术栈表格 [冲突 #3]

**问题**：AGENTS.md §14 明确依赖 `qasync`，PLAN.md 和 INIT.md 也都列出，唯独 AGENTS.md §3 技术栈表格遗漏。

**订正方案**：在 AGENTS.md §3 表格"异步 I/O"行中补充。

**具体操作**：

```diff
- | 异步 I/O | asyncio + httpx | 所有网络请求和数据库读写 |
+ | 异步 I/O | asyncio + httpx + qasync | 所有网络请求和数据库读写；qasync 集成 asyncio 与 Qt 事件循环 |
```

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §3 技术栈表格 (原行 33) | `old: "asyncio + httpx"` → `new: "asyncio + httpx + qasync"` |

---

### B-3. 更新 PLAN.md 附录的 AGENTS.md 章节引用编号 [冲突 #4]

**问题**：AGENTS.md 在增加 §12（测试规范）后所有后续章节编号 +1，PLAN.md 附录未同步。

**订正方案**：

| PLAN.md 附录原引用 | 修改为 |
|-------------------|--------|
| `AGENTS.md §12 当前状态` | `AGENTS.md §13 当前状态` |
| `AGENTS.md §13 关键设计决策` | `AGENTS.md §14 关键设计决策` |
| `AGENTS.md §14 已知问题` | `AGENTS.md §15 已知问题` |

> **预防措施**：将 PLAN.md 中的硬编码章节号替换为章节标题引用（如"AGENTS.md 当前状态章节"），避免未来再次偏移。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `PLAN.md` | 附录更新协议 (行 585) | `old: "AGENTS.md §12 当前状态"` → `new: "AGENTS.md 中'当前状态'章节"` |
| 2 | `PLAN.md` | 附录更新协议 (行 587) | `old: "AGENTS.md §13 关键设计决策"` → `new: "AGENTS.md 中'关键设计决策'章节"` |
| 3 | `PLAN.md` | 附录更新协议 (行 588) | `old: "AGENTS.md §14 已知问题"` → `new: "AGENTS.md 中'已知问题'章节"` |

---

### B-4. 国际化（i18n）职责归属明确化 [冲突 #9]

**问题**：任务分配表将 `core/i18n.py` 分配给成员 B，但 AGENTS 和 PLAN 都将 i18n 定位为 UI 层的 Qt 翻译机制。

**订正方案**：删除 `core/i18n.py`（i18n 不走 core 模块），将职责拆分：

| 职责 | 归属 | 说明 |
|------|------|------|
| UI 层 `tr()` 调用审查与 `QTranslator` 加载 | 成员 C（UI 工程师） | `app/app.py` 语言加载逻辑、`resources/i18n/` |
| 翻译文件 `.ts` 的英文翻译填充 | 成员 B（配合） | 仅翻译文本内容，不涉及代码 |

**具体操作**：

| 文件 | 修改内容 |
|------|---------|
| **任务分配表.xlsx** | 成员 B 的"具体文件"中删除 `core/i18n.py`；替换为"英文 `.ts` 翻译文件填充" |
| **PLAN.md §5.4** | 确认职责描述中明确 UI 代码由成员 C 负责，翻译文本由成员 B 配合 |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `任务分配表.xlsx` | 成员 B, 列 D | 末尾新增一行："英文 .ts 翻译文件内容填充（配合成员 C 的 Qt 翻译机制）" |
| 2 | `任务分配表.xlsx` | 成员 C, 列 D | 在 `app/app.py` 前插入一行："resources/i18n/: Qt .ts 翻译源文件管理" |

---

### B-5. INIT.md 数据库技术栈行去重 [冲突 #5]

**问题**：INIT.md §1.2 技术栈表格中 sqlite3 出现了两行，且约束条件不同。

**订正方案**：合并为一行。

**具体操作**：

```diff
- | 数据库 | sqlite3 + 单线程数据库执行器 | 避免阻塞 UI 主线程 |
- | 数据库 | Python sqlite3（内建） | 不引入 ORM |
+ | 数据库 | Python sqlite3（内建）| WAL 模式，通过 run_in_executor 异步包装，不引入 ORM |
```

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `INIT.md` | §1.2 技术栈表格 (原行 19–20) | `old: 两条 sqlite3 行` → `new: 合并为一行` |

---

## 🟢 C 类 — 轻微冲突（引用与命名不一致）

### C-1. 清理 INIT.md 中的旧文件名引用 [冲突 #11]

**问题**：PLAN.md 任务 0.1 和 AGENTS.md §13 状态表中引用历史文件名 `init1.md`，对当前开发者无实际价值且造成混淆。

**订正方案**：将 `init1.md` 统一替换为 `INIT.md`。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| PLAN.md | §0 任务 0.1 | `init1.md（→ 重命名为 INIT.md）` → `INIT.md` |
| AGENTS.md | §13 状态表 | `init1.md、AGENTS.md、PLAN.md` → `INIT.md、AGENTS.md、PLAN.md` |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `PLAN.md` | Phase 0 任务 0.1 (行 27) | `old: "init1.md（→ 重命名为 INIT.md）"` → `new: "INIT.md"` |
| 2 | `AGENTS.md` | §13 状态表 (行 291) | `old: "init1.md、AGENTS.md、PLAN.md"` → `new: "INIT.md、AGENTS.md、PLAN.md"` |

---

### C-2. 在 AGENTS.md 中补充源语言策略的明确声明 [冲突 #12]

**问题**：PLAN.md §5.4 称源语言策略已在 AGENTS.md 中记录，但 AGENTS.md 中无集中声明。

**订正方案**：在 AGENTS.md §8（UI 与用户体验规范）或 §7（编码约定）末尾增加一条明确声明。

**具体操作**：在 AGENTS.md §7 末尾增加：

```markdown
- **源语言策略**：代码中用户可见字符串默认使用中文原文。英文及其他语言通过 `resources/i18n/*.ts` 翻译文件提供，由 `QTranslator` 运行时加载。`core/` 和 `store/` 中的日志与异常消息使用英文（面向开发者），不纳入翻译范围。
```

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §7 编码约定，文档规范与命名规范之间 (原行 160 之后) | `new: 新增 "源语言策略" 条目` |

---

### A-3. Agent 状态机描述不一致 [冲突 #13]

**现状**：

| 文件 | 位置 | 状态机描述 |
|------|------|-----------|
| AGENTS.md | §10 第 2 段 | `idle → running → waiting → done/error` |
| PLAN.md | §3.1 任务详情第 1 条 | `idle → queued → running → done \| error \| cancelled` |

差异：
- AGENTS.md 有 `waiting`，PLAN.md 没有（PLAN 用 `queued` 替代）
- PLAN.md 有 `cancelled` 状态，AGENTS.md 状态机未包含（但 §10 第 3 段提到取消操作）

**订正方案**：以 PLAN.md §3.1 为准（更完整，覆盖了排队和取消两种场景），更新 AGENTS.md §10。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **AGENTS.md** | §10 第 2 段 | `idle → running → waiting → done/error` → `idle → queued → running → done \| error \| cancelled` |
| **AGENTS.md** | §10 第 3 段 | "禁止自动取消正在执行的任务"保留不变；补充说明 `cancelled` 状态仅来自用户明确操作 |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §10 第 2 段 | `old: "idle → running → waiting → done/error"` → `new: "idle → queued → running → done \| error \| cancelled"` |
| 2 | `AGENTS.md` | §10 Agent UI 展示契约 | 补充 `cancelled` 状态说明：仅在用户明确取消操作时进入，取消后保留已完成内容并提供重试 |

---

### A-4. 翻译并发策略矛盾：串行 vs 并发 [冲突 #14]

**现状**：

| 文件 | 位置 | 描述 |
|------|------|------|
| INIT.md | §2.4 AI 智能助手 | "文章翻译：按段落分段翻译、Reader 内双语渲染、纯手动触发、**串行执行 + 等待队列**" |
| PLAN.md | §3.3 任务详情第 1 条 | "以 `asyncio.Semaphore(degree)` 控制**并发**（默认 3，范围 1–5），逐段调用 LLM 翻译" |

INIT.md 描述段落翻译为串行执行，PLAN.md 描述为并发（Semaphore 控制）。此外 INIT.md 的"串行执行 + 等待队列"混淆了段落级并发和文章级排队两个维度。PLAN.md §3.3 正确区分了段落级并发（Semaphore）和文章级排队（AgentRuntime）。

**订正方案**：以 PLAN.md §3.3 为准（并发段落翻译），更新 INIT.md §2.4。文章级排队由 AgentRuntime 统一管理，无需在翻译描述中重复。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **INIT.md** | §2.4 AI 智能助手 | "串行执行 + 等待队列" → "按段落并发翻译（asyncio.Semaphore 控制并发度，默认 3，范围 1–5）" |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `INIT.md` | §2.4 (原行 72) | `old: "串行执行 + 等待队列"` → `new: "按段落并发翻译（asyncio.Semaphore 控制并发度，默认 3，范围 1–5）"` |

---

### A-5. AgentUIEvent 字段不一致 [冲突 #15]

**现状**：

| 文件 | 位置 | 字段列表 |
|------|------|---------|
| AGENTS.md | §10 Agent UI 展示契约 | `run_id, entry_id, agent_type, status, chunk, error` |
| PLAN.md | §3.1 任务详情第 1 条 | `run_id, entry_id, agent_type, status, chunk, progress, error, result_json` |

PLAN.md 多了 `progress`（翻译/批量打标需要进度百分比）和 `result_json`（缓存和重试所需）。AGENTS.md 作为所有 Agent 共用数据结构的权威定义，缺少这两个字段会导致 Agent 无法正确传递进度和结果。

**订正方案**：以 PLAN.md 为准，更新 AGENTS.md §10 的 `AgentUIEvent` dataclass。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **AGENTS.md** | §10 Agent UI 展示契约 dataclass | 增加 `progress: float = 0.0` 和 `result_json: str \| None = None` 两个字段 |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §10 AgentUIEvent dataclass (原行 235–243) | `old: 6 个字段` → `new: 增加 progress: float = 0.0, result_json: str \| None = None` |

---

## 🟡 B 类 — 中等冲突（续）

### B-6. 任务分配表"负责模块"列残留已删除模块 [冲突 #16]

**问题**：CORRECTION.md A-2 已将 `core/task_queue.py` 和 `core/http_client.py` 从"具体文件"列中删除，但成员 A 的"负责模块"摘要列仍列出"任务队列"和"HTTP 客户端"。

**订正方案**：从成员 A 的"负责模块"列中删除"任务队列"和"HTTP 客户端"。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **任务分配表.xlsx** | 成员 A, 列 B "负责模块" | 删除"任务队列、"和"HTTP 客户端、" |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `任务分配表.xlsx` | 成员 A, 列 B "负责模块" | `old: "数据库、Feed CRUD、Feed Sync、OPML I/O、任务队列、HTTP 客户端、CI/CD"` → `new: "数据库、Feed CRUD、Feed Sync、OPML I/O、CI/CD"` |

---

### B-7. Share Digest 功能缺口 [冲突 #17]

**问题**：INIT.md §2.6 详细描述了 Share Digest（macOS 系统分享面板、Windows/Linux 剪贴板复制），但 AGENTS.md §5 核心功能清单和 PLAN.md Phase 5 均无此功能。属于功能范围级遗漏。

**订正方案**：Share Digest 属于平台特定功能（macOS 分享面板不可跨平台），且 PLAN.md 已包含功能更完整的 Export Digest（文件导出，Hugo 兼容）。采用"导出覆盖分享"策略：从 INIT.md §2.6 删除 Share Digest 描述，将 Digest 功能聚焦于文件导出。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **INIT.md** | §2.6 笔记与导出 | 删除 Share Digest 小节（3 行：macOS 分享面板、Windows/Linux 剪贴板、"三个平台均支持"），保留 Export Digest 描述 |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `INIT.md` | §2.6 | 删除 Share Digest 相关 3 行；保留 Export Digest / Export Multiple Digest 描述 |

---

### B-8. "自动更新"孤儿功能 [冲突 #18]

**问题**：任务分配表成员 C 的"负责模块"列出"自动更新"，但三份文档（INIT.md §2、AGENTS.md §5、PLAN.md 全部 Phase）均无此功能的定义或任务安排。

**订正方案**：从成员 C 的"负责模块"中删除"自动更新"。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **任务分配表.xlsx** | 成员 C, 列 B "负责模块" | 删除"、自动更新" |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `任务分配表.xlsx` | 成员 C, 列 B "负责模块" | `old: "...设置页、自动更新"` → `new: "...设置页"` |

---

## 🟢 C 类 — 轻微冲突（续）

### C-3. AGENTS.md §13 当前状态表未更新 [冲突 #19]

**问题**：经过 CORRECTION.md 9 项修改后，Phase 0 文档阶段实际上已完成，但 §13 状态表中除"项目文档"行外仍全部为 🔲 待开始。

**订正方案**：阶段状态表是开发进度的运行时记录，不在此次文档订正中修改（应由里程碑完成后统一更新）。但验证清单中增加此项确认。

> **决定**：状态表保持现状，在 Phase 1 正式启动时统一更新。此处仅记录不一致，不做代码修改。

---

### C-4. AGENTS.md §3 和 INIT.md §1.2 测试依赖列表不完整 [冲突 #20]

**问题**：PLAN.md §1.1 的 `pyproject.toml` 依赖列表包含 `pytest-asyncio` 和 `pytest-qt`，但 AGENTS.md §3 技术栈表格和 INIT.md §1.2 均只写 `pytest`，未提这两个插件。

**订正方案**：同步更新两份文档的测试依赖描述。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **AGENTS.md** | §3 技术栈表格 测试框架行 | `pytest` → `pytest + pytest-asyncio + pytest-qt` |
| **INIT.md** | §1.2 技术栈表格 测试行 | `pytest` → `pytest + pytest-asyncio + pytest-qt` |

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §3 技术栈表格 (原行 42) | `old: "pytest"` → `new: "pytest + pytest-asyncio + pytest-qt"` |
| 2 | `INIT.md` | §1.2 技术栈表格 | `old: "pytest \| 不用 unittest.TestCase"` → `new: "pytest + pytest-asyncio + pytest-qt \| 不用 unittest.TestCase"` |

---

### C-5. INIT.md §1.2 技术栈表格缺少部分依赖 [冲突 #21]

**问题**：以下依赖在 PLAN.md §1.1 的 `pyproject.toml` 中列出但 INIT.md §1.2 技术栈表格未体现：

| 依赖 | PLAN §1.1 | INIT.md §1.2 |
|------|:---------:|:------------:|
| `qasync` | ✅ | ❌ |
| `jinja2` | ✅ | ❌ |

**订正方案**：在 INIT.md §1.2 技术栈表格中补充这两行。

**具体操作**：

| 文件 | 位置 | 修改内容 |
|------|------|---------|
| **INIT.md** | §1.2 技术栈表格 | 新增两行：`qasync`（异步事件循环集成行补充）和 `Jinja2`（模板引擎行补充）|

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `INIT.md` | §1.2 技术栈表格 (异步事件循环行) | `old: "asyncio + httpx"` → `new: "asyncio + httpx + qasync"` |
| 2 | `INIT.md` | §1.2 技术栈表格 | 将已有 `Jinja2` 行的说明补充完整：增加"Agent 提示词 + Digest 导出" |

---

### C-6. INIT.md §2.6 模板语法描述错误：Mustache → Jinja2 [冲突 #22]

**问题**：INIT.md §2.6 描述为"模板驱动输出（YAML，Mustache 风格语法）"，但实际统一模板引擎是 Jinja2（AGENTS.md §3、§14，PLAN.md §1.1 均确认）。Mustache 和 Jinja2 语法不兼容。

**订正方案**：将"Mustache 风格语法"改为"Jinja2 语法"。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `INIT.md` | §2.6 (原行 92) | `old: "模板驱动输出（YAML，Mustache 风格语法）"` → `new: "模板驱动输出（Jinja2 语法）"` |

---

### C-7. PLAN.md §5.1 笔记编辑器控件：QTextEdit → QPlainTextEdit [冲突 #23]

**问题**：PLAN.md §5.1 指定 `QTextEdit` 作为笔记编辑器，但笔记为纯文本 Markdown（不做实时预览），应使用 `QPlainTextEdit`（性能更优、接口更简洁）。PLAN-agent-system.md §F 已正确使用 `QPlainTextEdit`。

**订正方案**：统一为 `QPlainTextEdit`。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `PLAN.md` | §5.1 任务详情 (原行 425) | `old: "QTextEdit 编辑器"` → `new: "QPlainTextEdit 编辑器"` |

---

### C-8. PLAN.md §5.4 i18n 工具名：pylupdate6 → pyside6-lupdate [冲突 #24]

**问题**：PLAN.md §5.4 使用 `pylupdate6`，PLAN-agent-system.md §I 使用 `pyside6-lupdate`。PySide6 6.5+ 中正确名称是 `pyside6-lupdate`。

**订正方案**：统一为 `pyside6-lupdate`。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `PLAN.md` | §5.4 (原行 499) | `old: "pylupdate6"` → `new: "pyside6-lupdate"` |

---

### C-9. local_tagger.py 在 AGENTS.md §6 和 INIT.md 中存在但 PLAN.md 无对应任务 [冲突 #25]

**问题**：AGENTS.md §6 列出 `core/tags/local_tagger.py`，INIT.md §2.4 提及"NLP 实体提取（本地基线）"，但 PLAN.md Phase 4 未安排此文件的实现任务。LLM 标签 Agent（§4.2）已覆盖智能标签需求，本地基线被隐性砍掉。

**订正方案**：从 AGENTS.md §6 删除 `local_tagger.py`，从 INIT.md §2.4 删除"NLP 实体提取（本地基线）+ "。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §6 文件结构 `core/tags/` | 删除 `local_tagger.py` 行 |
| 2 | `INIT.md` | §2.4 智能标签 | `old: "NLP 实体提取（本地基线）+ LLM 按需建议"` → `new: "LLM 按需建议"` |

---

### C-10. AGENTS.md §6 pipeline.py 注释包含不属于它的 Render 阶段 [冲突 #26]

**问题**：AGENTS.md §6 中 `core/reader/pipeline.py` 注释为"Fetch → Extract → Convert → Render 管线"，但 Render 阶段实际上在 `ui/reader/html_renderer.py` 中执行，不在 core/reader/ 中。

**订正方案**：将注释修正为"Fetch → Extract → Convert 管线"。

**✅ 执行记录 (2026-07-12)**：

| # | 文件 | 位置 | 回退信息 |
|---|------|------|---------|
| 1 | `AGENTS.md` | §6 文件结构 (原行 110) | `old: "Fetch → Extract → Convert → Render 管线"` → `new: "Fetch → Extract → Convert 管线"` |

---

## 执行顺序

| 步骤 | 订正项 | 涉及文件 | 预估影响 | 状态 |
|:----:|--------|---------|:--------:|:----:|
| 1 | **A-1** HTML→Markdown 工具统一 | AGENTS.md, PLAN.md | 3 处修改 | ✅ |
| 2 | **A-2** 目录结构统一 | 任务分配表.xlsx, PLAN.md | 大量路径替换 | ✅ |
| 3 | **B-1** 补充缺失文件 | AGENTS.md §6 | 新增 2 行 | ✅ |
| 4 | **B-2** 补充 qasync | AGENTS.md §3 | 修改 1 行 | ✅ |
| 5 | **B-3** 修复章节引用 | PLAN.md 附录 | 修改 3 处 | ✅ |
| 6 | **B-4** i18n 职责拆分 | 任务分配表.xlsx | 修改 1 行 | ✅ |
| 7 | **B-5** 数据库行去重 | INIT.md | 合并 2 行 | ✅ |
| 8 | **C-1** 清理旧引用 | INIT.md | 修改 1 行 | ✅ |
| 9 | **C-2** 补充源语言声明 | AGENTS.md §7 | 新增 1 段 | ✅ |
| 10 | **A-3** Agent 状态机统一 | AGENTS.md | 修改 2 处 | ✅ |
| 11 | **A-4** 翻译并发策略统一 | INIT.md | 修改 1 处 | ✅ |
| 12 | **A-5** AgentUIEvent 字段补齐 | AGENTS.md | 修改 1 处 | ✅ |
| 13 | **B-6** 任务分配表残留模块 | 任务分配表.xlsx | 修改 1 行 | ✅ |
| 14 | **B-7** Share Digest 功能缺口 | INIT.md | 删除 3 行 | ✅ |
| 15 | **B-8** "自动更新"孤儿功能 | 任务分配表.xlsx | 修改 1 行 | ✅ |
| 16 | **C-4** 测试依赖列表补全 | AGENTS.md, INIT.md | 修改 2 处 | ✅ |
| 17 | **C-5** INIT 技术栈补全 | INIT.md | 已由 B-2/B-5 覆盖 | ✅ |
| 18 | **C-6** Mustache → Jinja2 | INIT.md | 修改 1 行 | ✅ |
| 19 | **C-7** QTextEdit → QPlainTextEdit | PLAN.md | 修改 1 处 | ✅ |
| 20 | **C-8** pylupdate6 → pyside6-lupdate | PLAN.md | 修改 1 处 | ✅ |
| 21 | **C-9** local_tagger.py 缺口 | AGENTS.md, INIT.md | 删除 2 处 | ✅ |
| 22 | **C-10** pipeline.py 注释修正 | AGENTS.md | 修改 1 处 | ✅ |

---

## 订正后验证清单

- [x] `AGENTS.md` 全文通读，无内部矛盾
- [x] `AGENTS.md §6` 文件结构与 `PLAN.md` 各里程碑"受影响文件"列表一一对应
- [x] `AGENTS.md §10` Agent 状态机与 `PLAN.md §3.1` 一致（`idle → queued → running → done | error | cancelled`）
- [x] `AGENTS.md §10` AgentUIEvent 包含 `progress` 和 `result_json` 字段
- [x] `AGENTS.md §11` Reader 管线四阶段工具选型与 §3 技术栈表格一致
- [x] `AGENTS.md` 章节编号连续且 PLAN.md 附录引用指向正确章节
- [x] `INIT.md §2.4` 翻译描述为段落并发（非串行），与 `PLAN.md §3.3` 一致
- [x] `INIT.md §2.6` 已删除 Share Digest 描述
- [x] `INIT.md §1.2` 技术栈无重复行，且所有依赖在 `PLAN.md` 里程碑 1.1 的 pyproject.toml 中均有体现
- [x] `任务分配表.xlsx` 中每个文件路径都在 `AGENTS.md §6` 中存在对应条目
- [x] `任务分配表.xlsx` 成员 A 负责模块中无"任务队列"和"HTTP 客户端"
- [x] `任务分配表.xlsx` 成员 C 负责模块中无"自动更新"
- [x] `INIT.md §2.6` 模板语法描述为 Jinja2（非 Mustache）
- [x] `PLAN.md §5.1` 笔记编辑器为 `QPlainTextEdit`（非 `QTextEdit`），与 PLAN-agent-system.md 一致
- [x] `PLAN.md §5.4` i18n 工具名为 `pyside6-lupdate`（非 `pylupdate6`）
- [x] `AGENTS.md §6` 中不含 `local_tagger.py`，`INIT.md §2.4` 中不含"本地基线"
- [x] `AGENTS.md §6` `pipeline.py` 注释不含 "Render"
