# tests/test_feed/test_parser.py
"""Feed 解析器单元测试（使用本地 fixture XML，不发真实网络请求）。"""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.feed.parser import (
    FeedParseError,
    _parse_blocking,
    _time_struct_to_iso,
    parse_feed,
)

FIXTURE_DIR = pathlib.Path(__file__).parent
FIXTURE_RSS = (FIXTURE_DIR / "fixture_feed.xml").read_bytes()


@pytest.mark.asyncio
async def test_parse_feed_returns_nonempty_entries() -> None:
    mock_response = MagicMock()
    mock_response.content = FIXTURE_RSS
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)
    with patch("core.feed.parser.httpx.AsyncClient", return_value=mock_client):
        feed_data = await parse_feed("https://example.com/feed")
    assert len(feed_data.entries) == 3
    assert feed_data.title == "Test RSS Feed"
    assert feed_data.entries[0].title == "Article One"
    assert feed_data.entries[0].author == "Alice"


@pytest.mark.asyncio
async def test_parse_feed_time_struct_converts_to_iso8601() -> None:
    mock_response = MagicMock()
    mock_response.content = FIXTURE_RSS
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)
    with patch("core.feed.parser.httpx.AsyncClient", return_value=mock_client):
        feed_data = await parse_feed("https://example.com/feed")
    pub = feed_data.entries[0].published_at
    assert pub is not None
    assert pub == "2024-01-15T08:30:00Z"


@pytest.mark.asyncio
async def test_parse_feed_missing_pubdate_is_none() -> None:
    mock_response = MagicMock()
    mock_response.content = FIXTURE_RSS
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)
    with patch("core.feed.parser.httpx.AsyncClient", return_value=mock_client):
        feed_data = await parse_feed("https://example.com/feed")
    assert feed_data.entries[2].published_at is None


@pytest.mark.asyncio
async def test_parse_feed_http_error_raises_parse_error() -> None:
    import httpx
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)
    with patch("core.feed.parser.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(FeedParseError, match="HTTP 404"):
            await parse_feed("https://example.com/feed")


def test_time_struct_none_returns_none() -> None:
    assert _time_struct_to_iso(None) is None


def test_parse_blocking_returns_feed_data() -> None:
    result = _parse_blocking("https://example.com/feed", FIXTURE_RSS)
    assert result.title == "Test RSS Feed"
    assert len(result.entries) == 3
