# tests/test_reader/test_pipeline.py
"""Reader 管线测试（mock httpx，不发真实网络请求）。"""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.reader.pipeline import (
    MARKDOWN_VERSION,
    READER_VERSION,
    ReaderFetchError,
    ReaderPipeline,
    RenderedContent,
)

FIXTURE_DIR = pathlib.Path(__file__).parent
FIXTURE_HTML = (FIXTURE_DIR / "fixture_article.html").read_text(encoding="utf-8")
FIXTURE_CLEAN = (FIXTURE_DIR / "fixture_clean.html").read_text(encoding="utf-8")


def _mock_http(content: str = FIXTURE_HTML, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.text = content
    mock_resp.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


@pytest.mark.asyncio
async def test_pipeline_full_run_returns_rendered_content(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p1", "https://example.com/article",
        "Python Asyncio", "Short summary", "Alice", None
    )
    pipeline = ReaderPipeline(db)
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=_mock_http()):
        result = await pipeline.build(entry.id, request_id="req-001")
    assert isinstance(result, RenderedContent)
    assert result.entry_id == entry.id
    assert result.request_id == "req-001"
    assert len(result.html) > 0
    assert result.from_cache is False


@pytest.mark.asyncio
async def test_pipeline_cache_hit_skips_http(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p2", "https://example.com/article2",
        "Cached Article", "Summary", "", None
    )
    pipeline = ReaderPipeline(db)
    mock_client = _mock_http()
    # 第一次：正常抓取，写入缓存
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client):
        await pipeline.build(entry.id)
    assert mock_client.get.call_count == 1
    # 第二次：应命中缓存，不发 HTTP
    mock_client2 = _mock_http()
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client2):
        result2 = await pipeline.build(entry.id)
    assert mock_client2.get.call_count == 0
    assert result2.from_cache is True


@pytest.mark.asyncio
async def test_pipeline_cache_miss_on_version_bump(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p3", "https://example.com/article3",
        "Version Test", "Summary", "", None
    )
    pipeline = ReaderPipeline(db)
    mock_client = _mock_http()
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client):
        await pipeline.build(entry.id)
    assert mock_client.get.call_count == 1
    # 模拟 READER_VERSION 升级到 2
    mock_client2 = _mock_http()
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client2):
        with patch("core.reader.pipeline.READER_VERSION", 2):
            result = await pipeline.build(entry.id)
    assert mock_client2.get.call_count == 1   # 缓存失效，重新抓取
    assert result.from_cache is False


@pytest.mark.asyncio
async def test_pipeline_fetch_404_raises_error(db) -> None:
    import httpx
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p4", "https://example.com/article4",
        "404 Article", "Summary", "", None
    )
    pipeline = ReaderPipeline(db)
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_resp)
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ReaderFetchError) as exc_info:
            await pipeline.build(entry.id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.entry_id == entry.id


@pytest.mark.asyncio
async def test_pipeline_network_error_raises_fetch_error(db) -> None:
    import httpx
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p5", "https://example.com/article5",
        "Net Error", "Summary", "", None
    )
    pipeline = ReaderPipeline(db)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ReaderFetchError):
            await pipeline.build(entry.id)


@pytest.mark.asyncio
async def test_pipeline_empty_readability_falls_back(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    from core.reader.readability import ExtractedContent
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p6", "https://example.com/article6",
        "Fallback Test", "This is the summary fallback text.", "", None
    )
    pipeline = ReaderPipeline(db)
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=_mock_http("<html><body>hi</body></html>")):
        with patch("core.reader.pipeline.rd_module.extract",
                   return_value=ExtractedContent("", "Fallback Test", "")):
            result = await pipeline.build(entry.id)
    # 回退时应包含 summary 内容，不抛异常
    assert "summary fallback" in result.html.lower() or "fallback" in result.html.lower()
    assert result.from_cache is False


@pytest.mark.asyncio
async def test_pipeline_request_id_passed_through(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-p7", "https://example.com/article7",
        "ReqID Test", "Summary", "", None
    )
    pipeline = ReaderPipeline(db)
    with patch("core.reader.pipeline.httpx.AsyncClient", return_value=_mock_http()):
        result = await pipeline.build(entry.id, request_id="unique-xyz-999")
    assert result.request_id == "unique-xyz-999"
