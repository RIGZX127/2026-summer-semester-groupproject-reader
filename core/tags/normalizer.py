# core/tags/normalizer.py
"""标签规范化与别名解析。

职责：
  - 将用户输入或 LLM 建议的原始标签规范化为统一形式
  - 通过别名表将同义词映射到规范标签
  - Unicode 标准化（NFC）

规范化规则（按顺序）：
  1. Unicode NFC 标准化
  2. 去除首尾空白 + 折叠内部连续空白为单个空格
  3. 可选：小写（默认开启，中文跳过）
  4. 别名查表 → 规范名称

TagStore 在初始化时注入别名映射 {alias: canonical_name}。
"""

from __future__ import annotations

import re
import unicodedata

_MULTI_SPACE = re.compile(r"\s+")


class TagNormalizer:
    """标签规范化器。

    Usage:
        normalizer = TagNormalizer()
        normalizer.load_aliases({"ml": "Machine Learning", "ai": "AI"})
        assert normalizer.normalize("  machine learning  ") == "machine learning"
        assert normalizer.normalize("ml") == "machine learning"  # via alias
    """

    def __init__(self, lowercase: bool = True) -> None:
        self._lowercase = lowercase
        self._aliases: dict[str, str] = {}  # alias → canonical_normalized

    # ── Alias management ────────────────────────────────────────────────

    def load_aliases(self, mapping: dict[str, str]) -> None:
        """批量加载别名映射。

        Args:
            mapping: {alias_raw: canonical_name_raw}。
                     两端都会经过 normalize() 后再存储。
        """
        self._aliases.clear()
        for alias, canonical in mapping.items():
            normalized_alias = self._normalize_text(alias)
            normalized_canonical = self._normalize_text(canonical)
            if normalized_alias and normalized_canonical:
                self._aliases[normalized_alias] = normalized_canonical

    def add_alias(self, alias: str, canonical: str) -> None:
        """添加单个别名。"""
        na = self._normalize_text(alias)
        nc = self._normalize_text(canonical)
        if na and nc:
            self._aliases[na] = nc

    def remove_alias(self, alias: str) -> None:
        """移除别名。"""
        self._aliases.pop(self._normalize_text(alias), None)

    @property
    def alias_count(self) -> int:
        return len(self._aliases)

    # ── Normalization ───────────────────────────────────────────────────

    def normalize(self, tag: str) -> str:
        """完整的标签规范化流程。

        Args:
            tag: 原始标签字符串。

        Returns:
            规范化后的标签。空字符串表示无效标签（如纯空白）。
        """
        # Step 1: Unicode NFC
        text = unicodedata.normalize("NFC", tag)

        # Step 2: Trim + collapse whitespace
        text = _MULTI_SPACE.sub(" ", text).strip()

        if not text:
            return ""

        # Step 3: Lowercase (skip CJK characters)
        if self._lowercase:
            text = self._smart_lower(text)

        # Step 4: Alias resolution
        if text in self._aliases:
            text = self._aliases[text]

        return text

    def normalize_many(self, tags: list[str]) -> list[str]:
        """批量规范化并去重（保留首次出现顺序）。"""
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            n = self.normalize(tag)
            if n and n not in seen:
                seen.add(n)
                result.append(n)
        return result

    # ── Internal helpers ────────────────────────────────────────────────

    def _normalize_text(self, text: str) -> str:
        """仅做文本层面的规范化（不查别名），用于别名表键值。"""
        text = unicodedata.normalize("NFC", text)
        text = _MULTI_SPACE.sub(" ", text).strip()
        if self._lowercase:
            text = self._smart_lower(text)
        return text

    @staticmethod
    def _smart_lower(text: str) -> str:
        """智能小写：对 ASCII 字符做 lower，CJK 字符保持原样。"""
        result: list[str] = []
        for ch in text:
            cp = ord(ch)
            # CJK Unified Ideographs + Extensions
            if (0x4E00 <= cp <= 0x9FFF
                    or 0x3400 <= cp <= 0x4DBF
                    or 0x20000 <= cp <= 0x2A6DF):
                result.append(ch)
            else:
                result.append(ch.lower())
        return "".join(result)


# ── Convenience function ─────────────────────────────────────────────────


def normalize(tag: str, lowercase: bool = True) -> str:
    """便捷函数：单次规范化（无别名解析）。"""
    normalizer = TagNormalizer(lowercase=lowercase)
    return normalizer.normalize(tag)
