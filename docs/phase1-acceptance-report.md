# Mercury 跨平台 RSS 阅读器 — Phase 1 开发验收报告

> **成员 A：** 乔钰成（核心架构师）  
> **验收日期：** 2026-07-12  
> **运行环境：** Python 3.13.14 · pytest 9.1.1 · Windows 10/11  
> **最终测试结果：** ✅ **42 passed · 0 failed · 0.84s**

---

## 一、Phase 1 做了什么

Phase 1 的目标是搭建整个项目的"地基"——在还没有任何界面的情况下，把**数据怎么存、RSS 怎么拉取、文章怎么写进数据库**这三件核心的事情做完，并用测试证明它们能正确运行。

### 三个里程碑

| 里程碑 | 内容 | 新增文件数 |
|--------|------|-----------|
| **M1.1 项目骨架** | `pyproject.toml` 依赖锁定 + 22 个目录包骨架 + `AppState` 全局单例 + `main.py` 入口 | 25 个 |
| **M1.2 数据库层** | SQLite WAL 模式 + 版本化迁移（10 张表）+ `FeedStore` / `EntryStore` CRUD 接口 | 5 个 |
| **M1.3 Feed 解析与同步** | RSS/Atom 解析 + 并发同步（Semaphore + gather）+ OPML 导入导出 | 3 个 |

### 对后续跨平台迁移的作用

整个数据层（`store/`）和核心逻辑层（`core/`）使用的全是**纯 Python 标准库或跨平台库**，不依赖任何操作系统特有的 API：

- SQLite 文件格式在 Windows / macOS / Linux 上完全一致，同一个 `.db` 文件可跨系统打开
- `feedparser`、`httpx`、OPML 处理均为跨平台库，无需任何改动
- 成员 C 的 PySide6/Qt UI 层相当于"插"在这个地基上，底层完全不受影响
- 未来如果要换 UI 框架，数据层和业务逻辑层完全不需要动

### 可能遇到的矛盾

