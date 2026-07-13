# tests/test_reader/test_cache_and_markdown.py
"""Reader cache 版本匹配测试 + markdown 转换测试。"""
from __future__ import annotations

import pathlib
import pytest

from core.reader.cache import ReaderCache
from core.reader.markdown import html_to_markdown

FIXTURE_DIR = pathlib.Path(__file__).parent
FIXTURE_CLEAN = (FIXTURE_DIR / "fixture_clean.html").read_text(encoding="utf-8")


# ── Cache 测试 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_get_hit_on_matching_versions(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-c1", None, "T", "S", "", None)
    cache = ReaderCache(db)
    await cache.save(entry.id, "<html/>", "<p>clean</p>", "# clean", 1, 1, 1)
    result = await cache.get(entry.id, reader_version=1, markdown_version=1)
    assert result is not None
    assert result.markdown == "# clean"


@pytest.mark.asyncio
async def test_cache_get_miss_on_reader_version_mismatch(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-c2", None, "T", "S", "", None)
    cache = ReaderCache(db)
    await cache.save(entry.id, "<html/>", "<p>clean</p>", "# clean", 1, 1, 1)
    result = await cache.get(entry.id, reader_version=2, markdown_version=1)
    assert result is None


@pytest.mark.asyncio
async def test_cache_get_miss_on_markdown_version_mismatch(db) -> None:
    from store.feed_store import FeedStore
    from store.entry_store import EntryStore
    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(feed.id, "guid-c3", None, "T", "S", "", None)
    cache = ReaderCache(db)
    await cache.save(entry.id, "<html/>", "<p>clean</p>", "# clean", 1, 1, 1)
    result = await cache.get(entry.id, reader_version=1, markdown_version=2)
    assert result is None


@pytest.mark.asyncio
async def test_cache_get_miss_when_no_row(db) -> None:
    cache = ReaderCache(db)
    result = await cache.get(99999, reader_version=1, markdown_version=1)
    assert result is None


# ── Markdown 转换测试 ─────────────────────────────────────────────────────

def test_html_to_markdown_atx_headings() -> None:
    result = html_to_markdown("<h1>Main Title</h1><h2>Sub Title</h2>")
    assert "# Main Title" in result
    assert "## Sub Title" in result


def test_html_to_markdown_strips_script_tags() -> None:
    html = "<p>Content</p><script>alert('xss')</script>"
    result = html_to_markdown(html)
    assert "script" not in result
    assert "alert" not in result
    assert "Content" in result


def test_html_to_markdown_strips_nav_and_footer() -> None:
    html = "<nav>Nav links</nav><p>Real content</p><footer>Footer text</footer>"
    result = html_to_markdown(html)
    assert "Nav links" not in result
    assert "Footer text" not in result
    assert "Real content" in result


def test_html_to_markdown_empty_input_returns_empty() -> None:
    assert html_to_markdown("") == ""


def test_html_to_markdown_data_uri_removed() -> None:
    html = '<p>Text</p><img src="data:image/png;base64,abc123" alt="img"/>'
    result = html_to_markdown(html)
    assert "data:image" not in result
    assert "Text" in result


def test_html_to_markdown_fixture_clean(  ) -> None:
    result = html_to_markdown(FIXTURE_CLEAN)
    assert "# Clean Article Title" in result
    assert "## Section One" in result
    assert len(result) > 100
