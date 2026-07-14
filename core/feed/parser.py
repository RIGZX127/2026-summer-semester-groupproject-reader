# core/feed/parser.py
"""Feed 解析器：将 RSS/Atom/JSON Feed URL 解析为 FeedData dataclass。"""
from __future__ import annotations

import asyncio
import calendar
import datetime
from dataclasses import dataclass, field

import feedparser
import httpx


class FeedParseError(Exception):
    """Feed 获取或解析失败时抛出。"""


@dataclass
class EntryData:
    guid: str
    url: str | None
    title: str
    summary: str
    author: str
    published_at: str | None


@dataclass
class FeedData:
    url: str
    title: str
    description: str
    entries: list[EntryData] = field(default_factory=list)


def _time_struct_to_iso(ts) -> str | None:
    if ts is None:
        return None
    try:
        epoch = calendar.timegm(ts)
        dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC) + datetime.timedelta(seconds=epoch)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _parse_blocking(url: str, raw_content: bytes) -> FeedData:
    parsed = feedparser.parse(raw_content)
    if parsed.get("bozo") and not parsed.get("entries"):
        exc = parsed.get("bozo_exception")
        raise FeedParseError(f"Feed parse error for {url}: {exc}")

    feed_title = parsed.feed.get("title", "") or ""
    feed_desc = parsed.feed.get("description", "") or parsed.feed.get("subtitle", "") or ""

    entries: list[EntryData] = []
    for e in parsed.entries:
        guid = e.get("id") or e.get("link")
        if not guid:
            continue
        raw_summary = ""
        if e.get("content"):
            raw_summary = e.content[0].get("value", "")
        elif e.get("summary"):
            raw_summary = e.get("summary", "")
        entries.append(EntryData(
            guid=guid,
            url=e.get("link"),
            title=e.get("title", "") or "",
            summary=raw_summary,
            author=e.get("author", "") or "",
            published_at=_time_struct_to_iso(
                e.get("published_parsed") or e.get("updated_parsed")
            ),
        ))
    return FeedData(url=url, title=feed_title, description=feed_desc, entries=entries)


async def parse_feed(url: str, timeout: float = 15.0) -> FeedData:
    """异步获取并解析 Feed URL，返回 FeedData。"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw_content = response.content
    except httpx.HTTPStatusError as exc:
        raise FeedParseError(f"HTTP {exc.response.status_code} for {url}") from exc
    except httpx.RequestError as exc:
        raise FeedParseError(f"Request failed for {url}: {exc}") from exc

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _parse_blocking, url, raw_content)
