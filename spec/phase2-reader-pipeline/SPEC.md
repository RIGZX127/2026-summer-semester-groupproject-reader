# Mercury Phase 2.1 — Reader 管线 SPEC

> 文件：`spec/phase2-reader-pipeline/SPEC.md`
> 对应 PLAN.md：里程碑 2.1 — Reader 管线（获取 + 提取 + 转换）
> 执行人：成员 A（核心架构师）
> 依赖前置：Phase 1 全部完成（store/db.py、store/entry_store.py 已稳定）
> 输出给：成员 C（`reader_view.py` 需要调用 `ReaderPipeline.build()`）

---

## 1. 这个任务要解决什么问题

Phase 1 实现了"文章从 RSS 拿下来存到数据库"。
Phase 2.1 要解决的是：**用户点击一篇文章后，Reader 面板要展示什么内容、怎么拿到它**。

RSS 里的文章 summary 通常只有摘要，完整正文需要：
1. 去文章原始 URL 抓完整 HTML（Fetch）
2. 用 readability 把导航栏、广告等噪声去掉，只保留正文（Extract）
3. 把干净的 HTML 转成 Markdown 方便渲染（Convert）
4. 缓存结果，下次点同一篇文章不用重新抓（Cache）

成员 A 负责这条管线的全部后端逻辑和缓存存储层。
成员 C 负责把结果渲染成 UI。

---

## 2. 文件清单与职责

| 文件 | 职责 | 新建/扩展 |
|------|------|-----------|
| `core/reader/pipeline.py` | 管线入口，串联四个阶段，对外暴露 `build(entry_id)` | 新建 |
| `core/reader/readability.py` | 封装 `readability-lxml`，提取正文 HTML | 新建 |
| `core/reader/markdown.py` | 封装 `markdownify`，HTML → Markdown | 新建 |
| `core/reader/cache.py` | 检查/读取/写入 `content` 表缓存 | 新建 |
| `store/content_store.py` | `content` 表的 async CRUD 接口 | 新建 |

---

## 3. 数据模型

### 3.1 RenderedContent（管线最终输出）

```python
@dataclass
class RenderedContent:
    entry_id: int
    html: str           # mistune 渲染后的 HTML，供 QWebEngineView.setHtml() 使用
    title: str          # readability 提取的文章标题（可能比 RSS 标题更准确）
    byline: str         # 作者信息（readability 提取，可为空字符串）
    from_cache: bool    # True = 从缓存读取，False = 刚刚新鲜抓取
```

### 3.2 ContentRow（数据库行模型）

```python
@dataclass
class ContentRow:
    id: int
    entry_id: int
    source_html: str | None      # 原始抓取的完整 HTML
    cleaned_html: str | None     # readability 提取后的正文 HTML
    markdown: str | None         # markdownify 转换后的 Markdown
    reader_version: int          # 当前 readability 算法版本号
    markdown_version: int        # 当前 markdownify 转换版本号
    render_version: int          # 当前 mistune 渲染版本号（供成员C使用）
    fetched_at: str              # ISO 8601，最近一次抓取时间
```

### 3.3 版本常量（定义在 pipeline.py）

```python
READER_VERSION   = 1   # 升级 readability 算法时递增
MARKDOWN_VERSION = 1   # 升级 markdownify 配置时递增
RENDER_VERSION   = 1   # 升级 mistune CSS/渲染方式时递增（由成员C维护）
```

缓存键：`(entry_id, reader_version, markdown_version)`。
三者任意一个与数据库中存储的不一致，视为缓存失效，重新抓取。

---

## 4. 各模块详细规格

### 4.1 core/reader/pipeline.py

