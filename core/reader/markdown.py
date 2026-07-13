"""HTML -> Markdown 转换（markdownify 封装）。"""
from __future__ import annotations

from markdownify import markdownify as md


def html_to_markdown(html: str, heading_style: str = "ATX") -> str:
    """将清洗后的 HTML 转换为 Markdown。

    Args:
        html: 清洗后的 HTML 字符串（来自 readability 输出）。
        heading_style: 标题样式，"ATX"（# 风格）或 "SETEXT"。

    Returns:
        Markdown 字符串。
    """
    return md(
        html,
        heading_style=heading_style,
        strip=["script", "style", "iframe", "noscript"],
    )
