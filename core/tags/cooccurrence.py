# core/tags/cooccurrence.py
"""标签共现推荐引擎。

基于 Jaccard 相似度：对每对标签，计算它们共同出现的文章数
与各自出现文章数的比率，推荐语义相关的标签。

算法：
  Jaccard(tag_a, tag_b) = |articles(tag_a) ∩ articles(tag_b)| /
                            |articles(tag_a) ∪ articles(tag_b)|

结果缓存 5 分钟以避免频繁全表扫描。
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class TagCooccurrence:
    tag_id: int
    tag_name: str
    score: float  # Jaccard similarity, 0.0–1.0
    shared_entries: int  # co-occurring article count


class CooccurrenceEngine:
    """标签共现推荐引擎。

    Usage:
        engine = CooccurrenceEngine(db)
        related = await engine.recommend(tag_id=1, limit=5)
        # → [TagCooccurrence(tag_id=3, tag_name="Python", score=0.42), ...]
    """

    _CACHE_TTL = 300.0  # 5 minutes

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._cache: dict[int, list[TagCooccurrence]] = {}
        self._cache_time: dict[int, float] = {}

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    async def recommend(
        self, tag_id: int, limit: int = 5, min_score: float = 0.05
    ) -> list[TagCooccurrence]:
        """为指定标签推荐共现标签。

        Args:
            tag_id: 源标签 ID。
            limit: 返回的最大推荐数。
            min_score: 最小 Jaccard 分数阈值。

        Returns:
            按 score 降序排列的共现标签列表。
        """
        # Check cache
        now = time.monotonic()
        if tag_id in self._cache:
            elapsed = now - self._cache_time.get(tag_id, 0)
            if elapsed < self._CACHE_TTL:
                return self._cache[tag_id][:limit]

        result = await asyncio.get_running_loop().run_in_executor(
            None, self._sync_compute, tag_id
        )

        # Filter + sort
        filtered = [r for r in result if r.score >= min_score]
        filtered.sort(key=lambda r: r.score, reverse=True)
        self._cache[tag_id] = filtered
        self._cache_time[tag_id] = now
        return filtered[:limit]

    def _sync_compute(self, tag_id: int) -> list[TagCooccurrence]:
        """同步计算 Jaccard 分数。"""
        # Get article set for target tag
        source_articles = self._article_set(tag_id)
        if not source_articles:
            return []

        source_count = len(source_articles)
        results: list[TagCooccurrence] = []

        # Get all other tags that appear on any of the same articles
        placeholders = ",".join("?" for _ in source_articles)
        rows = self._conn.execute(
            f"""SELECT t.id, t.name, et.entry_id
                FROM entry_tags et
                JOIN tags t ON et.tag_id = t.id
                WHERE et.entry_id IN ({placeholders})
                  AND et.tag_id != ?""",
            (*source_articles, tag_id),
        ).fetchall()

        # Group by tag_id
        tag_articles: dict[int, set[int]] = {}
        for row in rows:
            tid = row[0]
            eid = row[2]
            if tid not in tag_articles:
                tag_articles[tid] = set()
            tag_articles[tid].add(eid)

        # Compute Jaccard for each candidate
        for tid, articles in tag_articles.items():
            tag_name = ""
            for row in rows:
                if row[0] == tid:
                    tag_name = row[1]
                    break

            intersection = len(source_articles & articles)
            total_count = self._tag_article_count(tid)
            union = source_count + total_count - intersection

            if union > 0:
                score = intersection / union
                results.append(
                    TagCooccurrence(
                        tag_id=tid,
                        tag_name=tag_name,
                        score=round(score, 4),
                        shared_entries=intersection,
                    )
                )

        return results

    def _article_set(self, tag_id: int) -> set[int]:
        rows = self._conn.execute(
            "SELECT entry_id FROM entry_tags WHERE tag_id = ?", (tag_id,)
        ).fetchall()
        return {r[0] for r in rows}

    def _tag_article_count(self, tag_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM entry_tags WHERE tag_id = ?", (tag_id,)
        ).fetchone()
        return row[0] if row else 0

    def invalidate_cache(self, tag_id: int | None = None) -> None:
        """清除缓存。不传 tag_id 则清除全部。"""
        if tag_id is None:
            self._cache.clear()
            self._cache_time.clear()
        else:
            self._cache.pop(tag_id, None)
            self._cache_time.pop(tag_id, None)
