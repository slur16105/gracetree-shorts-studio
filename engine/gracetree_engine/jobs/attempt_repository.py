from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..storage.migrations import connect_database
from ..utils import utc_now as _utc_now


class AttemptRepository:
    def __init__(self, database_path: Any) -> None:
        self._database_path = database_path

    def create_attempt(
        self,
        *,
        attempt_id: str,
        job_id: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        """새 attempt를 생성하고 jobs.running_attempt_id를 설정한다.

        단일 활성 attempt 제약: job에 이미 running attempt가 있으면 RuntimeError를 발생시킨다.
        """
        snapshot_json = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT running_attempt_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if existing is None:
                conn.rollback()
                raise ValueError(f"job {job_id} does not exist")
            if existing["running_attempt_id"] is not None:
                conn.rollback()
                raise RuntimeError(
                    f"job {job_id} already has a running attempt: {existing['running_attempt_id']}"
                )
            conn.execute(
                """
                INSERT INTO job_attempts (id, job_id, snapshot_json, status, started_at)
                VALUES (?, ?, ?, 'running', ?)
                """,
                (attempt_id, job_id, snapshot_json, now),
            )
            conn.execute(
                "UPDATE jobs SET running_attempt_id = ?, status = 'running', updated_at = ? WHERE id = ?",
                (attempt_id, now, job_id),
            )
        return {
            "attemptId": attempt_id,
            "jobId": job_id,
            "status": "running",
            "startedAt": now,
        }

    def complete_attempt(
        self,
        *,
        attempt_id: str,
        artifact_path: str | None,
    ) -> None:
        """attempt를 completed로 전환하고 jobs.running_attempt_id를 지운다."""
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE job_attempts
                SET status = 'completed', ended_at = ?, artifact_path = ?
                WHERE id = ? AND status = 'running'
                """,
                (now, artifact_path, attempt_id),
            )
            conn.execute(
                """
                UPDATE jobs
                SET running_attempt_id = NULL, status = 'completed', updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (now, attempt_id),
            )

    def fail_attempt(
        self,
        *,
        attempt_id: str,
        error_code: str,
    ) -> None:
        """attempt를 failed로 전환하고 jobs.running_attempt_id를 지운다."""
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE job_attempts
                SET status = 'failed', ended_at = ?, error_code = ?
                WHERE id = ? AND status = 'running'
                """,
                (now, error_code, attempt_id),
            )
            conn.execute(
                """
                UPDATE jobs
                SET running_attempt_id = NULL, status = 'failed', updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (now, attempt_id),
            )

    def cancel_attempt(self, *, attempt_id: str) -> None:
        """attempt를 cancelled로 전환하고 jobs.running_attempt_id를 지운다."""
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE job_attempts
                SET status = 'cancelled', ended_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (now, attempt_id),
            )
            conn.execute(
                """
                UPDATE jobs
                SET running_attempt_id = NULL, status = 'cancelled', updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (now, attempt_id),
            )

    def get_snapshot(self, *, attempt_id: str) -> dict[str, Any] | None:
        with connect_database(self._database_path) as conn:
            row = conn.execute(
                "SELECT snapshot_json FROM job_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["snapshot_json"])
