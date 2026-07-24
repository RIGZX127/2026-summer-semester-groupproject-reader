@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo Mercury RSS Reader
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 goto :python_missing
    set "PYTHON_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 正在创建独立运行环境...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :failed
) else (
    echo [1/3] 已找到运行环境。
)

echo [2/3] 正在检查运行依赖...
".venv\Scripts\python.exe" -c "import PySide6, bs4, feedparser, httpx, jinja2, keyring, lxml, markdownify, mistune, openai, qasync, readability" >nul 2>nul
if errorlevel 1 (
    echo 首次运行，正在自动安装依赖，请稍候...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -e .
    if errorlevel 1 goto :failed
) else (
    echo 运行依赖已就绪。
)

echo [3/3] 正在启动 Mercury...
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :failed
exit /b 0

:python_missing
echo.
echo 未检测到 Python 3.11 或更高版本。
echo 请从 https://www.python.org/downloads/ 安装 Python，并勾选 Add Python to PATH。
goto :pause

:failed
echo.
echo 启动失败。请保留本窗口中的错误信息。

:pause
echo.
pause
exit /b 1
