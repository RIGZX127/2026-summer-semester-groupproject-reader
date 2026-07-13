# Mercury Phase 2.1 — Reader 管线 TASK

> 文件：`spec/phase2-reader-pipeline/TASK.md`
> 执行人：成员 A（核心架构师）
> 状态说明：`[x]` 待完成 · `[x]` 已完成 · `[-]` 跳过/不适用
> **规则：每完成一个子任务，立即将 `[x]` 改为 `[x]`，并在行末记录完成时间。**

---

## 前置检查（开始前确认）

- [x] `store/entry_store.py` 中 `get(entry_id)` 返回 `EntryRow`，其中含 `url` 字段
- [x] `store/db.py` 的 `DatabaseManager` 可正常传入各 Store
- [x] `content` 表已由 Phase 1 的 `migrations.py` 建立（运行 `pytest tests/test_store/test_db.py::test_migration_v1_all_tables_exist` 确认）

---

## T2.1.1 — store/content_store.py

### 数据模型
- [x] 定义 `ContentRow` dataclass（字段：`id, entry_id, source_html, cleaned_html, markdown, reader_version, markdown_version, render_version, fetched_at`）
- [x] 导出 `ContentRow` 到 `store/__init__.py`（可选）

### ContentStore 类
- [x] 实现 `ContentStore.__init__(db: DatabaseManager)`
- [x] 实现 `async get_by_entry(entry_id: int) -> ContentRow | None`
  - [x] 用 `run_in_executor` 包装 sqlite3 调用
  - [x] 无记录返回 `None`
- [x] 实现 `async upsert(entry_id, source_html, cleaned_html, markdown, reader_version, markdown_version, render_version) -> ContentRow`
  - [x] 使用 `INSERT OR REPLACE` 语句
  - [x] 自动更新 `fetched_at` 为当前 UTC 时间
  - [x] 用 `run_in_executor` 包装
- [x] 实现 `async delete_by_entry(entry_id: int) -> None`

### 子验收节点 T2.1.1-AC
- [x] `test_content_store_upsert_creates_row` 通过
- [x] `test_content_store_upsert_overwrites_existing` 通过（重复 upsert 不新增行）
- [x] `test_content_store_get_returns_none_for_missing` 通过
- [x] `test_content_store_delete_removes_row` 通过

---

## T2.1.2 — core/reader/readability.py

- [x] 定义 `ExtractedContent` dataclass（字段：`cleaned_html: str, title: str, byline: str`）
- [x] 实现同步函数 `extract(html: str, url: str = "") -> ExtractedContent`
  - [x] 使用 `readability.Document` 提取正文
  - [x] 若提取结果正文字符数 < 100，将 `cleaned_html` 置为空字符串（触发 pipeline 回退）
  - [x] `title` 取 `doc.title()`，`byline` 取 `doc.metadata.get("author", "")`（无则空字符串）
  - [x] 用 `try/except` 包裹整个提取过程，失败时返回 `ExtractedContent("", "", "")`

### 子验收节点 T2.1.2-AC
- [x] `test_extract_returns_nonempty_for_real_html` 通过（用 fixture_article.html）
- [x] `test_extract_returns_empty_for_minimal_html` 通过（输入 `<html><body>hi</body></html>`，正文太短）
- [x] `test_extract_does_not_raise_on_malformed_html` 通过（输入损坏 HTML 不抛异常）

---

## T2.1.3 — core/reader/markdown.py

- [x] 实现同步函数 `html_to_markdown(html: str) -> str`
  - [x] 使用 `markdownify.markdownify()`
  - [x] 配置 `heading_style="ATX"`
  - [x] 配置 `bullets="-"`
  - [x] `strip` 去除 `["script", "style", "nav", "footer", "header", "aside"]`
  - [x] 过滤 `data:` URI 的图片（替换为空字符串）
  - [x] 空字符串输入直接返回空字符串（不调用 markdownify）

### 子验收节点 T2.1.3-AC
- [x] `test_html_to_markdown_atx_headings` 通过（`<h1>` 转 `# `）
- [x] `test_html_to_markdown_strips_script_tags` 通过
- [x] `test_html_to_markdown_empty_input_returns_empty` 通过
- [x] `test_html_to_markdown_data_uri_removed` 通过

---

## T2.1.4 — core/reader/cache.py

- [x] 实现 `ReaderCache.__init__(db: DatabaseManager)`，内部持有 `ContentStore`
- [x] 实现 `async get(entry_id, reader_version, markdown_version) -> ContentRow | None`
  - [x] 调用 `content_store.get_by_entry(entry_id)`
  - [x] 检查 `row.reader_version == reader_version and row.markdown_version == markdown_version`
  - [x] 条件不满足返回 `None`（缓存失效）
- [x] 实现 `async save(entry_id, source_html, cleaned_html, markdown, reader_version, markdown_version, render_version) -> ContentRow`
  - [x] 直接调用 `content_store.upsert()`

