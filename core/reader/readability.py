# core/reader/readability.py
"""正文提取：对 readability-lxml 的薄封装 + HTML 后处理清洗。

同步函数，由 pipeline.py 用 run_in_executor 调用。
若提取结果纯文本字符数 < 80，cleaned_html 置为空字符串（触发 pipeline 回退逻辑）。

清洗原理（三层，由安全到激进）：
  L1 — 语义标签：移除 <footer>, <nav>, <aside> 及 ARIA 非正文 role。
  L2 — CSS 启发式：移除 class/id 包含非正文关键词的元素。
  L3 — 链接密度：移除链接文字占比 > 60% 的容器（如"往年回顾"链接列表）。

注意：所有规则均为通用规则，不得硬编码特定网站逻辑。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_MIN_TEXT_LENGTH = 80   # 纯文本字符数低于此值视为提取失败

# ── 清洗规则常量 ────────────────────────────────────────────────────────────

# L1: 语义化非正文标签
# 注意：不含 <header> — 页面级 header 已被 readability 移除，
# 文章内部 <header> 常包裹标题/作者/日期等正文内容，不应删除。
_NON_CONTENT_TAGS = frozenset({"footer", "nav", "aside"})

# L1: ARIA role 非正文值
_NON_CONTENT_ROLES = frozenset({
    "navigation", "contentinfo", "complementary", "banner", "search",
})

# L2: class / id 非正文关键词（按单词边界匹配）
_NON_CONTENT_CLASS_RE = re.compile(
    r"\b(?:"
    r"footer|sidebar|side-bar|nav-menu|nav-bar|site-nav|main-nav|"
    r"side-bar|widget|related-posts?|recommended-posts?|popular-posts?|"
    r"comments?|share-buttons?|social-links?|author-bio|about-author|"
    r"newsletter|subscrib|breadcrumb|pagination|read-more|sponsored|"
    r"tag-list|category-list|site-header|site-footer|meta-info|"
    r"post-nav|entry-nav|page-nav|written-by|author-info|back-to-top"
    r")\b",
    re.IGNORECASE,
)

# L3: 链接密度阈值（链接文字/总文字 > 阈值 → 移除）
_LINK_DENSITY_THRESHOLD = 0.6

# L3: 进行链接密度检查的标签
_LINK_DENSITY_TAGS = frozenset({"ul", "ol", "div", "section", "p", "li"})


# ── 清洗函数 ────────────────────────────────────────────────────────────────

def _clean_html(html: str) -> str:
    """对 readability 提取后的 HTML 做三层后处理清洗。"""
    if not html:
        return html

    from bs4 import BeautifulSoup  # type: ignore[import]  # local import

    soup = BeautifulSoup(html, "lxml")

    # ── Layer 1: 语义标签 + ARIA role ─────────────────────────────
    for tag_name in _NON_CONTENT_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    for role in _NON_CONTENT_ROLES:
        for el in soup.find_all(attrs={"role": role}):
            el.decompose()

    # ── Layer 2: CSS class / ID 启发式 ────────────────────────────
    for el in list(soup.find_all(True)):  # True = 所有标签
        if el.name is None or el.attrs is None:
            continue

        # 逐个 class 检查，降低误伤
        css_classes = el.attrs.get("class")
        if css_classes and isinstance(css_classes, list):
            if any(_NON_CONTENT_CLASS_RE.search(cls) for cls in css_classes):
                el.decompose()
                continue

        el_id = el.attrs.get("id")
        if el_id and isinstance(el_id, str) and _NON_CONTENT_CLASS_RE.search(el_id):
            el.decompose()

    # ── Layer 3: 高链接密度 ──────────────────────────────────────
    for el in list(soup.find_all(list(_LINK_DENSITY_TAGS))):
        if el.name is None:
            continue

        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue

        text_len = len(text)
        link_text_len = sum(
            len(a.get_text(separator=" ", strip=True))
            for a in el.find_all("a")
        )

        if text_len > 0 and (link_text_len / text_len) > _LINK_DENSITY_THRESHOLD:
            el.decompose()

    return str(soup)


# ── 公开接口 ────────────────────────────────────────────────────────────────

@dataclass
class ExtractedContent:
    cleaned_html: str
    title: str
    byline: str


def extract(html: str, url: str = "") -> ExtractedContent:
    """从原始 HTML 中提取正文并清洗。失败时返回全空字段而非抛异常。"""
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

        # 三层 HTML 后处理清洗（B 代劳，A 后续可在此基础上增强）
        cleaned = _clean_html(cleaned)

        # 用纯文本字符数判断内容是否充足，避免 HTML 标签干扰计数
        soup = BeautifulSoup(cleaned, "lxml")
        plain_text = soup.get_text(separator=" ", strip=True)
        if len(plain_text) < _MIN_TEXT_LENGTH:
            return ExtractedContent("", title, byline)

        return ExtractedContent(cleaned_html=cleaned, title=title, byline=byline)
    except Exception:  # noqa: BLE001
        return ExtractedContent("", "", "")