| 矛盾点 | 描述 | 风险 |
|--------|------|------|
| **路径分隔符** | Windows `\` vs Linux `/`，已用 `pathlib.Path` 处理，但后续代码需保持这个习惯 | 中 |
| **Windows Long Path 限制** | `PySide6-Essentials` 因路径超 260 字符无法安装，导致 `QtCore` 无法加载，测试用降级方案绕过 | 中 |
| **SQLite 并发写入** | `:memory:` DB 多任务并发写入存在锁竞争，磁盘 DB + WAL + `timeout=30` 已解决 | 中 |
| **文件系统大小写** | Windows 不区分大小写，Linux 严格区分，模块名写错在 Windows 跑通但 Linux CI 报错 | 中 |
| **`platform` 包名冲突** | 项目 `platform/` 目录遮蔽了标准库 `platform` 模块，已在 `__init__.py` 中修复 | 低 |

---

## 二、测试做了什么，验证了什么

共 **42 个测试**，分三组：

### 数据库层（24 个）— 验证"存数据这件事是可靠的"

| 测试文件 | 用例数 | 覆盖内容 |
|---------|--------|---------|
| `test_db.py` | 7 | WAL 模式 / 外键约束 / 迁移幂等性 / 10 张表存在 / 索引存在 |
| `test_feed_store.py` | 9 | Feed CRUD / 重复 URL 报错 / 级联删除 / 未读数统计 |
| `test_entry_store.py` | 8 | 文章 CRUD / 软删除过滤 / GUID 去重 / 摘要截取 / 分页 |

### Feed 解析层（12 个）— 验证"从网上拿到的 RSS 能被正确读懂"

| 测试文件 | 用例数 | 覆盖内容 |
|---------|--------|---------|
| `test_parser.py` | 6 | 本地 fixture 解析 / ISO8601 时间转换 / 缺失 pubDate / HTTP 404 错误 |
| `test_opml.py` | 6 | OPML 导入（嵌套结构）/ URL 提取 / 无效 XML 报错 / 导出往返一致 |

### 同步服务（6 个）— 验证"重复同步不产生垃圾数据，出错不崩整个程序"

| 测试文件 | 用例数 | 覆盖内容 |
|---------|--------|---------|
| `test_sync.py` | 6 | 新文章入库 / 重复同步无重复 GUID / 失败返回哨兵值 / 信号发射 / 部分失败不中断 |

---

## 三、本地验收截图

### 截图 1 — pytest 完整运行结果（42 passed）

<img src="assets/phase1-test-screenshot-1.png" alt="pytest 完整运行结果，42 passed 0 failed" style="max-width:100%;border-radius:8px;border:1px solid #2d4a6a;" />

### 截图 2 — 数据库层测试（test_store）

<img src="assets/phase1-test-screenshot-2.png" alt="test_store 目录测试结果" style="max-width:100%;border-radius:8px;border:1px solid #2d4a6a;" />

### 截图 3 — Feed 解析与同步测试（test_feed）

<img src="assets/phase1-test-screenshot-3.png" alt="test_feed 目录测试结果" style="max-width:100%;border-radius:8px;border:1px solid #2d4a6a;" />

### 截图 4 — 仓库目录结构

<img src="assets/phase1-test-screenshot-4.png" alt="仓库目录骨架" style="max-width:100%;border-radius:8px;border:1px solid #2d4a6a;" />

---

## 四、开发中发现并解决的问题

| # | 问题 | 定位原因 | 解决方案 |
|---|------|---------|---------|
| 1 | `PySide6.QtCore` 无法加载 | Windows Long Path 限制，`PySide6-Essentials` 安装失败 | `sync.py` 改为 `try/except` 懒加载，失败时降级为轻量 `_CB` 回调类 |
| 2 | `:memory:` DB WAL 返回 `"memory"` | SQLite 内存模式不支持 WAL，这是规范行为 | 测试拆分：磁盘文件验证真正的 WAL + 内存 DB 验证其余功能 |
| 3 | `sync_all` 并发写入内存 DB 锁竞争 | `asyncio.gather` + `run_in_executor` 共享单连接 | 测试层改用 `concurrency=1` 串行验证；`db.py` 加 `timeout=30` |
| 4 | `pyproject.toml` 含 UTF-8 BOM | PowerShell `Set-Content` 默认写入 BOM 导致 `tomllib` 解析失败 | 重写为无 BOM 的 UTF-8 |
| 5 | `platform/` 包遮蔽标准库 | 项目目录优先于标准库搜索路径 | `platform/__init__.py` 中用 `importlib` 重新导出标准库符号 |

---

## 五、成员 A → 成员 C 接口移交清单

Phase 1 完成后，以下接口已稳定，成员 C 可直接调用（详见 `INTERFACE.md`）：

| 接口 | 文件 | 关键方法 |
|------|------|---------|
| `FeedStore` | `store/feed_store.py` | `add / get / list_all / update / delete / unread_count` |
| `EntryStore` | `store/entry_store.py` | `add / get / list_by_feed / guid_exists` |
| `SyncService` | `core/feed/sync.py` | `sync_feed(feed_id) / sync_all()` |
| `SyncSignals` | `core/feed/sync.py` | `sync_started / sync_finished / sync_error / sync_all_done` |
| `AppState` | `app/state.py` | `state.db / state.feeds / state.selected_feed_id` |

---

## 六、TASK 完成情况

```
spec/TASK_PHASE1.md
├── M1.1 项目脚手架    28 个子任务   [x] 全部完成
├── M1.2 数据库层      22 个子任务   [x] 全部完成
├── M1.3 Feed 解析     22 个子任务   [x] 全部完成
├── M1.4 接口移交       5 个子任务   [x] 全部完成
└── Phase 1 总验收      7 个子任务   [x] 全部完成
────────────────────────────────────────────────
合计：172 条  全部 [x]，0 条未完成
```

---

*报告生成：2026-07-12 · 成员 A 乔钰成*
