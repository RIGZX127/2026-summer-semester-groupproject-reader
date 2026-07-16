"""Tests for TagNormalizer."""
from __future__ import annotations

import pytest

from core.tags.normalizer import TagNormalizer, normalize


class TestNormalizeBasics:
    def test_trims_whitespace(self) -> None:
        assert normalize("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize("hello   world") == "hello world"

    def test_lowercase_ascii(self) -> None:
        assert normalize("Machine Learning") == "machine learning"

    def test_preserves_cjk(self) -> None:
        assert normalize("机器学习") == "机器学习"

    def test_empty_after_trim_is_empty(self) -> None:
        assert normalize("   ") == ""

    def test_unicode_nfc(self) -> None:
        # é can be composed (NFC) or decomposed (NFD)
        # Normalizer should produce NFC
        import unicodedata
        nfd = unicodedata.normalize("NFD", "café")
        result = normalize(nfd)
        assert result == "café"

    def test_case_sensitive_mode(self) -> None:
        n = TagNormalizer(lowercase=False)
        assert n.normalize("Machine Learning") == "Machine Learning"


class TestAliases:
    def test_alias_resolves_to_canonical(self) -> None:
        n = TagNormalizer()
        n.load_aliases({"ml": "Machine Learning", "ai": "Artificial Intelligence"})
        assert n.normalize("ml") == "machine learning"
        assert n.normalize("ML") == "machine learning"

    def test_alias_chain_not_followed(self) -> None:
        """Aliases should NOT chain — only one hop."""
        n = TagNormalizer()
        n.load_aliases({"a": "b", "b": "c"})
        # "a" → "b" (one hop only)
        assert n.normalize("a") == "b"

    def test_add_remove_alias(self) -> None:
        n = TagNormalizer()
        n.add_alias("js", "JavaScript")
        assert n.normalize("js") == "javascript"
        n.remove_alias("js")
        assert n.normalize("js") == "js"

    def test_alias_count(self) -> None:
        n = TagNormalizer()
        assert n.alias_count == 0
        n.add_alias("a", "b")
        assert n.alias_count == 1

    def test_alias_to_self_ignored(self) -> None:
        n = TagNormalizer()
        n.add_alias("  ", "test")  # empty after normalize
        assert n.alias_count == 0


class TestNormalizeMany:
    def test_dedup_preserves_order(self) -> None:
        n = TagNormalizer()
        result = n.normalize_many(["Python", "python", "AI", "ai", "Rust"])
        assert result == ["python", "ai", "rust"]

    def test_alias_applied_to_all(self) -> None:
        n = TagNormalizer()
        n.add_alias("ml", "Machine Learning")
        result = n.normalize_many(["ML", "ml", "machine learning"])
        assert result == ["machine learning"]
