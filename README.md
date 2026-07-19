<div align="center">

# 🪐 Mercury RSS Reader

**跨平台智能 RSS 阅读器 · Python + PySide6 + AI Agent**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-41cd52?logo=qt)](https://doc.qt.io/qtforpython/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003b57?logo=sqlite)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## 📖 简介

**Mercury** 是一款面向阅读体验的跨平台 RSS / Atom 订阅阅读器，内置 AI Agent 能力，支持本地部署的大语言模型（Ollama）及云端模型（OpenAI / DeepSeek / 兼容 API）。

### ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📡 **RSS/Atom 订阅** | 支持任意标准 RSS 2.0 / Atom 源，OPML 批量导入导出 |
| 📰 **三模式阅读** | Reader 净化模式 / Web 原始渲染 / 双栏对比模式 |
| 🤖 **AI 摘要** | 流式生成，支持自动摘要，可折叠摘要面板 |
| 🌐 **AI 翻译** | 分段并发翻译，支持原文 / 双语 / 纯译文三种视图 |
| 🏷️ **AI 标签** | LLM 智能推荐标签，本地规范化去重，共现推荐 |
| ⭐ **文章管理** | 已读/未读、收藏、软删除、全文搜索 |
| 🎨 **主题系统** | 亮色 / 暗色双主题，跟随系统，字号 & 内容宽度可调 |
| 🔧 **LLM 路由** | 支持 Ollama / OpenAI / DeepSeek / 任意 OpenAI 兼容 API |
| 💾 **本地存储** | 全量 SQLite，数据存于 `~/.mercury/`，离线可用 |

---

## 🖥️ 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11、macOS 11+、Ubuntu 20.04+ / 主流 Linux 发行版 |
| Python | **3.11 或更高版本**（推荐 3.12） |
| 内存 | ≥ 4 GB RAM（使用 AI 功能时推荐 ≥ 8 GB） |
| 磁盘 | ≥ 500 MB（含 PySide6 依赖） |
| 网络 | 订阅同步需联网；AI 功能可连接本地 Ollama 离线运行 |

---

## 🚀 本地部署指南

### ① 克隆仓库

```bash
git clone https://github.com/<your-org>/mercury-reader.git
cd mercury-reader
```

---

### 🪟 Windows

#### 方法 A：使用 `uv`（推荐，速度更快）

```powershell
# 1. 安装 uv（若未安装）
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 创建虚拟环境并安装依赖
uv venv .venv
.venv\Scripts\activate
uv pip install -e ".[dev]"

# 3. 启动
python main.py
```

#### 方法 B：使用标准 pip

```powershell
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install --upgrade pip
pip install -e ".[dev]"

# 3. 启动
python main.py
```

> **注意**：若 PySide6 安装失败，请确认 Python 版本 ≥ 3.11，并使用官方 Python（[python.org](https://python.org)）而非 Microsoft Store 版本。

---

### 🍎 macOS

#### 方式 A：下载 DMG 包（推荐，普通用户）

1. 前往 [GitHub Releases](https://github.com/RIGZX127/2026-summer-semester-groupproject-reader/releases) 下载最新的 `Mercury-macos-xxx.dmg`
2. 双击 `.dmg` 文件挂载
3. 将 **Mercury** 拖入 **Applications** 文件夹
4. 首次打开：在 Applications 中**右键 Mercury → 打开**（未签名需确认一次，仅首次）

> **提示**：若系统提示「已损坏，无法打开」，在终端执行后重试：
> ```bash
> xattr -cr /Applications/Mercury.app
> ```

---

#### 方式 B：从源码运行（开发者）

```bash
# 1. 安装 Homebrew（若未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 Python 3.12
brew install python@3.12

# 3. 创建虚拟环境并安装依赖
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# 4. 启动
python main.py
```

> **Apple Silicon (M1/M2/M3) 用户**：PySide6 已原生支持 arm64，无需 Rosetta。
---

### 🐧 Linux

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip \
    libglib2.0-0 libgl1-mesa-glx libdbus-1-3 \
    libegl1 libxkbcommon-x11-0 libxcb-icccm4 \
    libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xfixes0

# Fedora / RHEL / CentOS
sudo dnf install python3.12 python3.12-venv \
    mesa-libGL dbus-libs xcb-util-keysyms

# Arch Linux
sudo pacman -S python python-pip xcb-util-keysyms libxkbcommon-x11

# 创建虚拟环境并安装
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# 启动
python main.py
```

> **无头环境 / 服务器**：Mercury 需要图形界面（X11 或 Wayland），不支持纯命令行服务器。  
> **Wayland 用户**（KDE Plasma 6 / GNOME 45+）：若出现渲染异常，可临时设置：
> ```bash
> QT_QPA_PLATFORM=xcb python main.py
> ```

---

## ⚙️ 配置 AI 功能（可选）

Mercury 内置三个 AI Agent：**摘要**、**翻译**、**标签推荐**。AI 功能需配置 LLM Provider。

### 配置步骤

1. 启动 Mercury，点击菜单栏 **AI → AI 设置**（快捷键 `Ctrl+,`）
2. 在 **Provider** 标签页填写：
   - **API Base URL**：LLM 服务地址
   - **Model**：模型名称
   - **API Key**：密钥（本地 Ollama 可留空）
3. 在 **Agent** 标签页配置摘要语言、翻译目标语言等

### 支持的 LLM Provider

| Provider | Base URL | Model 示例 |
|----------|----------|------------|
| **本地 Ollama**（无需 Key） | `http://localhost:11434/v1` | `qwen3`、`llama3.2` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini`、`gpt-4o` |
| **任意 OpenAI 兼容 API** | 自定义 | 自定义 |

### DeepSeek / OpenAI SDK 依赖修复（Windows）

如果在 **AI 设置 → 测试连接** 中遇到类似：

```text
No module named 'openai.types.beta.realtime.conversation_item_input_audio'
```

通常是当前虚拟环境中的 `openai` SDK 版本混杂或残留损坏。请在已激活 `.venv` 的 PowerShell 中执行：

```powershell
uv pip uninstall openai
Remove-Item -Recurse -Force ".venv\Lib\site-packages\openai" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".venv\Lib\site-packages\openai-*.dist-info" -ErrorAction SilentlyContinue
uv pip install "openai==1.55.3"
python -c "import openai; print(openai.__version__); print(openai.__file__)"
```



> 安装 Ollama：[https://ollama.com](https://ollama.com)，随后运行 `ollama pull qwen3`。

---

## 🏃 运行测试

```bash
# 激活虚拟环境后
pytest                    # 运行全部测试
pytest tests/test_store/  # 仅运行 Store 层测试
pytest -v                 # 详细输出
```

---

## 📦 打包为独立可执行文件

项目已包含 `mercury.spec`，可使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller mercury.spec
```

- **Windows**：生成 `dist/Mercury.exe`
- **macOS**：生成 `dist/Mercury.app`，可进一步通过 `hdiutil` 打包为 `.dmg`

> 详细 CI 打包流程参见 `.github/workflows/release.yml`。

---

## 📁 项目结构

```
mercury-reader/
├── main.py                    # 程序入口
├── pyproject.toml             # 依赖与构建配置
├── mercury.spec               # PyInstaller 打包配置
├── app/
│   ├── app.py                 # 应用生命周期与依赖注入
│   ├── state.py               # 全局状态 (AppState)
│   └── styles.py              # Qt 样式表
├── core/
│   ├── agent/                 # AI Agent (摘要/翻译/标签/运行时)
│   ├── digest/                # Digest 导出 (Jinja2 模板)
│   ├── feed/                  # RSS 解析与同步
│   ├── reader/                # Reader 管线 (正文提取/Markdown)
│   └── tags/                  # 标签规范化与共现推荐
├── store/                     # SQLite 数据层
│   ├── db.py                  # 数据库连接管理
│   ├── migrations.py          # 版本化迁移
│   ├── entry_store.py         # 文章 CRUD
│   ├── feed_store.py          # 订阅源 CRUD
│   ├── tag_store.py           # 标签 CRUD
│   └── agent_store.py         # Agent 运行记录
├── ui/
│   ├── main_window.py         # 三栏主窗口
│   ├── entry_list.py          # 文章列表组件
│   ├── sidebar.py             # 订阅源侧边栏
│   ├── dialogs/               # 对话框 (添加订阅源等)
│   ├── reader/                # 阅读视图 (ReaderView/Toolbar/摘要面板)
│   └── settings/              # 设置面板 (Provider/Agent)
├── resources/
│   └── prompts/               # AI 提示词模板 (YAML)
├── tests/                     # 单元测试
└── docs/                      # 项目文档与任务分配
```

---

## 📊 数据存储

所有数据存储在用户主目录的 `~/.mercury/` 文件夹下：

```
~/.mercury/
├── mercury.db          # SQLite 主数据库（订阅、文章、标签、AI 记录）
└── translation_*.html  # 翻译导出缓存
```

**备份**：直接复制整个 `~/.mercury/` 文件夹即可完整备份。  
**迁移**：将备份文件夹放回新机器相同位置即可恢复。

---

## ❓ 常见问题

**Q: 文章显示"Reader 模式不可用"？**  
部分网站（如 Cloudflare 防护站点）屏蔽了 httpx 抓取，系统自动降级为内置 WebEngine 渲染原始页面，属正常行为。

**Q: AI 翻译/摘要点击无响应？**  
请先在 **AI → AI 设置** 中配置 LLM Provider，并确认 API 服务可访问。

**Q: Linux 启动报 `xcb` 错误？**  
安装 `libxcb-icccm4 libxcb-image0 libxcb-keysyms1` 等 Qt XCB 依赖，或参考上方 Linux 安装步骤。

**Q: macOS 提示"已损坏，无法打开"？**  
在终端执行：`xattr -cr /Applications/Mercury.app`，然后重新打开。

**Q: Windows Defender 拦截 Mercury.exe？**  
这是未签名可执行文件的正常提示。点击"更多信息"→"仍要运行"即可。

**Q: 如何自定义 AI 提示词？**  
编辑 `resources/prompts/` 目录下的 YAML 文件（`summary.default.yaml`、`translation.default.yaml`、`tagging.default.yaml`）即可覆盖默认提示词。

---

## 🔧 技术栈

| 层次 | 技术 |
|------|------|
| UI 框架 | PySide6 6.5+ (Qt 6) |
| 异步事件循环 | qasync + asyncio |
| 正文提取 | readability-lxml + BeautifulSoup4 |
| Markdown 渲染 | mistune + markdownify |
| RSS 解析 | feedparser + httpx |
| AI Agent | OpenAI 兼容 API（支持 Ollama / GPT / DeepSeek） |
| 提示词模板 | Jinja2 + YAML |
| 数据库 | SQLite（WAL 模式） |
| 密钥存储 | keyring（系统原生密钥链） |
| 打包 | PyInstaller |
| 代码风格 | Ruff |
| 测试 | pytest + pytest-asyncio + pytest-qt |

---



<div align="center">

**Mercury RSS Reader** · 华东师范大学 2026 夏季学期软件开发小组项目

</div>
