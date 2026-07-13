# Mercury Cross-Platform — Phase 1 技术规格文档 (SPEC)

> 本文档是成员 A（核心架构师）在 Phase 1 开发期间的技术规格参考。
> 所有设计决策以 AGENTS.md 为权威来源，本文档仅做细化与展开。
> **开发前必读，开发中随时查阅，每个里程碑完成后在对应章节末尾补注实际偏差。**

---

## 0. Phase 1 成员 A 交付范围速查

| 里程碑 | 文件 | 成员 |
|--------|------|------|
| 1.1 脚手架 | `pyproject.toml`, `main.py`, `app/state.py`, 全部 `__init__.py` | **A** |
| 1.2 数据库 | `store/db.py`, `store/migrations.py`, `store/feed_store.py`, `store/entry_store.py` | **A** |
| 1.3 Feed 解析与同步 | `core/feed/parser.py`, `core/feed/sync.py`, `core/feed/opml.py` | **A** |
| 1.4 基础 UI（接口部分）| `app/state.py` 字段补全，Signal 定义稳定输出，供 C 调用 | **A 提供接口，C 实现 UI** |
| 测试框架 | `tests/conftest.py`, `tests/test_store/`, `tests/test_feed/` | **A** |

> 里程碑 1.4 的 UI 实现（`ui/` 目录下所有文件）归属成员 C，A 仅保证接口稳定。

---

## 1. 里程碑 1.1 — 项目脚手架

### 1.1.1 pyproject.toml 规格

```toml
[project]
name = "mercury-cross"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "PySide6>=6.5",
    "httpx>=0.27",
    "feedparser>=6.0",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "readability-lxml>=0.8",
    "markdownify>=0.13",
    "mistune>=3.0",
    "openai>=1.30",
    "jinja2>=3.1",
    "qasync>=0.27",
    "keyring>=25.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 1.1.2 main.py 规格

```python
# main.py — 程序唯一入口
# 职责：实例化 QApplication，注册组织/应用名（QSettings 命名空间），
#       启动 qasync 事件循环，加载 MainWindow。
# 不含业务逻辑，不直接导入 store / core 模块。
```

关键约束：
- `QApplication.setOrganizationName("Mercury")` + `setApplicationName("Mercury")`（QSettings 命名空间）
- 使用 `qasync.QEventLoop` 替换默认 Qt 事件循环
- 异常捕获：顶层 `try/except` 打印堆栈后以非零退出码退出

### 1.1.3 app/state.py 规格（Phase 1 初始版本）

```python
@dataclass
class AppState:
    # Phase 1 初始字段，后续里程碑增量添加
    feeds: list = field(default_factory=list)          # list[FeedRow]，Phase 1.2 补类型
    selected_feed_id: int | None = None
    db: Any | None = None                               # DatabaseManager，启动时注入
    agent_runtime: Any | None = None                   # Phase 3 注入
```

约束：`AppState` 为模块级单例，通过 `app/state.py` 的模块变量 `state = AppState()` 提供。
禁止其他模块声明可变全局变量。

### 1.1.4 目录结构（成员 A 负责创建骨架）

需创建的目录及 `__init__.py`（内容为空文件）：
```
mercury-cross/
├── app/
├── ui/
│   ├── reader/
│   ├── settings/
│   └── dialogs/
├── core/
│   ├── feed/
│   ├── reader/
│   ├── agent/
│   ├── tags/
│   └── digest/
├── store/
├── platform/
├── resources/
│   ├── prompts/
│   ├── templates/
│   └── i18n/
└── tests/
    ├── test_feed/
    ├── test_reader/
    ├── test_agent/
    ├── test_store/
    └── test_tags/
```

---

## 2. 里程碑 1.2 — 数据库 Schema 与迁移

### 2.1 store/db.py 规格

```python
class DatabaseManager:
    def __init__(self, path: str = ":memory:") -> None:
        """
        - path=":memory:" 用于测试
        - 实际路径由 platform/paths.py 提供（Phase 1 可硬编码默认路径）
        """

    @property
    def connection(self) -> sqlite3.Connection:
        """返回已配置 WAL 模式的连接，线程：主线程或 executor 线程"""

    def close(self) -> None: ...
