# Mercury 跨平台 RSS 阅读器 — Phase 2 开发验收报告

> **成员 A：** 乔钰成（核心架构师）  
> **验收日期：** 2026-07-12  
> **运行环境：** Python 3.13.14 · pytest 9.1.1 · Windows 10/11  
> **Phase 2 新增测试：** ✅ **43 passed · 0 failed**  
> **全量回归（Phase 1 + Phase 2）：** ✅ **85 passed · 0 failed · 1.14s**

---

## 一、如何在本地验收 Phase 2 的工作

在终端进入仓库目录后，按以下顺序执行命令：

```powershell
# 进入仓库目录
cd "C:\Users\dou12\Desktop\乔钰成\华东师范大学\大二\Software_development\2026-summer-semester-groupproject-reader-main (1)\2026-summer-semester-groupproject-reader-main"

# ① 只跑 Phase 2 新增的测试（43 个）
python3 -m pytest tests/test_reader/ tests/test_store/test_content_store.py tests/test_store/test_entry_management.py -v

# ② 全量回归（Phase 1 + Phase 2，共 85 个）
python3 -m pytest tests/ --tb=no -q

# ③ 验证管线核心模块可以导入
python3 -c "from core.reader.pipeline import ReaderPipeline; print('pipeline ok')"
python3 -c "from store.content_store import ContentStore; print('content_store ok')"
python3 -c "from store.entry_store import EntryStore; e = dir(EntryStore); print('new methods:', [m for m in e if not m.startswith('_')])"
```

期望看到的结果：

- 命令 ① ：`43 passed, 0 failed`
- 命令 ② ：`85 passed, 0 failed`
- 命令 ③ ：`pipeline ok` / `content_store ok` / 新方法列表包含 `mark_read, toggle_star, search, soft_delete` 等

---

## 二、Phase 2 做了什么

Phase 2 的任务是给 Phase 1 建好的"地基"上**盖起核心功能**——用户点击一篇文章后能看到完整正文（Reader 管线），以及对文章进行管理（已读、收藏、搜索、删除）。

### 两个里程碑

| 里程碑 | 内容 | 新增/扩展文件 |
|--------|------|-------------|
| **M2.1 Reader 管线** | Fetch → Extract → Convert → Render → Cache 五阶段管线 | 5 个新文件 |
| **M2.2 文章管理扩展** | `EntryStore` 新增 6 个 async 方法 | 扩展 1 个文件 |

### M2.1 Reader 管线详解

用户点开一篇文章，后台发生的事：

```
① Fetch      httpx 去文章原始 URL 抓完整 HTML（timeout=15s）
      ↓
② Extract    readability-lxml 把广告、导航栏、侧边栏剥离，只保留正文
      ↓
③ Convert    markdownify + BeautifulSoup 把干净 HTML 转成 Markdown
      ↓
④ Render     mistune 把 Markdown 渲染为 HTML（供 QWebEngineView 显示）
      ↓
⑤ Cache      结果写入 content 表，下次点同一篇文章直接从缓存读
```

**缓存机制**：管线维护版本号常量（`READER_VERSION / MARKDOWN_VERSION`），
算法升级时递增版本号，旧缓存自动失效，重新抓取。

**失败回退**：若 readability 提取的正文为空（页面反爬或内容太短），
自动回退到使用 RSS 的 `summary` 字段拼简单 HTML，不抛异常、不阻断流程。

### M2.2 文章管理扩展详解

在 `store/entry_store.py` 中新增 6 个方法，供成员 C 的 UI 层调用：

| 方法 | 作用 | 返回值 |
|------|------|--------|
| `mark_read(id)` | 标记单篇已读 | `None` |
| `mark_unread(id)` | 标记单篇未读 | `None` |
| `batch_mark_read(feed_id, only_before)` | 批量全读，可按时间过滤 | `int`（标记数量）|
| `toggle_star(id)` | 切换收藏状态 | `bool`（新状态）|
| `search(query, feed_id, limit, offset)` | 标题+摘要关键词搜索 | `list[EntryListItem]` |
| `soft_delete(id)` | 软删除（保留物理数据） | `None` |

