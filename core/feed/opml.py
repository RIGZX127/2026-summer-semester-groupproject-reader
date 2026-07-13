# core/feed/opml.py
"""OPML 导入导出：从 OPML XML 中提取 Feed URL，以及将 Feed 列表导出为 OPML。"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class FeedUrl:
    url: str
    title: str


def import_opml(xml_str: str) -> list[FeedUrl]:
    """解析 OPML XML 字符串，返回所有含 xmlUrl 属性的 outline 条目。"""
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid OPML XML: {exc}") from exc

    results: list[FeedUrl] = []

    def _walk(element: ET.Element) -> None:
        for child in element:
            xml_url = child.get("xmlUrl") or child.get("xmlurl")
            if xml_url:
                title = child.get("title") or child.get("text") or xml_url
                results.append(FeedUrl(url=xml_url, title=title))
            _walk(child)

    _walk(root)
    return results


def export_opml(feeds: list) -> str:
    """将 FeedRow 列表导出为 OPML 2.0 XML 字符串。"""
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    title_el = ET.SubElement(head, "title")
    title_el.text = "Mercury RSS Subscriptions"
    body = ET.SubElement(root, "body")
    for feed in feeds:
        ET.SubElement(body, "outline", **{
            "type": "rss",
            "text": feed.title or feed.url,
            "title": feed.title or feed.url,
            "xmlUrl": feed.url,
        })
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