```python
class ReaderPipeline:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def build(self, entry_id: int, request_id: str | None = None) -> RenderedContent:
        """
        主入口。流程：
          1. 调用 cache.py 检查缓存 → 命中直接返回
          2. 从 entry_store 取 entry.url
          3. httpx 抓取 HTML（timeout=15s，跟随重定向）
          4. readability 提取正文
          5. markdownify 转换
          6. mistune 渲染为 HTML（供 WebView 直接显示）
          7. 写入 content 表缓存
          8. 返回 RenderedContent

        异常处理：
          - httpx.RequestError → 抛 ReaderFetchError
          - httpx.HTTPStatusError（4xx/5xx） → 抛 ReaderFetchError
          - readability 提取结果为空 → 回退使用 entry.summary 拼简单 HTML
          - markdownify 失败 → 回退直接用 cleaned_html（不转 Markdown）
        """
```

#### ReaderFetchError

```python
class ReaderFetchError(Exception):
    """网络或 HTTP 错误。携带 entry_id 和 status_code（可为 None）。"""
    def __init__(self, message: str, entry_id: int, status_code: int | None = None): ...
```

#### 关键约束

- 管线**严格顺序执行**，单篇不并发。
- `request_id` 由调用方（成员 C 的 UI 层）传入，管线透传到返回值供 UI 校验，防止快速切换文章时渲染过期结果。
- `httpx.AsyncClient` 在每次 `build()` 调用中新建（不复用跨请求的 session），避免连接状态污染。
- User-Agent 设置为 `Mercury-Reader/1.0`。

---

### 4.2 core/reader/readability.py

```python
@dataclass
class ExtractedContent:
    cleaned_html: str   # 去噪后的正文 HTML
    title: str          # readability 提取的标题
    byline: str         # 作者信息（可为空字符串）

def extract(html: str, url: str = "") -> ExtractedContent:
    """
    对 readability.Document 的薄封装。
    - 若 readability 返回空正文（len < 100 chars），
      ExtractedContent.cleaned_html 置为空字符串，
      由 pipeline.py 触发回退逻辑。
    - url 参数传给 readability 用于解析相对链接。
    - 本函数为同步函数，由 pipeline.py 用 run_in_executor 调用。
    """
```

---

### 4.3 core/reader/markdown.py

```python
def html_to_markdown(html: str) -> str:
    """
    使用 markdownify 将 HTML 转换为 Markdown。

    markdownify 配置：
      - heading_style = ATX（# 标题而非下划线风格）
      - bullets = "-"（统一使用 - 作为列表符号）
      - strip = ["script", "style", "nav", "footer", "header"]
      - convert_img：保留图片，但若 src 为 data: URI 则丢弃
      - autolinks = True

    本函数为同步函数，由 pipeline.py 用 run_in_executor 调用。
    空字符串输入返回空字符串，不抛异常。
    """
```

---

### 4.4 core/reader/cache.py

```python
class ReaderCache:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def get(
        self,
        entry_id: int,
        reader_version: int,
        markdown_version: int,
    ) -> ContentRow | None:
        """
        精确匹配 (entry_id, reader_version, markdown_version)。
        任意字段不一致返回 None（缓存失效）。
        """

    async def save(
        self,
        entry_id: int,
        source_html: str,
        cleaned_html: str,
        markdown: str,
        reader_version: int,
        markdown_version: int,
        render_version: int,
    ) -> ContentRow:
        """
        UPSERT（已有记录则覆盖，无则插入）。
        同时更新 fetched_at 为当前 UTC 时间。
        """
```

---

### 4.5 store/content_store.py

```python
class ContentStore:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def get_by_entry(self, entry_id: int) -> ContentRow | None:
        """按 entry_id 查询，不做版本检查（返回数据库中存储的版本）。"""

    async def upsert(
        self,
        entry_id: int,
        source_html: str | None,
        cleaned_html: str | None,
        markdown: str | None,
        reader_version: int,
        markdown_version: int,
        render_version: int,
    ) -> ContentRow:
        """INSERT OR REPLACE，更新 fetched_at。"""

    async def delete_by_entry(self, entry_id: int) -> None:
        """删除指定文章的缓存（用于强制刷新场景）。"""
```

所有方法用 `run_in_executor` 包装阻塞 sqlite3 调用（与 Phase 1 的 Store 规范一致）。

