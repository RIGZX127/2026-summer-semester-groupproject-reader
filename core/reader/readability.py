"""Readability 正文提取封装。

对 readability-lxml 的 Document 做薄封装，仅返回清洗后的 HTML、标题和作者。
"""
from __future__ import annotations

from bs4 import BeautifulSoup
from readability import Document


class ReadabilityError(Exception):
    """正文提取失败时抛出。"""


def _extract_byline_from_meta(html: str) -> str:
    """用 BeautifulSoup 从 HTML meta 标签中提取作者信息。

    依次检查: author, article:author, byline, dc.creator。
    """
    soup = BeautifulSoup(html, "lxml")
    # 有 name 属性的 meta
    for name_attr in ("author", "byline", "dc.creator"):
        tag = soup.find("meta", attrs={"name": name_attr})
        if tag and tag.get("content"):
            return tag["content"].strip()

    # 有 property 属性的 meta (og / article)
    for prop_attr in ("article:author", "og:author"):
        tag = soup.find("meta", attrs={"property": prop_attr})
        if tag and tag.get("content"):
            return tag["content"].strip()

    # Twitter Card
    tag = soup.find("meta", attrs={"name": "twitter:creator"})
    if tag and tag.get("content"):
        return tag["content"].strip()

    return ""


def extract_content(html: str, url: str = "") -> tuple[str, str, str]:
    """从 HTML 中提取正文内容。

    Args:
        html: 原始 HTML 字符串。
        url: 文章 URL（用于相对路径解析）。

    Returns:
        (cleaned_html, title, byline) 三元组。

    Raises:
        ReadabilityError: 提取失败或结果为空。
    """
    try:
        doc = Document(html, url=url)
        cleaned_html = doc.summary()
        title = doc.title() or ""
    except Exception as exc:
        raise ReadabilityError(
            f"readability-lxml extraction failed: {exc}"
        ) from exc

    if not cleaned_html:
        raise ReadabilityError(
            "Extracted content is empty"
        )

    # 测量纯文本长度而非 HTML 标记长度
    text = BeautifulSoup(cleaned_html, "lxml").get_text().strip()
    if len(text) < 50:
        raise ReadabilityError(
            "Extracted content is empty or too short (< 50 chars)"
        )

    # 优先使用 readability 自带的 author 方法
    byline = ""
    try:
        raw_author = (doc.author() or "").strip()
        # readability 返回 '[no-author]' 表示未找到作者
        if raw_author and raw_author != "[no-author]":
            byline = raw_author
    except Exception:
        pass

    # 如果 readability 没有提取到作者，回退到 BeautifulSoup 解析 meta 标签
    if not byline:
        try:
            byline = _extract_byline_from_meta(html)
        except Exception:
            pass

    return (cleaned_html, title, byline)
