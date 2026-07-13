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
