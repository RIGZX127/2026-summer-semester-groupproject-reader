# Phase 3 UI 整合与运行说明

## 整合结果

本项目以 `2026-summer-semester-groupproject-reader-main (4)(1).zip` 为基础，
仅合入 `mercury-reader-phase3-ui-cleanup-complete (8).zip` 的 UI 功能：

- 文章批量选择、已读、未读、收藏和删除。
- 侧栏、文章栏、Reader 工具栏统一为 30×30 px 控件和 18×18 px 图标。
- 图标按钮恢复鼠标悬浮名称，并保留可访问名称。
- AI 摘要面板支持折叠、展开和拖动调整大小。
- 三栏顶部控件对齐。
- 字号、主题、内容宽度、翻译、阅读模式和专注模式使用紧凑图标控件。
- 移除顶部 AI 菜单和侧栏大尺寸 AI 卡片；AI 设置入口保留在左侧栏右上角的 AI 图标。

主项目中的 `core/`、`store/`、`tools/`、`pyproject.toml`、`uv.lock`、Digest、
NoteStore 和其他成员代码均未被第二个压缩包覆盖。

## Windows 推荐运行方式

在解压后的项目根目录打开 PowerShell，然后执行：

```powershell
# 首次运行：安装 uv（已经安装可跳过）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 安装项目依赖，但跳过当前项目原有的 editable-package 构建问题
uv sync --extra dev --no-install-project

# 项目代码会导入 yaml，但当前依赖文件尚未声明 PyYAML
uv pip install PyYAML

# 启动 Mercury
.\.venv\Scripts\python.exe main.py
```

以后再次运行时，只需要进入项目目录执行：

```powershell
.\.venv\Scripts\python.exe main.py
```

## 不使用 uv 的备用方式

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install PySide6 httpx feedparser beautifulsoup4 lxml readability-lxml markdownify mistune openai jinja2 qasync keyring PyYAML
.\.venv\Scripts\python.exe main.py
```

## 操作入口

1. 左侧栏右上角“加号”添加 RSS 订阅源。
2. 点击同步图标获取文章。
3. 中间文章栏右上角点击批量管理图标，可多选文章并执行批量操作。
4. 点击文章后，在右侧 Reader 顶部切换 Reader、Web 或双栏模式。
5. AI 设置不再位于顶部菜单；点击左侧栏右上角的 AI 图标打开。
6. 拖动 Reader 正文与 AI 摘要之间的横向分隔条可调整摘要区域高度。

## 验证记录

- Python 编译检查：通过。
- Ruff（本次修改的 UI、样式和 UI 测试）：通过。
- 非 UI 回归：146 项通过；1 项项目原有 Reader 测试因 Linux 环境缺少
  `libXtst.so.6` 无法执行 WebEngine 回退。
- Qt UI 动态测试：当前 Linux 环境缺少 `libEGL.so.1`，无法创建 Qt GUI；测试文件已
  完整合入，可在安装完整 PySide6 运行库的 Windows 环境执行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui -q
```
