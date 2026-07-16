# core/reader/pipeline.py
"""Reader 管线：Fetch -> Extract -> Convert -> Render -> Cache。

对外唯一接口：ReaderPipeline.build(entry_id, request_id=None)
返回 RenderedContent，可直接传给 QWebEngineView.setHtml()。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from core.reader import markdown as md_module
from core.reader import readability as rd_module
from core.reader.cache import ReaderCache
from store.content_store import ContentStore
from store.entry_store import EntryStore

if TYPE_CHECKING:
    from store.db import DatabaseManager

# ── 版本常量（算法升级时递增，触发缓存失效）────────────────────────────
READER_VERSION   = 1
MARKDOWN_VERSION = 1
RENDER_VERSION   = 1

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_EXECUTOR_TIMEOUT = 30.0   # run_in_executor 的统一超时（秒）

# 模拟真实浏览器的请求头，降低被 Cloudflare 等 CDN 拦截的概率
# Sec-Fetch 系列是 Chromium 每次请求都发送的头，Cloudflare Bot Detection 会检查
_REQUEST_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


# ── Fetch 降级策略 ──────────────────────────────────────────────────────────

_WEBENGINE_TIMEOUT = 20.0  # QWebEngineView 加载超时（比 httpx 长，因需等 JS）


async def _fetch_article(url: str, entry_id: int) -> str:
    """获取文章 HTML。先 httpx，被拦则降级到 QWebEngineView。

    QWebEngineView = 真实 Chromium，可过 Cloudflare JS 挑战、WAF 等一切反爬。
    """
    # 第一级：httpx（快速、轻量）
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers=_REQUEST_HEADERS,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status not in (403, 429, 503):
            raise ReaderFetchError(
                f"HTTP {status} for {url}",
                entry_id=entry_id,
                status_code=status,
            ) from exc
        # 403/429/503 → 可能是 Cloudflare 拦截，降级到 WebEngine
    except httpx.RequestError:
        # 网络错误也可能是 Cloudflare 导致的（SSL 指纹等），降级
        pass

    # 第二级：QWebEngineView（真实浏览器，零配置过 Cloudflare）
    return await _fetch_via_webengine(url)


async def _fetch_via_webengine(url: str) -> str:
    """用隐藏的 QWebEnginePage（Chromium 内核）加载页面并提取 HTML。

    原理：
      1. 创建隐藏的 QWebEnginePage
      2. 加载 URL（Chromium 渲染器执行所有 JS，Cloudflare 挑战自动通过）
      3. 等待 loadFinished 信号
      4. 通过 page.toHtml() 回调获取完整 HTML
      5. 销毁 page 并返回 HTML
    """
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtWebEngineCore import QWebEnginePage

    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    page: QWebEnginePage | None = QWebEnginePage()

    def _on_load_finished(ok: bool) -> None:
        if future.done():
            return
        if not ok:
            future.set_exception(
                RuntimeError(f"QWebEnginePage failed to load: {url}")
            )
            return
        # toHtml 回调拿到渲染后的完整 HTML
        assert page is not None
        page.toHtml(lambda html: _on_html_received(html))

    def _on_html_received(html: str) -> None:
        if future.done():
            return
        future.set_result(html)

    def _on_timeout() -> None:
        if future.done():
            return
        future.set_exception(
            RuntimeError(f"QWebEnginePage load timeout ({_WEBENGINE_TIMEOUT}s): {url}")
        )
        _cleanup()

    def _cleanup() -> None:
        nonlocal page
        if page is not None:
            try:
                page.deleteLater()
            except RuntimeError:
                pass
            page = None

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(_on_timeout)
    timer.start(int(_WEBENGINE_TIMEOUT * 1000))

    page.loadFinished.connect(_on_load_finished)
    page.load(QUrl(url))

    try:
        html = await future
        return html
    finally:
        timer.stop()
        _cleanup()


class ReaderFetchError(Exception):
    """网络或 HTTP 错误。"""

    def __init__(self, message: str, entry_id: int, status_code: int | None = None) -> None:
        super().__init__(message)
        self.entry_id = entry_id
        self.status_code = status_code


@dataclass
class RenderedContent:
    entry_id: int
    html: str              # mistune 渲染后的 HTML，直接传给 QWebEngineView.setHtml()
    title: str
    byline: str
    from_cache: bool
    markdown: str = field(default="")          # 问题1：暴露原始 Markdown，供 Agent 直接使用
    request_id: str | None = field(default=None)


def _render_markdown(markdown_text: str) -> str:
    """用 mistune 将 Markdown 渲染为 HTML。"""
    import mistune  # type: ignore[import]
    renderer = mistune.HTMLRenderer()
    md = mistune.create_markdown(
        renderer=renderer,
        plugins=["table", "strikethrough", "url"],
    )
    return md(markdown_text)


def _fallback_html(title: str, summary: str) -> str:
    """readability 提取失败时的简单回退 HTML。"""
    safe_title   = title.replace("<", "&lt;").replace(">", "&gt;")
    safe_summary = summary.replace("<", "&lt;").replace(">", "&gt;")
    return f"<h1>{safe_title}</h1><p>{safe_summary}</p>"


async def _run_sync(fn, *args) -> object:
    """在 executor 中运行同步函数，附带统一超时保护。问题2.2"""
    loop = asyncio.get_running_loop()   # 问题2.1：已更新为非废弃 API
    return await asyncio.wait_for(
        loop.run_in_executor(None, fn, *args),
        timeout=_EXECUTOR_TIMEOUT,
    )


class ReaderPipeline:
    def __init__(self, db: DatabaseManager) -> None:
        self._entry_store   = EntryStore(db)
        self._cache         = ReaderCache(db)
        self._content_store = ContentStore(db)

    async def build(
        self,
        entry_id: int,
        request_id: str | None = None,
    ) -> RenderedContent:
        """
        构建单篇文章的 Reader 视图。

        1. 检查缓存 → 命中直接渲染返回
        2. Fetch 原始 HTML
        3. readability 提取正文
        4. markdownify 转 Markdown
        5. mistune 渲染为 HTML
        6. 写入缓存
        """
        # ── 0. 取文章基本信息 ───────────────────────────────────────────
        entry = await self._entry_store.get(entry_id)
        if entry is None:
            raise ReaderFetchError(
                f"Entry {entry_id} not found", entry_id=entry_id
            )

        # ── 1. 检查缓存 ─────────────────────────────────────────────────
        cached = await self._cache.get(entry_id, READER_VERSION, MARKDOWN_VERSION)
        if cached and cached.markdown:
            rendered_html = await _run_sync(_render_markdown, cached.markdown)
            return RenderedContent(
                entry_id=entry_id,
                html=rendered_html,
                title=entry.title,
                byline="",
                from_cache=True,
                markdown=cached.markdown,       # 问题1：透传缓存的 markdown
                request_id=request_id,
            )

        # ── 2. Fetch ─────────────────────────────────────────────────────
        source_html = ""
        if entry.url:
            # 先尝试 httpx（快速），403/5xx 则降级到 QWebEngineView（可过 Cloudflare）
            source_html = await _fetch_article(entry.url, entry_id)

        # ── 3. Extract（readability）────────────────────────────────────
        if source_html:
            extracted = await _run_sync(rd_module.extract, source_html, entry.url or "")
            cleaned_html = extracted.cleaned_html
            title        = extracted.title or entry.title
            byline       = extracted.byline
        else:
            cleaned_html = ""
            title        = entry.title
            byline       = ""

        # ── 4. Convert（markdownify）── 回退：用 summary ─────────────────
        if cleaned_html:
            markdown_text = await _run_sync(md_module.html_to_markdown, cleaned_html)
        else:
            # 提取失败：用 summary 生成简单 HTML，不缓存
            fallback = _fallback_html(title, entry.summary)
            return RenderedContent(
                entry_id=entry_id,
                html=fallback,
                title=title,
                byline=byline,
                from_cache=False,
                markdown="",                    # 回退路径无 markdown
                request_id=request_id,
            )

        # ── 5. Render（mistune）─────────────────────────────────────────
        rendered_html = await _run_sync(_render_markdown, markdown_text)

        # ── 6. 写缓存 ────────────────────────────────────────────────────
        await self._cache.save(
            entry_id=entry_id,
            source_html=source_html,
            cleaned_html=cleaned_html,
            markdown=markdown_text,
            reader_version=READER_VERSION,
            markdown_version=MARKDOWN_VERSION,
            render_version=RENDER_VERSION,
        )

        return RenderedContent(
            entry_id=entry_id,
            html=rendered_html,
            title=title,
            byline=byline,
            from_cache=False,
            markdown=markdown_text,             # 问题1：传出 markdown 字段
            request_id=request_id,
        )

