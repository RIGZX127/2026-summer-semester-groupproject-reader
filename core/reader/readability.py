# core/reader/readability.py
"""正文提取：对 readability-lxml 的薄封装。

同步函数，由 pipeline.py 用 run_in_executor 调用。
若提取结果纯文本字符数 < 80，cleaned_html 置为空字符串（触发 pipeline 回退逻辑）。
"""
from __future__ import annotations

from dataclasses import dataclass

_MIN_TEXT_LENGTH = 80   # 纯文本字符数低于此值视为提取失败


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
        from bs4 import BeautifulSoup  # type: ignore[import]
        from readability import Document  # type: ignore[import]

        doc = Document(html, url=url)
        cleaned = doc.summary(html_partial=False)
        title = doc.title() or ""

                # byline 只取真正的作者字段（author / byline / dc:creator）
        byline = ""
        meta = getattr(doc, "metadata", None)
        if meta and isinstance(meta, dict):
            for key in ("author", "byline", "dc:creator"):
                candidate = (meta.get(key) or "").strip()
                if candidate:
                    byline = candidate
                    break

                # 用纯文本字符数判断内容是否充足，避免 HTML 标签干扰计数
        soup = BeautifulSoup(cleaned, "lxml")
        plain_text = soup.get_text(separator=" ", strip=True)
        if len(plain_text) < _MIN_TEXT_LENGTH:
            return ExtractedContent("", title, byline)

        return ExtractedContent(cleaned_html=cleaned, title=title, byline=byline)
    except Exception:  # noqa: BLE001
        return ExtractedContent("", "", "")