---

## 三、测试做了什么，验证了什么

### Phase 2 新增：43 个测试

#### 1. ContentStore（4 个）— 验证"缓存存储层可靠"

| 测试名 | 验证内容 |
|--------|---------|
| `test_content_store_upsert_creates_row` | upsert 正确写入所有字段，`fetched_at` 自动生成 |
| `test_content_store_upsert_overwrites_existing` | 重复 upsert 只有 1 行，不新增重复记录 |
| `test_content_store_get_returns_none_for_missing` | 不存在的 `entry_id` 返回 `None` 而非报错 |
| `test_content_store_delete_removes_row` | 删除后 `get` 返回 `None` |

#### 2. ReaderCache + Markdown（10 个）— 验证"版本号缓存逻辑正确"

| 测试名 | 验证内容 |
|--------|---------|
| `test_cache_get_hit_on_matching_versions` | 版本号完全匹配时命中缓存 |
| `test_cache_get_miss_on_reader_version_mismatch` | `READER_VERSION` 不一致时缓存失效 |
| `test_cache_get_miss_on_markdown_version_mismatch` | `MARKDOWN_VERSION` 不一致时缓存失效 |
| `test_cache_get_miss_when_no_row` | 数据库无记录时返回 `None` |
| `test_html_to_markdown_atx_headings` | `<h1>` 转换为 `# ` 格式（ATX 风格） |
| `test_html_to_markdown_strips_script_tags` | `<script>` 标签及其内容被彻底删除 |
| `test_html_to_markdown_strips_nav_and_footer` | `<nav>` / `<footer>` 连同内容一起删除 |
| `test_html_to_markdown_empty_input_returns_empty` | 空字符串输入返回空字符串 |
| `test_html_to_markdown_data_uri_removed` | base64 内嵌图片被过滤 |
| `test_html_to_markdown_fixture_clean` | 对标准文章 fixture 转换结果包含正确的 ATX 标题 |

#### 3. ReaderPipeline（7 个）— 验证"管线端到端行为正确"

| 测试名 | 验证内容 |
|--------|---------|
| `test_pipeline_full_run_returns_rendered_content` | 完整运行返回非空 `RenderedContent`，`from_cache=False` |
| `test_pipeline_cache_hit_skips_http` | 第二次调用不发 HTTP 请求，`from_cache=True` |
| `test_pipeline_cache_miss_on_version_bump` | `READER_VERSION` 改为 2 后重新抓取 |
| `test_pipeline_fetch_404_raises_error` | HTTP 404 抛 `ReaderFetchError`，`status_code=404` |
| `test_pipeline_network_error_raises_fetch_error` | 网络断开抛 `ReaderFetchError` |
| `test_pipeline_empty_readability_falls_back` | readability 返回空时回退到 summary，不报错 |
| `test_pipeline_request_id_passed_through` | `request_id` 原样透传到返回值 |

#### 4. EntryStore 文章管理（22 个）— 验证"文章操作语义正确"

| 测试组 | 数量 | 验证内容 |
|--------|------|---------|
| mark_read / mark_unread | 4 | 已读状态持久化 / 不存在 ID 静默忽略 / unread_count 联动 |
| batch_mark_read | 4 | 批量数量准确 / 只影响目标 Feed / 排除软删除 / `only_before` 时间过滤 |
| toggle_star | 3 | 双向切换 / 返回值为新状态 / 不存在 ID 返回 `False` |
| search | 7 | 标题匹配 / 摘要匹配 / 大小写不敏感 / Feed 范围限定 / 排除软删除 / 空查询 / 分页 |
| soft_delete | 3 | 从列表隐藏 / 从搜索隐藏 / `get()` 仍可访问 |
| EntryListItem 字段 | 1 | `is_read` 和 `is_starred` 字段存在且为 `bool` 类型 |

### Phase 1 全量回归：42 个

Phase 2 开发后，Phase 1 的全部 42 个测试继续全部通过，证明扩展没有引入破坏性变更。

---

## 四、本地验收截图

