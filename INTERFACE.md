# Mercury Cross-Platform — 数据接口契约 (INTERFACE.md)

> **本文件是成员 A（核心架构师）向成员 B、C 开放的稳定 API 契约。**
> Phase 1 交付后，以下所有接口签名、参数名、返回类型均已锁定。
> **调用方（B、C）只需读本文件，无需翻阅源码。**
> 若接口需要变更，由成员 A 提前通知并更新此文件，同时在 CORRECTION.md 记录变更。

---

## 目录

1. [使用前提：获取 DatabaseManager](#1-使用前提获取-databasemanager)
2. [FeedStore — 订阅源接口](#2-feedstore--订阅源接口)
3. [EntryStore — 文章接口](#3-entrystore--文章接口)
4. [SyncService — Feed 同步接口](#4-syncservice--feed-同步接口)
5. [SyncSignals — Qt 信号接口（成员 C 专用）](#5-syncsignals--qt-信号接口成员-c-专用)
6. [OPML 工具函数](#6-opml-工具函数)
7. [全局状态 AppState](#7-全局状态-appstate)
8. [数据模型定义（只读，不可修改）](#8-数据模型定义只读不可修改)
9. [错误类型](#9-错误类型)
10. [禁止事项](#10-禁止事项)

---

## 1. 使用前提：获取 DatabaseManager

所有 Store 均需传入 `DatabaseManager` 实例。**不要自己 new 一个**，直接从全局状态取：

```python
from app.state import state

db = state.db          # DatabaseManager 实例，由 app/app.py 在启动时注入
```

实例化 Store：

```python
from store.feed_store import FeedStore
from store.entry_store import EntryStore
from core.feed.sync import SyncService

feed_store  = FeedStore(state.db)
entry_store = EntryStore(state.db)
sync_svc    = SyncService(state.db)
```

> **注意**：每次使用时实例化即可，Store 是无状态的轻量对象，没有连接池开销。

---

## 2. FeedStore — 订阅源接口

```python
from store.feed_store import FeedStore, FeedRow, DuplicateFeedError
```

### `async add(url, title="", description="") -> FeedRow`

插入一条新订阅源。

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `str` | RSS 地址，**必须唯一** |
| `title` | `str` | 订阅源名称，默认空字符串 |
| `description` | `str` | 描述，默认空字符串 |

- 返回：新插入的 `FeedRow`
- 异常：若 `url` 已存在，抛 `DuplicateFeedError`

```python
# 示例
feed = await feed_store.add("https://example.com/rss", title="Example Feed")
print(feed.id, feed.url, feed.title)
```

---

### `async get(feed_id) -> FeedRow | None`

按 ID 查单条订阅源。不存在返回 `None`。

```python
feed = await feed_store.get(42)
if feed is None:
    print("不存在")
```

---

### `async list_all() -> list[FeedRow]`

返回所有订阅源，按 `created_at` 升序排列。

```python
feeds = await feed_store.list_all()
for f in feeds:
    print(f.id, f.title)
```

---

### `async update(feed_id, *, title=None, favicon_url=None) -> None`

更新订阅源字段。**只传需要更新的字段**，未传的字段保持不变。

```python
await feed_store.update(42, title="新标题")
await feed_store.update(42, favicon_url="https://example.com/favicon.ico")
await feed_store.update(42, title="新标题", favicon_url="https://...")
```

---

### `async delete(feed_id) -> None`

删除订阅源。**关联的所有文章（entries）会被级联删除。**

```python
await feed_store.delete(42)
```

---

### `async unread_count(feed_id) -> int`

返回该订阅源下未读且未删除的文章数量。

```python
count = await feed_store.unread_count(42)
# 用于侧边栏角标显示
```

---

## 3. EntryStore — 文章接口

```python
from store.entry_store import EntryStore, EntryRow, EntryListItem
```

### `async add(feed_id, guid, url, title, summary, author, published_at) -> EntryRow`

插入一篇文章。

| 参数 | 类型 | 说明 |
|------|------|------|
| `feed_id` | `int` | 所属订阅源 ID |
| `guid` | `str` | 文章唯一标识（来自 RSS `<guid>`）|
| `url` | `str \| None` | 文章链接 |
| `title` | `str` | 文章标题 |
| `summary` | `str` | 摘要/正文摘录 |
| `author` | `str` | 作者 |
| `published_at` | `str \| None` | ISO 8601 格式，如 `"2024-01-15T08:30:00Z"` |

> ⚠️ **通常不需要手动调用 add()。** 文章由 `SyncService.sync_feed()` 自动写入。

---

### `async get(entry_id) -> EntryRow | None`

按 ID 查单篇文章（完整字段）。不存在返回 `None`。

```python
entry = await entry_store.get(100)
```

---

### `async list_by_feed(feed_id, limit=50, offset=0) -> list[EntryListItem]`

获取某订阅源的文章列表（**轻量对象，用于列表展示**）。

- 自动排除 `is_deleted=1` 的文章
- 按 `published_at DESC`（最新在前）排列
- 支持分页：`limit` + `offset`

```python
# 第一页（前 50 篇）
items = await entry_store.list_by_feed(feed_id=42, limit=50, offset=0)

# 第二页
items = await entry_store.list_by_feed(feed_id=42, limit=50, offset=50)

for item in items:
    print(item.id, item.title, item.is_read, item.is_starred)
    print(item.summary_snippet)   # 前 120 字符
```

---

### `async guid_exists(feed_id, guid) -> bool`

检查某 `(feed_id, guid)` 组合是否已存在。去重用。

```python
if not await entry_store.guid_exists(feed_id, "some-guid"):
    await entry_store.add(...)
```

---

## 4. SyncService — Feed 同步接口

```python
from core.feed.sync import SyncService
```

### `async sync_feed(feed_id) -> int`

同步单个订阅源。

- 返回：新增文章数（`>= 0`）；解析失败时返回 `-1`（`_SYNC_FAILED`）
- 自动发射 `sync_started` / `sync_finished` / `sync_error` 信号

```python
svc = SyncService(state.db)
new_count = await svc.sync_feed(42)
if new_count >= 0:
    print(f"新增 {new_count} 篇")
else:
    print("同步失败，见 sync_error 信号")
```

---

### `async sync_all(concurrency=5) -> tuple[int, int]`

并发同步所有订阅源。

- 返回：`(total_new, total_failed)`
- 单个 Feed 失败不中断其他 Feed

```python
svc = SyncService(state.db)
total_new, total_failed = await svc.sync_all()
print(f"完成：新增 {total_new} 篇，失败 {total_failed} 个源")
```

---

## 5. SyncSignals — Qt 信号接口（成员 C 专用）

`SyncService` 实例上有 `.signals` 属性，暴露以下 Qt 信号，**成员 C 在 UI 层 connect 这些信号来更新界面**。

```python
svc = SyncService(state.db)

# 某个 Feed 开始同步
svc.signals.sync_started.connect(lambda feed_id: ...)

# 某个 Feed 同步完成
svc.signals.sync_finished.connect(lambda feed_id, new_count: ...)

# 某个 Feed 同步出错
svc.signals.sync_error.connect(lambda feed_id, error_msg: ...)

# 全部 Feed 同步完成
svc.signals.sync_all_done.connect(lambda total_new, total_failed: ...)
```

### 信号签名速查

| 信号 | 参数 | 触发时机 |
|------|------|---------|
| `sync_started` | `feed_id: int` | 开始同步某个 Feed 时 |
| `sync_finished` | `feed_id: int, new_count: int` | 同步成功完成时 |
| `sync_error` | `feed_id: int, error_msg: str` | 网络或解析失败时 |
| `sync_all_done` | `total_new: int, total_failed: int` | `sync_all()` 全部完成时 |

### 完整 UI 接入示例（成员 C 参考）

```python
# 在 MainWindow 或 FeedListWidget 中
class FeedListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc = SyncService(state.db)

        # 连接信号
        self._svc.signals.sync_finished.connect(self._on_feed_synced)
        self._svc.signals.sync_all_done.connect(self._on_all_done)
        self._svc.signals.sync_error.connect(self._on_sync_error)

    def _on_feed_synced(self, feed_id: int, new_count: int) -> None:
        # 刷新该 Feed 的未读角标
        ...

    def _on_all_done(self, total_new: int, total_failed: int) -> None:
        # 更新状态栏文字
        self.status_bar.showMessage(f"同步完成：+{total_new} 篇")

    def _on_sync_error(self, feed_id: int, msg: str) -> None:
        # 在 Feed 行显示错误图标
        ...

    @asyncSlot()
    async def refresh_all(self) -> None:
        await self._svc.sync_all()
```

> `@asyncSlot()` 来自 `qasync` 库，用于在 Qt 槽中运行协程。

---

## 6. OPML 工具函数

```python
from core.feed.opml import import_opml, export_opml, FeedUrl
```

### `import_opml(xml_str: str) -> list[FeedUrl]`

解析 OPML XML 字符串，返回所有 Feed URL 列表。

```python
with open("subscriptions.opml", encoding="utf-8") as f:
    feeds = import_opml(f.read())

for item in feeds:
    print(item.url, item.title)
    await feed_store.add(item.url, title=item.title)
```

- 异常：`ValueError`（XML 格式无效时）

---

### `export_opml(feeds: list[FeedRow]) -> str`

将 `FeedRow` 列表导出为 OPML 2.0 XML 字符串。

```python
all_feeds = await feed_store.list_all()
xml_str = export_opml(all_feeds)

with open("backup.opml", "w", encoding="utf-8") as f:
    f.write(xml_str)
```

---

## 7. 全局状态 AppState

```python
from app.state import state
```

| 字段 | 类型 | 说明 | 可写？ |
|------|------|------|--------|
| `state.db` | `DatabaseManager` | 数据库实例，启动时注入 | ❌ 只读 |
| `state.feeds` | `list[FeedRow]` | 当前已加载的订阅源列表 | ✅ UI 层可更新 |
| `state.selected_feed_id` | `int \| None` | 当前选中的订阅源 ID | ✅ UI 层可更新 |
| `state.agent_runtime` | `Any \| None` | Phase 3 由成员 B 注入 | ❌ 暂不使用 |

```python
# 成员 C 示例：用户点击某个 Feed 后更新选中状态
state.selected_feed_id = feed.id
entries = await entry_store.list_by_feed(feed.id)
```

---

## 8. 数据模型定义（只读，不可修改）

> 以下 dataclass 由成员 A 定义并维护。**调用方直接使用，禁止在外部模块修改字段或继承。**

### FeedRow

```python
@dataclass
class FeedRow:
    id: int
    url: str
    title: str
    description: str
    favicon_url: str | None   # 可为 None
    created_at: str           # ISO 8601，如 "2024-01-15T08:30:00Z"
    updated_at: str
```

### EntryRow（完整字段，用于 Reader 页）

```python
@dataclass
class EntryRow:
    id: int
    feed_id: int
    guid: str
    url: str | None
    title: str
    summary: str
    author: str
    published_at: str | None  # ISO 8601 或 None
    is_read: bool
    is_starred: bool
    is_deleted: bool
    created_at: str
```

### EntryListItem（轻量字段，用于文章列表）

```python
@dataclass
class EntryListItem:
    id: int
    feed_id: int
    title: str
    summary_snippet: str   # summary 前 120 字符
    author: str
    published_at: str | None
    is_read: bool
    is_starred: bool
```

### FeedUrl（OPML 导入用）

```python
@dataclass
class FeedUrl:
    url: str
    title: str
```

---

## 9. 错误类型

| 异常 | 来自 | 触发条件 | 调用方处理建议 |
|------|------|---------|--------------|
| `DuplicateFeedError` | `store.feed_store` | `add()` 时 URL 已存在 | 提示用户"已订阅该源" |
| `FeedParseError` | `core.feed.parser` | 网络失败或 RSS 格式无效 | 通常由 `SyncService` 内部捕获并发射 `sync_error` 信号 |
| `ValueError` | `core.feed.opml` | OPML XML 格式无效 | 提示用户"文件格式错误" |

---

## 10. 禁止事项

以下行为**违反 AGENTS.md 架构原则**，成员 B、C 请勿执行：

| ❌ 禁止 | ✅ 替代方案 |
|---------|-----------|
| 在 `ui/` 代码中直接 `import sqlite3` 执行 SQL | 通过 `FeedStore` / `EntryStore` 方法访问数据 |
| 自行 `new DatabaseManager(...)` | 使用 `state.db` |
| 直接修改 `FeedRow` / `EntryRow` 的字段 | 调用对应 Store 的 `update()` 方法 |
| 在 `ui/` 中调用 `parse_feed()` | 通过 `SyncService` 触发同步 |
| 在主线程中直接调用阻塞的 sqlite3 操作 | 所有 Store 方法已内置 `run_in_executor`，直接 `await` 即可 |
| 在 `core/` 或 `store/` 中 import PySide6 | 只有 `core/feed/sync.py` 的 Signal 层允许，且已做降级处理 |

---

*最后更新：Phase 1 交付 — 2026-07-12 · 成员 A*


---

## Phase 2 新增接口（2026-07-12 更新）

---

## 9. ReaderPipeline — Reader 管线接口（成员 C 专用）

```python
from core.reader.pipeline import ReaderPipeline, RenderedContent, ReaderFetchError
from app.state import state
```

### `async build(entry_id, request_id=None) -> RenderedContent`

构建单篇文章的 Reader 视图（Fetch → Extract → Convert → Render → Cache）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `entry_id` | `int` | 文章 ID |
| `request_id` | `str \| None` | 调用方传入的唯一标识，原样返回，防止快速切换时渲染过期结果 |

- 返回：`RenderedContent`（含 `html` 可直接传给 `QWebEngineView.setHtml()`）
- 缓存命中时 `from_cache=True`，不重新抓取
- HTTP 错误 / 网络错误时抛 `ReaderFetchError`

```python
pipeline = ReaderPipeline(state.db)

@asyncSlot()
async def on_entry_selected(self, entry_id: int) -> None:
    import uuid
    req_id = str(uuid.uuid4())
    self._pending_req = req_id
    try:
        result = await pipeline.build(entry_id, request_id=req_id)
    except ReaderFetchError:
        self._show_error(); return
    if self._pending_req != req_id:
        return  # 用户已切换文章，丢弃过期结果
    self.web_view.setHtml(result.html)
```

### RenderedContent dataclass

```python
@dataclass
class RenderedContent:
    entry_id: int
    html: str           # 直接传给 QWebEngineView.setHtml()
    title: str          # readability 提取的标题（通常比 RSS 标题更准确）
    byline: str         # 作者信息（可为空字符串）
    from_cache: bool    # True = 命中缓存
    request_id: str | None
```

---

## 10. EntryStore 扩展方法（Phase 2.2 新增）

以下方法已追加到 Phase 1 的 `EntryStore`。

### `async mark_read(entry_id) -> None`
### `async mark_unread(entry_id) -> None`

```python
await entry_store.mark_read(42)
await entry_store.mark_unread(42)
```

---

### `async batch_mark_read(feed_id, only_before=None) -> int`

批量标记全读，返回实际标记数量。

```python
# 全部标记已读
count = await entry_store.batch_mark_read(feed_id=1)
# 仅标记某时间前的
count = await entry_store.batch_mark_read(feed_id=1, only_before="2024-06-01T00:00:00Z")
# 完成后刷新角标
new_count = await feed_store.unread_count(feed_id)
```

---

### `async toggle_star(entry_id) -> bool`

切换收藏状态，返回新状态（`True` = 已收藏）。

```python
is_starred = await entry_store.toggle_star(entry_id)
star_btn.setChecked(is_starred)  # 直接用返回值更新按钮
```

---

### `async search(query, feed_id=None, limit=50, offset=0) -> list[EntryListItem]`

全局或限定 Feed 内的关键词搜索（标题 + 摘要，不区分大小写）。

```python
# 搜索全部
results = await entry_store.search("Python")
# 限定 Feed
results = await entry_store.search("Python", feed_id=1)
# 分页
page2  = await entry_store.search("Python", limit=20, offset=20)
```

---

### `async soft_delete(entry_id) -> None`

软删除：`is_deleted=1`，物理数据保留，列表和搜索自动过滤。

```python
await entry_store.soft_delete(entry_id)
# 之后 list_by_feed / search 均不再返回该文章
# 但 get(entry_id) 仍可访问（is_deleted=True）
```

---

## 11. ContentStore（通常不直接调用）

```python
from store.content_store import ContentStore, ContentRow
```

成员 B/C **通常不需要直接调用**。Reader 管线的缓存读写由 `ReaderPipeline` 内部处理。
仅在需要**强制刷新**某篇文章缓存时使用：

```python
content_store = ContentStore(state.db)
await content_store.delete_by_entry(entry_id)
# 之后 pipeline.build(entry_id) 会重新抓取
```
