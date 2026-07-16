# Phase 2 UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ReaderPipeline、文章管理接口和三种阅读模式完整接入现有 PySide6 三栏 UI。

**Architecture:** 保留现有 MainWindow 协调模式和 QListWidget 列表；新增独立 ReaderToolbar、Theme、ThemeManager。所有 I/O 仍通过注入的 Store/Pipeline 异步接口完成，View 只发信号和渲染状态。

**Tech Stack:** Python 3.11+、PySide6/Qt 6、QWebEngineView、qasync、pytest、pytest-qt、QSettings。

## Global Constraints

- 不修改 EntryStore、ReaderPipeline、数据库 Schema 和稳定接口签名。
- UI 不直接执行 SQL、HTTP 或正文提取。
- UI 只在 Qt 主线程更新；异步槽使用 qasync.asyncSlot。
- 删除使用删除前确认，不提供无效撤销按钮。
- 用户可见字符串使用 tr()；Reader 禁用 JavaScript 和本地文件访问。
- 测试不访问真实网络、用户数据库或 LLM。

---

### Task 1: Reader 主题模型与持久化

**Files:**
- Create: `ui/reader/theme.py`
- Create: `ui/reader/theme_manager.py`
- Create: `tests/test_ui/test_reader_theme.py`

**Interfaces:**
- Produces: `Theme`, `ThemeManager.theme`, `set_font_size(int)`, `set_color_scheme(str)`, `set_content_width(int)`, `reader_css()`。

- [ ] **Step 1: 写失败测试**，验证默认值、边界限制、QSettings 恢复和 CSS 溢出保护。
- [ ] **Step 2: 运行** `pytest tests/test_ui/test_reader_theme.py -q`，确认因模块不存在失败。
- [ ] **Step 3: 最小实现**：不可变 Theme；ThemeManager 仅接受 14–24 px、`light|dark`、`640|760|920`。
- [ ] **Step 4: 重跑测试**，确认通过。
- [ ] **Step 5: 运行** `ruff check ui/reader/theme.py ui/reader/theme_manager.py tests/test_ui/test_reader_theme.py`。

### Task 2: Reader 工具栏

**Files:**
- Create: `ui/reader/reader_toolbar.py`
- Create: `tests/test_ui/test_reader_toolbar.py`

**Interfaces:**
- Produces: `mode_changed(str)`、`font_size_changed(int)`、`color_scheme_changed(str)`、`content_width_changed(int)`。

- [ ] **Step 1: 写失败的 pytest-qt 测试**，验证 Reader/Web/双栏互斥模式、控件信号和 accessibleName。
- [ ] **Step 2: 运行目标测试**，确认因 ReaderToolbar 不存在失败。
- [ ] **Step 3: 实现单行工具栏**，模式使用 QButtonGroup，设置使用 QComboBox/QSpinBox。
- [ ] **Step 4: 重跑目标测试并执行 ruff**。

### Task 3: ReaderView 三模式与主题

**Files:**
- Modify: `ui/reader/reader_view.py`
- Create: `tests/test_ui/test_reader_view_phase2.py`

**Interfaces:**
- Consumes: `ThemeManager`、`ReaderToolbar`。
- Produces: `show_content(html: str, url: str | None)`、`show_fallback(entry, message)`、`set_mode(str)`，保留 `show_empty/show_loading/show_error`。

- [ ] **Step 1: 写失败测试**，验证三模式页面切换、当前 HTML/URL 保留、无 URL Web 状态和 CSS 注入。
- [ ] **Step 2: 运行目标测试确认失败原因正确**。
- [ ] **Step 3: 扩展 ReaderView**：工具栏 + Reader WebView + Web WebView + 双栏 splitter；Reader 安全配置保持禁用。
- [ ] **Step 4: 实现 Feed 摘要回退 HTML 和重试页面**。
- [ ] **Step 5: 重跑测试并执行 ruff**。