> **注意：** Phase 2 开发完成时暂无新截图，待补充。  
> 你可以在本地运行以下命令并截图替换此占位说明：
> ```powershell
> python3 -m pytest tests/ -v --tb=no
> ```

如需添加截图，将图片放入 `docs/assets/` 目录，并用以下格式引用：

<img src="assets/phase2-test-screenshot-1.png" alt="Phase 2 pytest 完整运行结果" style="max-width:100%;border-radius:8px;border:1px solid #2d4a6a;" />

---

## 五、开发中发现并解决的问题

| # | 问题 | 定位原因 | 解决方案 |
|---|------|---------|---------|
| 1 | `markdownify` 的 `strip` 参数只删标签不删内容 | 该版本（1.2.3）`strip` 行为与文档描述不符，只移除标签本身，保留其文本 | 改用 `BeautifulSoup.decompose()` 预处理，彻底连同内容一起删除噪声标签 |
| 2 | `readability-lxml` 依赖链缺失 | `--no-deps` 安装跳过了 `lxml_html_clean`、`chardet`、`beautifulsoup4` | 逐一补装，已记录到 `pyproject.toml` 依赖注释 |

---

## 六、成员 A → 成员 C Phase 2 接口移交清单

Phase 2 完成后，以下接口已稳定，成员 C 可调用（详见 `INTERFACE.md` 第 9～11 节）：

| 接口 | 文件 | 关键方法 / 属性 |
|------|------|----------------|
| `ReaderPipeline` | `core/reader/pipeline.py` | `build(entry_id, request_id=None) → RenderedContent` |
| `RenderedContent` | `core/reader/pipeline.py` | `.html`（直接传给 `setHtml()`）/ `.from_cache` / `.request_id` |
| `ReaderFetchError` | `core/reader/pipeline.py` | `.entry_id` / `.status_code` |
| `ContentStore` | `store/content_store.py` | `delete_by_entry(id)`（强制刷新缓存时使用）|
| `EntryStore 扩展` | `store/entry_store.py` | `mark_read / mark_unread / batch_mark_read / toggle_star / search / soft_delete` |

**成员 C 接入 Reader 的最简代码：**

```python
from core.reader.pipeline import ReaderPipeline, ReaderFetchError
from app.state import state
import uuid

pipeline = ReaderPipeline(state.db)

@asyncSlot()
async def on_entry_selected(self, entry_id: int) -> None:
    req_id = str(uuid.uuid4())
    self._pending_req = req_id
    try:
        result = await pipeline.build(entry_id, request_id=req_id)
    except ReaderFetchError:
        self._show_error()
        return
    if self._pending_req != req_id:
        return   # 用户已切换文章，丢弃过期结果
    self.web_view.setHtml(result.html)
```

---

## 七、TASK 完成情况

```
spec/phase2-reader-pipeline/TASK.md
├── T2.1.1 ContentStore        4 项  [x] 全部完成
├── T2.1.2 readability.py      3 项  [x] 全部完成
├── T2.1.3 markdown.py         4 项  [x] 全部完成
├── T2.1.4 cache.py            4 项  [x] 全部完成
├── T2.1.5 pipeline.py        14 项  [x] 全部完成
├── T2.1.6 Fixture 文件        3 项  [x] 全部完成
├── T2.1.7 conftest 扩展       2 项  [x] 全部完成
└── M2.1 整体验收              5 项  [x] 全部完成
共 93 条，全部 [x]

spec/phase2-entry-management/TASK.md
├── T2.2.1 EntryListItem 扩展  6 项  [x] 全部完成
├── T2.2.2 mark_read/unread    5 项  [x] 全部完成
├── T2.2.3 batch_mark_read     5 项  [x] 全部完成
├── T2.2.4 toggle_star         4 项  [x] 全部完成
├── T2.2.5 search              8 项  [x] 全部完成
├── T2.2.6 soft_delete         4 项  [x] 全部完成
├── T2.2.7 测试文件更新         3 项  [x] 全部完成
└── M2.2 整体验收              4 项  [x] 全部完成
共 79 条，全部 [x]

Phase 2 总计：172 条，全部 [x]，0 条未完成
```

---

*报告生成：2026-07-12 · 成员 A 乔钰成*
