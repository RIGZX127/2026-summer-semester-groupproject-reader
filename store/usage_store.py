# store/usage_store.py
"""UsageStore：LLM 调用用量记录。

llm_usage 表由 migrations v1 定义。
Phase 5.3 扩展聚合查询方法。
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class UsageRecord:
    id: int
    provider: str
    model: str
    agent_type: str
    prompt_tokens: int
    completion_tokens: int
    created_at: str


@dataclass
class UsageSummary:
    """指定时间范围内的总量汇总。"""
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int


@dataclass
class GroupedUsage:
    """按 provider / model / agent_type 分组统计。"""
    key: str
    calls: int
    prompt_tokens: int
    completion_tokens: int


@dataclass
class DailyUsage:
    """单日用量时间线。"""
    date: str
    calls: int
    prompt_tokens: int
    completion_tokens: int


class UsageStore:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def _sync_record(
        self,
        provider: str,
        model: str,
        agent_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT INTO llm_usage
                   (provider, model, agent_type, prompt_tokens, completion_tokens)
                   VALUES (?, ?, ?, ?, ?)""",
                (provider, model, agent_type, prompt_tokens, completion_tokens),
            )

    async def record(
        self,
        provider: str,
        model: str,
        agent_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._sync_record,
            provider,
            model,
            agent_type,
            prompt_tokens,
            completion_tokens,
        )

    # ── 聚合查询（Issue 5）─────────────────────────────────────────────

    @staticmethod
    def _time_clause_and_params(
        since: str | None, until: str | None
    ) -> tuple[str, list]:
        """Build WHERE clause fragments for time range filtering.

        Returns:
            (clause_sql, params) — clause_sql starts with "WHERE" or is empty.
        """
        conditions: list[str] = []
        params: list = []
        if since:
            conditions.append("created_at >= ?")
            params.append(since)
        if until:
            conditions.append("created_at <= ?")
            params.append(until)
        if conditions:
            return "WHERE " + " AND ".join(conditions), params
        return "", []

    def _sync_get_summary(
        self, since: str | None = None, until: str | None = None
    ) -> UsageSummary:
        clause, params = self._time_clause_and_params(since, until)
        row = self._conn.execute(
            f"SELECT COUNT(*), IFNULL(SUM(prompt_tokens), 0), "
            f"IFNULL(SUM(completion_tokens), 0) FROM llm_usage {clause}",  # noqa: S608
            params,
        ).fetchone()
        return UsageSummary(
            total_calls=row[0],
            total_prompt_tokens=row[1],
            total_completion_tokens=row[2],
        )

    def _sync_get_grouped(
        self, column: str, since: str | None, until: str | None
    ) -> list[GroupedUsage]:
        """Reusable grouped-query helper."""
        allowed = {"provider", "model", "agent_type"}
        if column not in allowed:
            raise ValueError(f"Invalid grouping column: {column!r}")
        clause, params = self._time_clause_and_params(since, until)
        rows = self._conn.execute(
            f"SELECT {column} AS key, COUNT(*), "
            f"IFNULL(SUM(prompt_tokens), 0), IFNULL(SUM(completion_tokens), 0) "
            f"FROM llm_usage {clause} "
            f"GROUP BY {column} ORDER BY COUNT(*) DESC",  # noqa: S608
            params,
        ).fetchall()
        return [
            GroupedUsage(key=r[0], calls=r[1], prompt_tokens=r[2], completion_tokens=r[3])
            for r in rows
        ]

    def _sync_get_by_provider(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return self._sync_get_grouped("provider", since, until)

    def _sync_get_by_model(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return self._sync_get_grouped("model", since, until)

    def _sync_get_by_agent_type(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return self._sync_get_grouped("agent_type", since, until)

    def _sync_get_daily_timeline(self, days: int = 30) -> list[DailyUsage]:
        rows = self._conn.execute(
            "SELECT DATE(created_at) AS date, COUNT(*), "
            "IFNULL(SUM(prompt_tokens), 0), IFNULL(SUM(completion_tokens), 0) "
            "FROM llm_usage "
            "WHERE created_at >= DATE('now', ? || ' days') "
            "GROUP BY date ORDER BY date",
            (f"-{days}",),
        ).fetchall()
        return [
            DailyUsage(date=r[0], calls=r[1], prompt_tokens=r[2], completion_tokens=r[3])
            for r in rows
        ]

    # ── Async wrappers ────────────────────────────────────────────────

    async def get_summary(
        self, since: str | None = None, until: str | None = None
    ) -> UsageSummary:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_summary, since, until
        )

    async def get_by_provider(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_by_provider, since, until
        )

    async def get_by_model(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_by_model, since, until
        )

    async def get_by_agent_type(
        self, since: str | None = None, until: str | None = None
    ) -> list[GroupedUsage]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_by_agent_type, since, until
        )

    async def get_daily_timeline(self, days: int = 30) -> list[DailyUsage]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._sync_get_daily_timeline, days
        )
