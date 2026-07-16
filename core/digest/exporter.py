# core/digest/exporter.py
"""DigestExporter：将文章导出为 Markdown 文件（Hugo 兼容）。

功能：
  - export_single(entry, dest_dir, template_name)  → 单篇导出
  - export_multi(entries, dest_dir, template_name) → 多篇合并导出
  - list_templates()                                → 可用模板列表
  - preview(entry, template_name, max_chars)        → 预览文本（截断）

模板发现顺序（先用户后内置）：
  1. ~/.mercury/templates/*.j2
  2. <repo_root>/resources/templates/*.j2

模板变量（单篇）：
  title, url, author, published_at, feed_title,
  summary, notes, tags, content_markdown, date

多篇额外变量：
  entries（列表，每项含上述字段），date（导出日期）
"""
from __future__ import annotations

import pathlib
import re
import textwrap
from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any

import jinja2


# ── 内置模板目录（相对于本文件向上两级到仓库根）─────────────────────
_BUILTIN_TEMPLATE_DIR = (
    pathlib.Path(__file__).parent.parent.parent / "resources" / "templates"
)
_USER_TEMPLATE_DIR = pathlib.Path.home() / ".mercury" / "templates"


# ── 数据契约 ──────────────────────────────────────────────────────────

@dataclass
class EntryDigest:
    """导出所需的文章数据快照，调用方填充后传入。"""
    entry_id: int
    title: str
    url: str = ""
    author: str = ""
    published_at: str = ""
    feed_title: str = ""
    summary: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    content_markdown: str = ""


# ── 导出结果 ──────────────────────────────────────────────────────────

@dataclass
class ExportResult:
    ok: bool
    path: pathlib.Path | None = None
    error: str | None = None


# ── 工具函数 ──────────────────────────────────────────────────────────

def _slugify(text: str, max_len: int = 40) -> str:
    """将标题转换为 URL 友好的 slug，用于文件名。"""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:max_len] or "untitled"


def _build_jinja_env() -> jinja2.Environment:
    """构建 Jinja2 环境，用户模板目录优先于内置模板目录。"""
    loaders: list[jinja2.BaseLoader] = []
    if _USER_TEMPLATE_DIR.exists():
        loaders.append(jinja2.FileSystemLoader(str(_USER_TEMPLATE_DIR)))
    if _BUILTIN_TEMPLATE_DIR.exists():
        loaders.append(jinja2.FileSystemLoader(str(_BUILTIN_TEMPLATE_DIR)))
    if not loaders:
        # 内置目录缺失时，退回到字符串模板引擎（最小保底）
        return jinja2.Environment(
            loader=jinja2.BaseLoader(), autoescape=False, keep_trailing_newline=True
        )
    return jinja2.Environment(
        loader=jinja2.ChoiceLoader(loaders),
        autoescape=False,
        keep_trailing_newline=True,
        undefined=jinja2.Undefined,  # 变量缺失时静默替换为空字符串
    )


def _entry_to_ctx(entry: EntryDigest) -> dict[str, Any]:
    """将 EntryDigest 转换为模板上下文字典。"""
    return {
        "title": entry.title,
        "url": entry.url,
        "author": entry.author,
        "published_at": entry.published_at or str(_date.today()),
        "feed_title": entry.feed_title,
        "summary": entry.summary,
        "notes": entry.notes,
        "tags": entry.tags,
        "content_markdown": entry.content_markdown,
        "date": str(_date.today()),
    }


# ── 主类 ──────────────────────────────────────────────────────────────

