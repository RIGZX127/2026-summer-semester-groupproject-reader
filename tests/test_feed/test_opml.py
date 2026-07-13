# tests/test_feed/test_opml.py
"""OPML 导入导出测试。"""
from __future__ import annotations

import pathlib

import pytest

from core.feed.opml import FeedUrl, export_opml, import_opml

FIXTURE_DIR = pathlib.Path(__file__).parent
FIXTURE_OPML = (FIXTURE_DIR / "fixture_opml.xml").read_text(encoding="utf-8")


def test_import_opml_returns_all_feeds() -> None:
    feeds = import_opml(FIXTURE_OPML)
    assert len(feeds) == 3


def test_import_opml_extracts_urls() -> None:
    feeds = import_opml(FIXTURE_OPML)
    urls = [f.url for f in feeds]
    assert "https://news.ycombinator.com/rss" in urls
    assert "https://blog.python.org/feeds/posts/default" in urls
    assert "https://feeds.bbci.co.uk/news/rss.xml" in urls


def test_import_opml_extracts_titles() -> None:
    feeds = import_opml(FIXTURE_OPML)
    titles = [f.title for f in feeds]
    assert "Hacker News" in titles


def test_import_opml_invalid_xml_raises_valueerror() -> None:
    with pytest.raises(ValueError, match="Invalid OPML"):
        import_opml("this is not xml <<>>")


def test_export_opml_roundtrip() -> None:
    from dataclasses import dataclass

    @dataclass
    class FakeRow:
        url: str
        title: str

    original = [FakeRow("https://a.com/rss", "Feed A"), FakeRow("https://b.com/atom", "Feed B")]
    xml_str = export_opml(original)
    restored = import_opml(xml_str)
    assert len(restored) == 2
    assert restored[0].url == "https://a.com/rss"
    assert restored[1].url == "https://b.com/atom"
    assert restored[0].title == "Feed A"


def test_export_opml_contains_opml_tag() -> None:
    xml_str = export_opml([])
    assert "<opml" in xml_str
    assert 'version="2.0"' in xml_str
