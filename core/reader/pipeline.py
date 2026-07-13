# core/reader/pipeline.py
"""Reader 管线：将原始文章数据加工为 Agent 可消费的 RenderedContent。

G2.1 冻结接口：RenderedContent 和 ReaderPipeline.build()。

流程
  1. 检查缓存（ContentStore.get + is_cache_valid）——有效且含 markdown 则直接返回
  2. 获取 Entry（EntryStore.get）——不存在则抛 ValueError
  3. HTTP 请求（httpx）——获取原始 HTML
  4. 正文提取（readability）——CPU 密集，在 executor 中执行
  5. HTML → Markdown 转换（markdownify）——CPU 密集，在 executor 中执行
  6. 写缓存（ContentStore.upsert）
  7. 返回 RenderedContent
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from store.db import DatabaseManager

from core.reader.cache import (
    MARKDOWN_VERSION,
    READER_VERSION,
    RENDER_VERSION,
    is_cache_valid,
)
from core.reader.markdown import html_to_markdown
from core.reader.readability import ReadabilityError, extract_content
from store.content_store import ContentStore
from store.entry_store import EntryStore


@dataclass
class RenderedContent:
    """G2.1 冻结接口：管线最终产物。"""

    html: str  # 渲染就绪的清洗后 HTML
    title: str
    byline: str
    markdown: str  # 清洗后的 Markdown（供 Agent 消费）
    from_cache: bool  # True 表示缓存命中，未发起网络请求


class ReaderPipeline:
    """串联缓存检查 -> 获取 -> 提取 -> 转换 -> 缓存的管线。"""

    def __init__(self, db: DatabaseManager) -> None:
        self._content_store = ContentStore(db)
        self._entry_store = EntryStore(db)

    async def build(self, entry_id: int) -> RenderedContent:
        """对指定 entry_id 执行完整管线，返回 RenderedContent。

        Args:
            entry_id: 文章 ID。

        Returns:
            RenderedContent 实例。

        Raises:
            ValueError: entry_id 对应的文章不存在。
            httpx.RequestError: 网络请求失败（由调用方处理）。
        """
        # ── Step 1: 缓存检查 ────────────────────────────────────────────
        cached = await self._content_store.get(entry_id)
        if cached is not None and is_cache_valid(cached) and cached.markdown is not None:
            # 缓存命中：仅需轻量 DB 读取获取标题/作者，无网络请求
            entry = await self._entry_store.get(entry_id)
            if entry is None:
                raise ValueError(f"Entry {entry_id} not found")
            return RenderedContent(
                html=cached.cleaned_html or "",
                title=entry.title,
                byline=entry.author,
                markdown=cached.markdown,
                from_cache=True,
            )

        # ── Step 2: 获取 Entry ──────────────────────────────────────────
        entry = await self._entry_store.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id} not found")

        # ── Step 3: 网络请求 ────────────────────────────────────────────
        source_html: str | None = None
        if entry.url:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(entry.url, follow_redirects=True)
                response.raise_for_status()
                source_html = response.text

        # ── Step 4: 正文提取（CPU 密集，在 executor 中运行）─────────────
        loop = asyncio.get_running_loop()
        if source_html:
            try:
                cleaned_html, title, byline = await asyncio.wait_for(
                    loop.run_in_executor(None, extract_content, source_html, entry.url or ""),
                    timeout=30.0,
                )
            except ReadabilityError:
                # 提取失败 → 回退到 feed 摘要
                cleaned_html = entry.summary
                title = entry.title
                byline = entry.author
        else:
            # 无原文 → 直接使用 feed 摘要
            cleaned_html = entry.summary
            title = entry.title
            byline = entry.author

        # ── Step 5: HTML → Markdown 转换（CPU 密集）─────────────────────
        if cleaned_html:
            markdown = await asyncio.wait_for(
                loop.run_in_executor(None, html_to_markdown, cleaned_html),
                timeout=30.0,
            )
        else:
            markdown = ""

        # ── Step 6: 写缓存 ──────────────────────────────────────────────
        await self._content_store.upsert(
            entry_id=entry_id,
            source_html=source_html,
            cleaned_html=cleaned_html or None,
            markdown=markdown or None,
            reader_version=READER_VERSION,
            markdown_version=MARKDOWN_VERSION,
            render_version=RENDER_VERSION,
        )

        # ── Step 7: 返回 ────────────────────────────────────────────────
        return RenderedContent(
            html=cleaned_html or "",
            title=title,
            byline=byline,
            markdown=markdown or "",
            from_cache=False,
        )