class DigestExporter:
    """Markdown 导出器。无状态，每次导出自动重新扫描模板目录。"""

    # ── 模板发现 ─────────────────────────────────────────────────────

    @staticmethod
    def list_templates() -> list[str]:
        """返回所有可用模板名称列表（含 .j2 后缀，用户目录优先）。"""
        seen: dict[str, None] = {}  # 保序去重
        for tpl_dir in (_USER_TEMPLATE_DIR, _BUILTIN_TEMPLATE_DIR):
            if tpl_dir.exists():
                for p in sorted(tpl_dir.glob("*.j2")):
                    seen.setdefault(p.name)
        return list(seen)

    # ── 预览 ─────────────────────────────────────────────────────────

    @staticmethod
    def preview(
        entry: EntryDigest,
        template_name: str = "single.md.j2",
        max_chars: int = 500,
    ) -> str:
        """渲染单篇模板并截断前 max_chars 字符，用于导出对话框实时预览。
        模板未找到时返回含错误说明的字符串，不抛出异常。
        """
        try:
            env = _build_jinja_env()
            tpl = env.get_template(template_name)
            rendered = tpl.render(**_entry_to_ctx(entry))
        except jinja2.TemplateNotFound:
            return f"[模板 {template_name!r} 未找到]"
        except Exception as exc:  # noqa: BLE001
            return f"[渲染错误：{exc}]"
        if len(rendered) <= max_chars:
            return rendered
        return textwrap.shorten(rendered, width=max_chars, placeholder="\n…（截断）")

    # ── 单篇导出 ─────────────────────────────────────────────────────

    @staticmethod
    def export_single(
        entry: EntryDigest,
        dest_dir: pathlib.Path | str,
        template_name: str = "single.md.j2",
        filename: str | None = None,
    ) -> ExportResult:
        """将单篇文章导出为 Markdown 文件。

        Args:
            entry:         文章数据快照。
            dest_dir:      输出目录，不存在时自动创建。
            template_name: 模板文件名（含 .j2 后缀）。
            filename:      自定义文件名；为 None 时自动生成 {date}_{slug}.md。

        Returns:
            ExportResult(ok=True, path=...) 或 ExportResult(ok=False, error=...)
        """
        dest_dir = pathlib.Path(dest_dir)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return ExportResult(ok=False, error=f"无法创建目录：{exc}")

        try:
            env = _build_jinja_env()
            tpl = env.get_template(template_name)
            content = tpl.render(**_entry_to_ctx(entry))
        except jinja2.TemplateNotFound:
            return ExportResult(ok=False, error=f"模板 {template_name!r} 未找到")
        except Exception as exc:  # noqa: BLE001
            return ExportResult(ok=False, error=f"渲染失败：{exc}")

        if filename is None:
            slug = _slugify(entry.title)
            today = str(_date.today())
            filename = f"{today}_{slug}.md"

        out_path = dest_dir / filename
        try:
            out_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ExportResult(ok=False, error=f"写入失败：{exc}")

        return ExportResult(ok=True, path=out_path)

    # ── 多篇导出 ─────────────────────────────────────────────────────

    @staticmethod
    def export_multi(
        entries: list[EntryDigest],
        dest_dir: pathlib.Path | str,
        template_name: str = "multi.md.j2",
        filename: str | None = None,
    ) -> ExportResult:
        """将多篇文章合并导出为单个 Markdown 文件，按 published_at 降序排列。

        Args:
            entries:       文章数据快照列表。
            dest_dir:      输出目录。
            template_name: 模板文件名。
            filename:      自定义文件名；为 None 时自动生成 {date}_digest.md。

        Returns:
            ExportResult(ok=True, path=...) 或 ExportResult(ok=False, error=...)
        """
        if not entries:
            return ExportResult(ok=False, error="没有可导出的文章")

        dest_dir = pathlib.Path(dest_dir)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return ExportResult(ok=False, error=f"无法创建目录：{exc}")

        # 按 published_at 降序排列
        sorted_entries = sorted(
            entries, key=lambda e: e.published_at or "", reverse=True
        )

        ctx = {
            "entries": [_entry_to_ctx(e) for e in sorted_entries],
            "date": str(_date.today()),
        }

        try:
            env = _build_jinja_env()
            tpl = env.get_template(template_name)
            content = tpl.render(**ctx)
        except jinja2.TemplateNotFound:
            return ExportResult(ok=False, error=f"模板 {template_name!r} 未找到")
        except Exception as exc:  # noqa: BLE001
            return ExportResult(ok=False, error=f"渲染失败：{exc}")

        if filename is None:
            today = str(_date.today())
            filename = f"{today}_digest.md"

        out_path = dest_dir / filename
        try:
            out_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ExportResult(ok=False, error=f"写入失败：{exc}")

        return ExportResult(ok=True, path=out_path)