### 子验收节点 T2.1.4-AC
- [x] `test_cache_get_hit_on_matching_versions` 通过
- [x] `test_cache_get_miss_on_reader_version_mismatch` 通过
- [x] `test_cache_get_miss_on_markdown_version_mismatch` 通过
- [x] `test_cache_get_miss_when_no_row` 通过

---

## T2.1.5 — core/reader/pipeline.py

### 数据模型与常量
- [x] 定义 `RenderedContent` dataclass（字段：`entry_id, html, title, byline, from_cache, request_id`）
- [x] 定义 `ReaderFetchError(Exception)`（携带 `entry_id: int, status_code: int | None`）
- [x] 定义版本常量：`READER_VERSION = 1`、`MARKDOWN_VERSION = 1`、`RENDER_VERSION = 1`

### ReaderPipeline 类
- [x] 实现 `ReaderPipeline.__init__(db: DatabaseManager)`
  - [x] 实例化 `EntryStore`、`ReaderCache`、`ContentStore`
- [x] 实现 `async build(entry_id: int, request_id: str | None = None) -> RenderedContent`

  #### 阶段 0：检查缓存
  - [x] 调用 `cache.get(entry_id, READER_VERSION, MARKDOWN_VERSION)`
  - [x] 命中时：用 `mistune` 将缓存 `markdown` 渲染为 HTML，返回 `RenderedContent(from_cache=True)`

  #### 阶段 1：Fetch
  - [x] 从 `entry_store.get(entry_id)` 取 `entry.url`
  - [x] `entry.url` 为空时直接触发回退（使用 `entry.summary`）
  - [x] `httpx.AsyncClient` 设置 `timeout=15.0`、`follow_redirects=True`
  - [x] 设置 `User-Agent: Mercury-Reader/1.0`
  - [x] HTTP 错误（raise_for_status）→ 抛 `ReaderFetchError`
  - [x] 网络错误（`httpx.RequestError`）→ 抛 `ReaderFetchError`

  #### 阶段 2：Extract
  - [x] `run_in_executor` 调用 `readability.extract(html, url=entry.url)`
  - [x] `cleaned_html` 为空时触发回退（使用 `entry.summary` 拼简单 HTML）

  #### 阶段 3：Convert
  - [x] `run_in_executor` 调用 `markdown.html_to_markdown(cleaned_html)`

  #### 阶段 4：Render
  - [x] 用 `mistune.create_markdown()` 将 Markdown 渲染为 HTML
  - [x] mistune 配置：启用 `table`、`strikethrough` 插件

  #### 阶段 5：写缓存
  - [x] `cache.save(entry_id, source_html, cleaned_html, markdown, READER_VERSION, MARKDOWN_VERSION, RENDER_VERSION)`

  #### 回退逻辑
  - [x] 回退 HTML 格式：`<h1>{title}</h1><p>{summary}</p>`
  - [x] 回退时 `from_cache=False`，不写缓存
  - [x] 回退时不抛异常，返回 `RenderedContent`

### 子验收节点 T2.1.5-AC
- [x] `test_pipeline_full_run_returns_rendered_content` 通过（mock httpx，使用 fixture HTML）
- [x] `test_pipeline_cache_hit_skips_http` 通过（第二次调用不触发 httpx）
- [x] `test_pipeline_cache_miss_on_version_bump` 通过（READER_VERSION 改为 2 后重新抓取）
- [x] `test_pipeline_fetch_404_raises_reader_fetch_error` 通过
- [x] `test_pipeline_network_error_raises_reader_fetch_error` 通过
- [x] `test_pipeline_empty_readability_falls_back_to_summary` 通过（mock readability 返回空）
- [x] `test_pipeline_request_id_passed_through` 通过（`result.request_id == input_request_id`）

---

## T2.1.6 — 测试 fixture 文件

- [x] 创建 `tests/test_reader/fixture_article.html`（包含正文 + 侧边栏 + 广告的完整 HTML，≥500 字符正文）
- [x] 创建 `tests/test_reader/fixture_clean.html`（纯净正文 HTML，含 h1/h2/p/ul/code/img）
- [x] 创建 `tests/test_reader/__init__.py`

---

## T2.1.7 — conftest.py 扩展

- [x] 在 `tests/conftest.py` 中添加 `content_store` fixture
- [x] 添加 `pipeline` fixture（传入内存 db 的 `ReaderPipeline` 实例）

---

## M2.1 里程碑整体验收

- [x] `pytest tests/test_reader/ -v` 全部通过（零失败）
- [x] `pytest tests/test_store/test_content_store.py -v` 全部通过
- [x] `ruff check core/reader/ store/content_store.py` 零问题
- [x] 通知成员 C：`ReaderPipeline.build()` 接口已稳定，可对接 `reader_view.py`
- [x] 更新 `INTERFACE.md`，补充 `ReaderPipeline`、`RenderedContent`、`ContentStore` 接口说明

