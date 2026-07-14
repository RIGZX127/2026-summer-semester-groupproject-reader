# core/reader/markdown.py
"""HTML -> Markdown 转换：对 markdownify 的薄封装。

同步函数，由 pipeline.py 用 run_in_executor 调用。
预处理步骤：用 BeautifulSoup 彻底删除噪声标签（含其文本内容），
再交给 markdownify 做结构转换。
"""
from __future__ import annotations

import re

# 需要连同内容一起删除的标签（不只是删标签本身）
_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "aside"}


def html_to_markdown(html: str) -> str:
    """将 HTML 字符串转换为 Markdown。空输入直接返回空字符串。"""
    if not html:
        return ""
    try:
        import markdownify  # type: ignore[import]
        from bs4 import BeautifulSoup  # type: ignore[import]

        # 1. 过滤 data: URI 图片（base64 内嵌图，避免巨量字符）
        html = re.sub(r'<img[^>]+src=["\']data:[^"\']*["\'][^>]*/?>', "", html)

        # 2. 用 BeautifulSoup 彻底删除噪声标签（含文本内容）
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(_REMOVE_TAGS):
            tag.decompose()   # decompose() 删除标签及其全部子节点
        clean_html = str(soup)

        # 3. markdownify 结构转换
        result = markdownify.markdownify(
            clean_html,
            heading_style="ATX",
            bullets="-",
            autolinks=True,
        )

        # 4. 压缩连续空行
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()
    except Exception:  # noqa: BLE001
        return ""
