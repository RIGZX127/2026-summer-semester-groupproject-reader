# core/reader/readability.py
"""正文提取：对 readability-lxml 的薄封装。

同步函数，由 pipeline.py 用 run_in_executor 调用。
若提取结果正文字符数 < 100，cleaned_html 置为空字符串（触发 pipeline 回退逻辑）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtractedContent:
    cleaned_html: str
    title: str
    byline: str


def extract(html: str, url: str = "") -> ExtractedContent:
    """从原始 HTML 中提取正文。失败时返回全空字段而非抛异常。"""
    if not html:
        return ExtractedContent("", "", "")
    try:
        from readability import Document  # type: ignore[import]
        doc = Document(html, url=url)
        cleaned = doc.summary(html_partial=False)
        title = doc.title() or ""
        byline = ""
        # readability 部分版本在 metadata 中提供 author
        meta = getattr(doc, "metadata", None)
        if meta and isinstance(meta, dict):
            byline = meta.get("author", "") or ""
        # 内容太短视为提取失败
        text_len = len(cleaned.replace("<", " ").replace(">", " ").split())
        if text_len < 20:
            return ExtractedContent("", title, byline)
        return ExtractedContent(cleaned_html=cleaned, title=title, byline=byline)
    except Exception:  # noqa: BLE001
        return ExtractedContent("", "", "")