```

PRAGMA 启动序列（按顺序执行）：
1. `PRAGMA journal_mode=WAL`
2. `PRAGMA foreign_keys=ON`
3. `PRAGMA synchronous=NORMAL`
4. 执行 `migrations.migrate(conn)`

异步包装规则：
- `db.py` 本身不提供 async 方法
- 各 Store 中使用 `asyncio.get_event_loop().run_in_executor(None, blocking_func)` 包装所有 sqlite3 调用

### 2.2 store/migrations.py 规格

```python
CURRENT_VERSION = 1   # 每次新增迁移时递增

def migrate(conn: sqlite3.Connection) -> None:
    """
    读取 PRAGMA user_version，按序执行所有 version > user_version 的迁移函数，
    每执行一个迁移后立即更新 user_version。
    使用单个事务包裹每个迁移（迁移失败则回滚该迁移，不影响已完成的迁移）。
    """

def _migration_v1(conn: sqlite3.Connection) -> None:
    """创建所有初始表（见下方 Schema 定义）"""
```

### 2.3 初始 Schema（v1）完整定义

```sql
-- feeds: RSS 订阅源
CREATE TABLE IF NOT EXISTS feeds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL DEFAULT '',
    favicon_url TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- entries: 文章
CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id      INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
    guid         TEXT    NOT NULL,
    url          TEXT,
    title        TEXT    NOT NULL DEFAULT '',
    summary      TEXT    NOT NULL DEFAULT '',
    author       TEXT    NOT NULL DEFAULT '',
    published_at TEXT,
    is_read      INTEGER NOT NULL DEFAULT 0,
    is_starred   INTEGER NOT NULL DEFAULT 0,
    is_deleted   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(feed_id, guid)
);
CREATE INDEX IF NOT EXISTS idx_entries_feed_id    ON entries(feed_id);
CREATE INDEX IF NOT EXISTS idx_entries_published  ON entries(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_entries_is_deleted ON entries(is_deleted);

-- content: Reader 管线缓存
CREATE TABLE IF NOT EXISTS content (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id         INTEGER NOT NULL UNIQUE REFERENCES entries(id) ON DELETE CASCADE,
    source_html      TEXT,
    cleaned_html     TEXT,
    markdown         TEXT,
    reader_version   INTEGER NOT NULL DEFAULT 0,
    markdown_version INTEGER NOT NULL DEFAULT 0,
    render_version   INTEGER NOT NULL DEFAULT 0,
    fetched_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- notes: 文章笔记
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id   INTEGER NOT NULL UNIQUE REFERENCES entries(id) ON DELETE CASCADE,
    body       TEXT    NOT NULL DEFAULT '',
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- tags: 标签库
CREATE TABLE IF NOT EXISTS tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    normalized_name TEXT    NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- entry_tags: 文章-标签多对多
CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);

-- tag_aliases: 标签别名
CREATE TABLE IF NOT EXISTS tag_aliases (
    alias           TEXT    NOT NULL PRIMARY KEY,
    canonical_tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE
);

-- agent_runs: AI 任务运行记录
CREATE TABLE IF NOT EXISTS agent_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    agent_type  TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'idle',
    result_json TEXT,
    error       TEXT,
    started_at  TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_entry ON agent_runs(entry_id, agent_type);

-- llm_usage: LLM 调用用量记录
CREATE TABLE IF NOT EXISTS llm_usage (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    provider          TEXT    NOT NULL,
    model             TEXT    NOT NULL,
    agent_type        TEXT    NOT NULL,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- app_settings: 键值配置
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
```

### 2.4 Dataclass 定义（store 层行模型）

```python
# store/feed_store.py
@dataclass
class FeedRow:
    id: int
    url: str
    title: str
    description: str
    favicon_url: str | None
    created_at: str
    updated_at: str

# store/entry_store.py
@dataclass
class EntryRow:
    id: int
    feed_id: int
    guid: str
    url: str | None
    title: str
    summary: str
    author: str
    published_at: str | None
    is_read: bool
    is_starred: bool
    is_deleted: bool
    created_at: str

@dataclass
class EntryListItem:
    # 轻量级，供列表视图使用
    id: int
    feed_id: int
    title: str
    summary_snippet: str   # summary 前 120 字符
    author: str
    published_at: str | None
    is_read: bool
    is_starred: bool
```

### 2.5 store/feed_store.py 公共 API

```python
class FeedStore:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def add(self, url: str, title: str = "", description: str = "") -> FeedRow: ...
    async def get(self, feed_id: int) -> FeedRow | None: ...
    async def list_all(self) -> list[FeedRow]: ...
    async def update(self, feed_id: int, *, title: str | None = None, ...) -> None: ...
    async def delete(self, feed_id: int) -> None: ...
    async def unread_count(self, feed_id: int) -> int: ...
```

### 2.6 store/entry_store.py 公共 API（Phase 1 子集）

Phase 1 仅实现以下方法，Phase 2 补充其余方法：

```python
class EntryStore:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def add(self, feed_id: int, guid: str, url: str | None, title: str,
                  summary: str, author: str, published_at: str | None) -> EntryRow: ...
    async def get(self, entry_id: int) -> EntryRow | None: ...
    async def list_by_feed(self, feed_id: int, limit: int = 50,
                            offset: int = 0) -> list[EntryListItem]: ...
    async def guid_exists(self, feed_id: int, guid: str) -> bool: ...
```

Phase 2 补充：`mark_read`, `mark_unread`, `batch_mark_read`, `toggle_star`,
`search`, `soft_delete`。

---

## 3. 里程碑 1.3 — Feed 解析与同步

### 3.1 Dataclass 定义（core 层，非数据库行模型）

```python
# core/feed/parser.py
@dataclass
class EntryData:
    guid: str
    url: str | None
    title: str
    summary: str
    author: str
    published_at: str | None   # ISO 8601 字符串，feedparser time_struct 转换

@dataclass
class FeedData:
    url: str
    title: str
    description: str
    entries: list[EntryData]
```

### 3.2 core/feed/parser.py 规格

```python
async def parse_feed(url: str, *, timeout: float = 15.0) -> FeedData:
    """
    使用 httpx.AsyncClient 获取 Feed 内容，再用 feedparser.parse() 解析。
    feedparser 的 time_struct 转换为 ISO 8601 字符串（UTC）。
    HTTP 错误 / 解析失败抛出 FeedParseError（自定义异常）。
    """
```

注意事项：
- `feedparser.parse()` 是同步调用，需用 `run_in_executor` 包装
- 空标题 Entry 用 URL 的 hostname 作为标题备用
- `guid` 不存在时使用 `entry.link` 或 `entry.id` 降级

### 3.3 core/feed/sync.py 规格

```python
class SyncService:
    def __init__(self, db: DatabaseManager) -> None: ...

    # Qt 信号（定义在 SyncService 内部的 QObject 子类或外部 Signals 类）
    # sync_started = Signal(int)          # feed_id
    # sync_finished = Signal(int, int)    # feed_id, new_count
    # sync_error = Signal(int, str)       # feed_id, error_msg
    # sync_all_done = Signal(int, int)    # total_new, total_failed

    async def sync_feed(self, feed_id: int) -> int:
        """同步单个 Feed，返回新增文章数。"""

    async def sync_all(self, concurrency: int = 5) -> tuple[int, int]:
        """
        并发同步全部 Feed。
        使用 asyncio.TaskGroup + asyncio.Semaphore(concurrency) 控制并发。
        返回 (total_new, total_failed)。
        """
```

### 3.4 core/feed/opml.py 规格

```python
@dataclass
class FeedUrl:
    url: str
    title: str

def import_opml(xml_str: str) -> list[FeedUrl]:
    """
    解析 OPML XML，提取所有 <outline type="rss"> 或含 xmlUrl 属性的节点。
    忽略文件夹层级（扁平化）。无效节点跳过，不抛异常。
    """

def export_opml(feeds: list[FeedRow]) -> str:
    """
    生成标准 OPML 2.0 XML 字符串。
    """
```

---

## 4. 测试规格

### 4.1 tests/conftest.py 核心 fixture

```python
import pytest
from store.db import DatabaseManager

@pytest.fixture
def db():
    """每个测试用例独立的内存数据库，自动迁移后提供。"""
    manager = DatabaseManager(":memory:")
    yield manager
    manager.close()

@pytest.fixture
async def feed_store(db):
    from store.feed_store import FeedStore
    return FeedStore(db)

@pytest.fixture
async def entry_store(db):
    from store.entry_store import EntryStore
    return EntryStore(db)
```

### 4.2 测试文件清单（Phase 1 成员 A 交付）

| 文件 | 覆盖场景 |
|------|---------|
| `tests/test_store/test_db.py` | 迁移幂等、user_version 正确、PRAGMA 设置 |
| `tests/test_store/test_feed_store.py` | CRUD、unread_count |
| `tests/test_store/test_entry_store.py` | add、guid_exists 去重、list_by_feed 分页 |
| `tests/test_feed/test_parser.py` | fixture RSS 解析、time_struct 转换、空 guid 降级 |
| `tests/test_feed/test_sync.py` | 单 Feed 同步新增数、重复同步无重复 GUID |
| `tests/test_feed/test_opml.py` | OPML 导入扁平化、导出往返 |

### 4.3 测试命名约定

```
test_<行为描述>_<预期结果>
# 例：
test_add_feed_persists_url_and_title
test_sync_feed_twice_no_duplicate_guids
test_import_opml_ignores_invalid_nodes
```

---

## 5. 接口契约（成员 A → 成员 C）

成员 C 在里程碑 1.4 实现 UI 时依赖以下接口，A 负责在 1.2 完成时即锁定并稳定输出：

| 接口 | 位置 | 说明 |
|------|------|------|
| `AppState.feeds: list[FeedRow]` | `app/state.py` | 所有 Feed 列表，C 的侧边栏数据源 |
| `AppState.selected_feed_id: int \| None` | `app/state.py` | 当前选中 Feed |
| `FeedStore.add()` | `store/feed_store.py` | C 的"添加 Feed"对话框调用 |
| `FeedStore.list_all()` | `store/feed_store.py` | C 的侧边栏加载 |
| `FeedStore.unread_count()` | `store/feed_store.py` | C 的侧边栏未读数徽章 |
| `EntryStore.list_by_feed()` | `store/entry_store.py` | C 的文章列表加载 |
| `SyncService.sync_feed()` | `core/feed/sync.py` | C 的手动同步触发 |
| `SyncService.sync_finished` Signal | `core/feed/sync.py` | C 监听，同步完成后刷新列表 |
| `SyncService.sync_error` Signal | `core/feed/sync.py` | C 监听，显示错误横幅 |

**约定**：A 在 1.2 完成后向 C 通知接口已稳定，C 方可开始实现依赖上述接口的 UI 部分。

---

## 6. 编码约定（Phase 1 执行要点）

1. 所有公共函数和 dataclass 字段必须有完整类型标注
2. 所有 I/O（sqlite3、httpx、feedparser）必须通过 `run_in_executor` 或 async 包装
3. 禁止在 `store/` 或 `core/` 中 import 任何 PySide6 模块
4. 日志和异常消息使用英文（面向开发者）
5. 用户可见字符串（仅出现在 `ui/` 目录，Phase 1 不涉及）使用 `tr()`
6. 每次提交前运行 `ruff check . && pytest`，保持零问题零失败

---

*文档版本：v1.0 | 对应 Phase 1 | 最后更新：2026-07*
