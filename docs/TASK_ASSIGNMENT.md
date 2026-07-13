# Mercury 任务分配表

> 更新：2026-07-14 | 仓库：`docs/TASK_ASSIGNMENT.md`

---

## 团队

| 成员 | 角色 | 负责 |
|------|------|------|
| **A** | 后端 | 数据库、Store、Reader管线、标签核心、Digest导出 |
| **B** | AI+管理 | Agent运行时、LLM Provider、摘要/翻译/标签Agent、提示词模板 |
| **C** | UI | Qt界面、主题、对话框、i18n |

---

## 整体进度

```
Phase 0 [████] 文档 ✅
Phase 1 [████] 基础搭建 ✅
Phase 2 [██░░] Reader 🔄 G2.1完成，G2.2待A
Phase 3 [█░░░] Agent  🔄 B后端完成(G3.1+G3.2)，Agent实现+UI待做
Phase 4 [░░░░] 标签
Phase 5 [░░░░] 笔记/导出/统计/i18n
Phase 6 [░░░░] CI/打包
```

---

## 接口移交状态

| 门控 | 谁→谁 | 内容 | 状态 |
|------|-------|------|------|
| G2.1 | A→B,C | `RenderedContent` + `ReaderPipeline.build()` | ✅ 已冻结 |
| G2.2 | A→C | `EntryStore` 文章管理方法 | ⬜ 待A |
| G3.1 | B→A | `AgentRuntime` 单例注入 | ✅ 已冻结 |
| G3.2 | B→C | `AgentUIEvent` + Signals | ✅ 已冻结 |
| G3.3 | B→C | `ProviderConfig` + `LLMRouter` | ⬜ 待B确认 |
| G4.1 | A→B,C | `normalize()` + `TagStore` | ⬜ 待A |

---

## A 需要做的

| # | 任务 | 说明 | 阻塞谁 |
|---|------|------|--------|
| 1 | `store/entry_store.py` 加6个方法 | mark_read/unread, batch_mark_read, toggle_star, search, soft_delete → **G2.2** | C的文章管理UI |
| 2 | `core/tags/normalizer.py` | 标签规范化+别名解析 | B的TagAgent, C的标签UI |
| 3 | `store/tag_store.py` | 标签库+批量打标+临时标签 → **G4.1** | B的TagAgent, C的标签UI |
| 4 | `core/tags/cooccurrence.py` | 共现推荐 | — |
| 5 | `store/note_store.py` | 笔记CRUD | C的笔记编辑器 |
| 6 | `core/digest/exporter.py` + 模板 | Jinja2导出(Hugo兼容) | C的导出对话框 |
| 7 | `.github/workflows/ci.yml` | 三平台CI | — |
| 8 | PyInstaller打包 | Windows .exe + macOS .app | — |

---

## B 需要做的

| # | 任务 | 说明 | 依赖 |
|---|------|------|------|
| 1 | `core/agent/summary.py` | SummaryAgent(手动+自动,防抖,缓存) | G2.1✅ G3.1✅ |
| 2 | `core/agent/translation.py` | TranslationAgent(分段,并发,双语HTML) | G2.1✅ G3.1✅ |
| 3 | G3.3冻结 | 确认ProviderConfig+LLMRouter接口 | — |
| 4 | `core/agent/tagging.py` | TagAgent(LLM建议+去重+批量) | G4.1⬜ |

---

## C 需要做的

| # | 任务 | 说明 | 依赖 |
|---|------|------|------|
| 1 | `ui/reader/theme.py` + `theme_manager.py` | 主题系统(预设+自定义+持久化) | 无，立即做 |
| 2 | `ui/reader/reader_view.py` 管线对接 | 调用ReaderPipeline,占位层,回退,错误重试 | G2.1✅ |
| 3 | `ui/entry_list.py` 扩展 | 已读/收藏/右键菜单 | G2.2⬜ |
| 4 | 搜索栏组件 | 标题+摘要搜索 | G2.2⬜ |
| 5 | `ui/reader/reader_toolbar.py` | 模式切换+主题+导出 | G2.1✅ |
| 6 | `ui/dialogs/opml_dialog.py` | OPML导入导出UI | Phase1✅ |
| 7 | `ui/settings/provider_panel.py` | LLM提供者配置 | G3.3⬜ |
| 8 | `ui/settings/agent_panel.py` | Agent类型设置 | G3.3⬜ |
| 9 | `ui/reader/summary_panel.py` | 摘要面板(可折叠,流式) | G3.2✅ |
| 10 | 翻译按钮+双语渲染 | reader_toolbar+reader_view扩展 | G3.2✅ |
| 11 | `ui/dialogs/tag_manager_dialog.py` | 标签管理 | G4.1⬜ |
| 12 | 标签徽章+筛选栏 | reader_view+sidebar扩展 | G4.1⬜ |
| 13 | `ui/reader/note_editor.py` | 笔记编辑器(5s防抖) | — |
| 14 | `ui/dialogs/export_dialog.py` | 导出对话框(模板预览) | — |
| 15 | `ui/settings/usage_panel.py` | 用量统计面板 | — |
| 16 | i18n | 中英文.ts生成+运行时切换 | 所有UI稳定后 |
| 17 | 高DPI/跨平台验证 | 125%/150%/200%缩放 | Phase 6 |

---

## 当前阻塞点

```
A → entry_store.py(G2.2) → C 的文章管理UI
A → tag_store.py(G4.1)   → B 的TagAgent + C 的标签UI
B → G3.3冻结             → C 的Provider设置面板
```

---

## G2.1 接口速查（A→B,C, 已冻结）

```python
# core/reader/pipeline.py
@dataclass
class RenderedContent:
    html: str        # 渲染HTML
    title: str
    byline: str
    markdown: str    # Agent消费
    from_cache: bool

class ReaderPipeline:
    async def build(entry_id: int) -> RenderedContent: ...
```

## G3.1+G3.2 接口速查（B→A,C, 已冻结）

```python
# core/agent/runtime.py
@dataclass(frozen=True)
class AgentUIEvent:
    run_id: str; entry_id: int; agent_type: str
    status: str      # queued|running|done|error|cancelled
    chunk: str = ""; progress: float = 0.0
    error: str | None = None; result_json: str | None = None

class AgentRuntime:
    def register(agent_type, handler) -> None: ...
    def submit(entry_id, agent_type) -> str: ...  # returns run_id
    def cancel(run_id) -> None: ...
    def broadcast_chunk(run_id, entry_id, agent_type, text) -> None: ...
    signals: AgentSignals  # state_changed + chunk_received (PySide6 Signals)
```
