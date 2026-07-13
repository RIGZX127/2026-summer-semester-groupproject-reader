# store/agent_store.py
"""AgentStore：Agent 运行状态与结果持久化。

agent_runs 表由 migrations v1 定义。
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store.db import DatabaseManager


@dataclass
class AgentRun:
    id: int
    entry_id: int
    agent_type: str
    status: str
    result_json: str | None
    error: str | None
    started_at: str | None
    finished_at: str | None


def _row_to_agent_run(row: sqlite3.Row) -> AgentRun:
    return AgentRun(
        id=row["id"],
        entry_id=row["entry_id"],
        agent_type=row["agent_type"],
        status=row["status"],
        result_json=row["result_json"],
        error=row["error"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


class AgentStore:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def _sync_create(self, entry_id: int, agent_type: str) -> AgentRun:
        with self._conn:
            self._conn.execute(
                """INSERT INTO agent_runs (entry_id, agent_type, status, started_at)
                   VALUES (?, ?, 'running', strftime('%Y-%m-%dT%H:%M:%SZ','now'))""",
                (entry_id, agent_type),
            )
        row = self._conn.execute(
            "SELECT * FROM agent_runs WHERE id = last_insert_rowid()"
        ).fetchone()
        return _row_to_agent_run(row)

    def _sync_complete(
        self, run_id: int, result: dict | None, error: str | None
    ) -> None:
        status = "error" if error else "done"
        result_json = json.dumps(result, ensure_ascii=False) if result else None
        with self._conn:
            self._conn.execute(
                """UPDATE agent_runs
                   SET status=?, result_json=?, error=?,
                       finished_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
                   WHERE id=?""",
                (status, result_json, error, run_id),
            )

    def _sync_cancel(self, run_id: int) -> None:
        with self._conn:
            self._conn.execute(
                """UPDATE agent_runs SET status='cancelled',
                   finished_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
                   WHERE id=?""",
                (run_id,),
            )

    def _sync_get(self, run_id: int) -> AgentRun | None:
        row = self._conn.execute(
            "SELECT * FROM agent_runs WHERE id = ?", (run_id,)
        ).fetchone()
        return _row_to_agent_run(row) if row else None

    def _sync_get_latest(
        self, entry_id: int, agent_type: str
    ) -> AgentRun | None:
        row = self._conn.execute(
            """SELECT * FROM agent_runs
               WHERE entry_id=? AND agent_type=?
               ORDER BY started_at DESC LIMIT 1""",
            (entry_id, agent_type),
        ).fetchone()
        return _row_to_agent_run(row) if row else None

    async def create(self, entry_id: int, agent_type: str) -> AgentRun:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_create, entry_id, agent_type
        )

    async def complete(
        self,
        run_id: int,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self._sync_complete, run_id, result, error
        )

    async def cancel(self, run_id: int) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_cancel, run_id)

    async def get(self, run_id: int) -> AgentRun | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_get, run_id)

    async def get_latest(
        self, entry_id: int, agent_type: str
    ) -> AgentRun | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_get_latest, entry_id, agent_type
        )