### Task 4: EntryListWidget 搜索、状态与右键动作

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `tests/test_ui/test_components.py`

**Interfaces:**
- Produces: `search_requested(str)`、`mark_read_requested(int, bool)`、`star_requested(int)`、`delete_requested(int)`；条目 UserRole 保存 id，UserRole+1/+2 保存状态。

- [ ] **Step 1: 写失败测试**，覆盖搜索回车/清空、状态文字、右键动作信号、刷新后恢复 entry_id 选择。
- [ ] **Step 2: 运行目标测试确认 RED**。
- [ ] **Step 3: 添加搜索框、状态数据和自定义右键菜单**。
- [ ] **Step 4: 重跑测试并执行 ruff**。

### Task 5: MainWindow 接入文章管理和 ReaderPipeline

**Files:**
- Modify: `ui/main_window.py`
- Modify: `tests/test_ui/test_main_window.py`

**Interfaces:**
- Consumes: `ReaderPipeline.build(entry_id, request_id)` 和 EntryStore 六个稳定接口。
- Constructor adds: `reader_pipeline: ReaderPipeline`。

- [ ] **Step 1: 扩展假 Store/Pipeline 并写失败测试**：搜索范围、打开自动已读、收藏、状态切换、删除确认、失败保留、过期请求过滤。
- [ ] **Step 2: 运行目标测试确认 RED**。
- [ ] **Step 3: 注入 pipeline，连接 EntryListWidget 信号，集中实现 `refresh_entries()`**。
- [ ] **Step 4: 将 `select_entry()` 改为获取 EntryRow、标记已读、调用 Pipeline、校验 request_id、显示正文或回退**。
- [ ] **Step 5: 实现搜索、收藏、已读和删除异步槽；删除取消时不调用 Store**。
- [ ] **Step 6: 重跑目标测试并执行 ruff**。

### Task 6: 应用依赖注入与回归

**Files:**
- Modify: `app/app.py`
- Modify: `tests/test_ui/test_main_window.py`（构造调用如有需要）

**Interfaces:**
- `MercuryApp.create_main_window()` 注入 `ReaderPipeline(state.db)`。

- [ ] **Step 1: 写/更新失败测试**，断言 MainWindow 收到可用 pipeline。
- [ ] **Step 2: 修改 app/app.py 的依赖注入**。
- [ ] **Step 3: 运行** `pytest tests/test_ui/ -q`。
- [ ] **Step 4: 运行** `pytest tests/ -q`。
- [ ] **Step 5: 运行** `ruff check .`。

### Task 7: 人工验收与交付

**Files:**
- Update: `docs/superpowers/plans/2026-07-15-phase2-ui-integration.md`（勾选完成项）
- Create: updated ZIP deliverable outside repository source tree。

- [ ] **Step 1: 无头环境验证应用模块可导入**。
- [ ] **Step 2: 检查 ReaderPipeline 正文、搜索、状态、收藏、删除确认和三模式代码路径**。
- [ ] **Step 3: 生成更新后的 ZIP，排除 `__pycache__`、`.pytest_cache` 和本地数据库**。
- [ ] **Step 4: 校验 ZIP 完整性并交付测试结果与人工运行步骤**。

## 执行记录

- 已实现 Theme、ThemeManager、ReaderToolbar、三模式 ReaderView、搜索、状态菜单、ReaderPipeline 接入和删除前确认。
- 新增 pytest-qt 测试已写入，但当前容器缺少 `libEGL.so.1`，无法执行 Qt 测试；需在 Windows 或带完整 Qt 图形库的 CI 中运行。
- 非 UI 回归：`tests/test_store tests/test_feed tests/test_reader tests/test_tags` 共 85 项通过。
- 全仓库 ruff 检查通过，compileall 通过。
- Agent 测试收集暴露既有依赖缺口：代码 import `yaml`，但 `pyproject.toml` 未声明 PyYAML；本任务未修改成员 B 范围。