---

## 5. 管线调用流（成员 C 参考）

```python
# ui/reader/reader_view.py 中的调用方式（成员C参考）
import uuid
from core.reader.pipeline import ReaderPipeline, ReaderFetchError
from app.state import state

pipeline = ReaderPipeline(state.db)

@asyncSlot()
async def load_entry(self, entry_id: int) -> None:
    request_id = str(uuid.uuid4())          # 每次加载生成唯一 ID
    self._pending_request_id = request_id   # 保存当前请求 ID
    self._show_loading()

    try:
        result = await pipeline.build(entry_id, request_id=request_id)
    except ReaderFetchError as e:
        if self._pending_request_id != request_id:
            return  # 已切换文章，丢弃
        self._show_error(str(e))
        return

    if self._pending_request_id != request_id:
        return  # 已切换文章，丢弃过期结果

    self.setHtml(result.html)   # 渲染
```

---

## 6. 测试规格

测试文件：`tests/test_reader/test_pipeline.py`、`test_cache.py`、`test_markdown.py`

### 需要准备的 fixture

- `tests/test_reader/fixture_article.html`：一段包含标题、正文、广告侧栏的 HTML（用于测试 readability 提取）
- `tests/test_reader/fixture_clean.html`：干净的正文 HTML（用于测试 markdownify 转换）

### 核心测试用例

| 测试名 | 验证内容 |
|--------|---------|
| `test_pipeline_returns_rendered_content` | 管线对 fixture HTML 运行完整，返回非空 `RenderedContent` |
| `test_pipeline_cache_hit_returns_from_cache` | 第一次运行写缓存，第二次运行不发 HTTP 请求，`from_cache=True` |
| `test_pipeline_cache_miss_on_version_bump` | `READER_VERSION` 递增后，缓存失效重新抓取 |
| `test_pipeline_fetch_error_raises` | mock httpx 返回 404，抛 `ReaderFetchError` |
| `test_pipeline_empty_readability_falls_back` | readability 返回空，回退使用 `entry.summary` |
| `test_html_to_markdown_headings` | ATX 风格标题正确转换 |
| `test_html_to_markdown_strips_scripts` | `<script>` 标签被去除 |
| `test_html_to_markdown_empty_input` | 空字符串输入返回空字符串 |
| `test_cache_get_miss_on_version_mismatch` | 数据库版本与查询版本不一致，返回 None |
| `test_cache_upsert_overwrites` | 重复 upsert 覆盖旧记录，不新增行 |

---

## 7. 与成员 C 的接口约定

**成员 A 保证（可调用时通知成员 C）：**
- `ReaderPipeline.build(entry_id, request_id=None) -> RenderedContent` 接口签名稳定
- `RenderedContent` dataclass 字段不变
- `ReaderFetchError` 异常类型固定
- `ContentStore.get_by_entry()` 供成员 C 读取缓存版本号（用于主题 CSS 注入的 `render_version`）

**成员 C 需要做的（不需要修改 A 的代码）：**
- `reader_view.py` 调用 `pipeline.build()` 并处理 `ReaderFetchError`
- 用 `result.html` 调用 `self.setHtml(html, base_url)`
- 维护 `_pending_request_id` 防止渲染过期结果
- `RENDER_VERSION` 由 C 维护（CSS 样式变化时递增）

---

## 8. 依赖说明

| 库 | 用途 | 已在 pyproject.toml |
|----|------|---------------------|
| `httpx` | 抓取文章原始 HTML | ✅ |
| `readability-lxml` | 正文提取 | ✅ |
| `markdownify` | HTML → Markdown | ✅ |
| `mistune` | Markdown → HTML | ✅（由成员C维护CSS注入） |
| `lxml` | readability-lxml 底层依赖 | ✅ |

---

## 9. 实际偏差记录（开发中填写）

> 开发完成后在此记录与本 SPEC 的实际偏差，供后续 Phase 参考。
