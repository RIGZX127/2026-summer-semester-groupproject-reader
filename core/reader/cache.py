# core/reader/cache.py
"""版本化缓存检查器。

每个管线阶段维护一个版本常量。修改阶段逻辑时递增对应版本号，
已缓存的旧版本内容将自动失效并重新处理。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.content_store import ContentRow

READER_VERSION = 1
MARKDOWN_VERSION = 1
RENDER_VERSION = 1


def is_cache_valid(cached: ContentRow | None) -> bool:
    """检查缓存的管线结果是否仍然有效。

    三个版本必须全部匹配才视为有效。
    """
    if cached is None:
        return False
    return (
        cached.reader_version == READER_VERSION
        and cached.markdown_version == MARKDOWN_VERSION
        and cached.render_version == RENDER_VERSION
    )


def get_cache_versions() -> dict[str, int]:
    """返回当前所有管线版本号，供日志/调试使用。"""
    return {
        "reader_version": READER_VERSION,
        "markdown_version": MARKDOWN_VERSION,
        "render_version": RENDER_VERSION,
    }
