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

from core.reader.cache import ReaderCache
from core.reader import markdown as md_module
from core.reader import readability as rd_module
from store.content_store import ContentStore
from store.entry_store import EntryStore

if TYPE_CHECKING:
    from store.db import DatabaseManager

# ── 版本常量（算法升级时递增，触发缓存失效）────────────────────────────
READER_VERSION   = 1
MARKDOWN_VERSION = 1
RENDER_VERSION   = 1

_USER_AGENT = "Mercury-Reader/1.0"
_EXECUTOR_TIMEOUT = 30.0   # run_in_executor 的统一超时（秒）


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
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=15.0,
                    headers={"User-Agent": _USER_AGENT},
                ) as client:
                    response = await client.get(entry.url)
                    response.raise_for_status()
                    source_html = response.text
            except httpx.HTTPStatusError as exc:
                raise ReaderFetchError(
                    f"HTTP {exc.response.status_code} for {entry.url}",
                    entry_id=entry_id,
                    status_code=exc.response.status_code,
                ) from exc
            except httpx.RequestError as exc:
                raise ReaderFetchError(
                    f"Network error for {entry.url}: {exc}",
                    entry_id=entry_id,
                ) from exc

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

