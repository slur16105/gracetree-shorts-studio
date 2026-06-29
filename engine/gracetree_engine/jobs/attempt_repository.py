from __future__ import annotations

import json
import os
from pathlib import Path
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
        is_regeneration: bool = False,
    ) -> dict[str, Any]:
        """새 attempt를 생성하고 jobs.running_attempt_id를 설정한다.

        단일 활성 attempt 제약: job에 이미 running attempt가 있으면 RuntimeError를 발생시킨다.
        is_regeneration=True는 job.status='completed'일 때만 허용된다.
        일반 생성(is_regeneration=False)은 job.status='completed'이면 거부된다.
        """
        snapshot_json = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)
        now = _utc_now()
        # 스크립트 [제목] 섹션을 한 줄로 정규화해 job 제목으로 보존한다(파서 oneLiner와 동일).
        # 제목이 없으면 None으로 두고 COALESCE로 기존 제목을 덮어쓰지 않는다.
        script_title: str | None = None
        script_ast = snapshot.get("scriptAst")
        if isinstance(script_ast, dict):
            raw_title = script_ast.get("title")
            if raw_title:
                script_title = " ".join(str(raw_title).split()) or None
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT running_attempt_id, status FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if existing is None:
                conn.rollback()
                raise ValueError(f"job {job_id} does not exist")
            if existing["running_attempt_id"] is not None:
                conn.rollback()
                raise RuntimeError(
                    f"job {job_id} already has a running attempt: {existing['running_attempt_id']}"
                )
            job_status = existing["status"]
            if is_regeneration and job_status != "completed":
                conn.rollback()
                raise ValueError(
                    f"job {job_id} is not completed (status={job_status}); regeneration requires completed job"
                )
            if not is_regeneration and job_status == "completed":
                conn.rollback()
                raise ValueError(
                    f"job {job_id} is already completed; use regeneration to re-run"
                )
            conn.execute(
                """
                INSERT INTO job_attempts (id, job_id, snapshot_json, status, started_at, is_regeneration)
                VALUES (?, ?, ?, 'running', ?, ?)
                """,
                (attempt_id, job_id, snapshot_json, now, 1 if is_regeneration else 0),
            )
            conn.execute(
                "UPDATE jobs SET running_attempt_id = ?, status = 'running', "
                "title = COALESCE(?, title), updated_at = ? WHERE id = ?",
                (attempt_id, script_title, now, job_id),
            )
        return {
            "attemptId": attempt_id,
            "jobId": job_id,
            "status": "running",
            "startedAt": now,
        }

    def mark_artifact_commit_pending(self, *, job_id: str, artifact_path: str) -> None:
        """파일 이동 전 crash 복구용 마커를 DB에 커밋한다."""
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE jobs SET pending_artifact_path = ?, updated_at = ? WHERE id = ?",
                (artifact_path, now, job_id),
            )

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
                SET running_attempt_id = NULL, status = 'completed',
                    pending_artifact_path = NULL, completed_at = ?, updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (now, now, attempt_id),
            )

    def fail_attempt(
        self,
        *,
        attempt_id: str,
        error_code: str,
        error_stage_id: str | None = None,
        log_path: str | None = None,
    ) -> None:
        """attempt를 failed로 전환하고 jobs.running_attempt_id를 지운다.

        재생성 attempt가 실패하면 job status를 completed로 복원한다.
        """
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT is_regeneration FROM job_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            is_regen = bool(row and row["is_regeneration"])
            conn.execute(
                """
                UPDATE job_attempts
                SET status = 'failed', ended_at = ?, error_code = ?, error_stage_id = ?, log_path = ?
                WHERE id = ? AND status = 'running'
                """,
                (now, error_code, error_stage_id, log_path, attempt_id),
            )
            new_job_status = "completed" if is_regen else "failed"
            conn.execute(
                """
                UPDATE jobs
                SET running_attempt_id = NULL, status = ?,
                    pending_artifact_path = NULL, updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (new_job_status, now, attempt_id),
            )

    def cancel_attempt(self, *, attempt_id: str) -> None:
        """attempt를 cancelled로 전환하고 jobs.running_attempt_id를 지운다.

        재생성 attempt가 취소되면 job status를 completed로 복원한다.
        """
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT is_regeneration FROM job_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            is_regen = bool(row and row["is_regeneration"])
            conn.execute(
                """
                UPDATE job_attempts
                SET status = 'cancelled', ended_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (now, attempt_id),
            )
            new_job_status = "completed" if is_regen else "cancelled"
            conn.execute(
                """
                UPDATE jobs
                SET running_attempt_id = NULL, status = ?,
                    pending_artifact_path = NULL, updated_at = ?
                WHERE running_attempt_id = ?
                """,
                (new_job_status, now, attempt_id),
            )

    def interrupt_running_attempts(self) -> int:
        """startup reconciliation: running 상태 attempt를 interrupted로 전환한다.

        재생성 attempt가 중단된 경우 job status를 completed로 복원한다.
        반환값: 전환된 attempt 수.
        """
        now = _utc_now()
        # read without write lock first to avoid unnecessary BEGIN IMMEDIATE on no-op startup
        with connect_database(self._database_path) as conn:
            running = conn.execute(
                "SELECT id, job_id, is_regeneration FROM job_attempts WHERE status = 'running'"
            ).fetchall()
        if not running:
            return 0
        with connect_database(self._database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for row in running:
                conn.execute(
                    "UPDATE job_attempts SET status = 'interrupted', ended_at = ? WHERE id = ?",
                    (now, row["id"]),
                )
                new_job_status = "completed" if row["is_regeneration"] else "interrupted"
                conn.execute(
                    """
                    UPDATE jobs
                    SET running_attempt_id = NULL, status = ?,
                        pending_artifact_path = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_job_status, now, row["job_id"]),
                )
            # 고아 job 안전망: job_attempts에 running 행이 없지만 jobs.running_attempt_id가 남은 경우
            conn.execute(
                "UPDATE jobs SET running_attempt_id = NULL, status = 'interrupted', updated_at = ? WHERE running_attempt_id IS NOT NULL",
                (now,),
            )
        return len(running)

    def reconcile_pending_artifacts(self) -> None:
        """startup reconciliation: pending_artifact_path 마커가 있는 job의 artifact commit을 완료한다.

        crash로 인해 파일 이동과 DB 업데이트 사이에 중단된 경우를 복구한다.
        - staging 파일이 존재하면 output으로 이동한다.
        - running attempt를 completed로 전환한다.
        """
        now = _utc_now()
        with connect_database(self._database_path) as conn:
            pending = conn.execute(
                "SELECT id, work_path, pending_artifact_path FROM jobs WHERE pending_artifact_path IS NOT NULL"
            ).fetchall()

        for job_row in pending:
            job_id = job_row["id"]
            work_path = Path(job_row["work_path"])
            staging_path = Path(job_row["pending_artifact_path"])
            output_dir = work_path / "output"
            output_path = output_dir / staging_path.name

            if staging_path.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
                os.replace(str(staging_path), str(output_path))
            elif not output_path.exists():
                # staging 파일도 output 파일도 없음 → commit 이전에 crash
                # 기존 output을 복원할 수 없으므로 interrupted로 처리
                with connect_database(self._database_path) as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        "UPDATE job_attempts SET status = 'interrupted', ended_at = ? WHERE job_id = ? AND status = 'running'",
                        (now, job_id),
                    )
                    conn.execute(
                        "UPDATE jobs SET running_attempt_id = NULL, status = 'interrupted', pending_artifact_path = NULL, updated_at = ? WHERE id = ?",
                        (now, job_id),
                    )
                continue

            with connect_database(self._database_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                attempt_row = conn.execute(
                    "SELECT id FROM job_attempts WHERE job_id = ? AND status = 'running'",
                    (job_id,),
                ).fetchone()
                if attempt_row:
                    attempt_id = attempt_row["id"]
                    conn.execute(
                        "UPDATE job_attempts SET status = 'completed', ended_at = ?, artifact_path = ? WHERE id = ?",
                        (now, str(output_path), attempt_id),
                    )
                conn.execute(
                    """
                    UPDATE jobs
                    SET running_attempt_id = NULL, status = 'completed',
                        pending_artifact_path = NULL, completed_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, job_id),
                )

    def get_snapshot(self, *, attempt_id: str) -> dict[str, Any] | None:
        with connect_database(self._database_path) as conn:
            row = conn.execute(
                "SELECT snapshot_json FROM job_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["snapshot_json"])
