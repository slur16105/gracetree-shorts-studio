from __future__ import annotations

from pathlib import Path

import pytest

from gracetree_engine.storage.migrations import apply_migrations, connect_database
from gracetree_engine.jobs.attempt_repository import AttemptRepository

JOB_ID = "11111111-1111-4111-8111-111111111111"
ATTEMPT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ATTEMPT_ID_2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _setup_db(tmp_path: Path) -> Path:
    db = tmp_path / "studio.db"
    apply_migrations(db)
    with connect_database(db) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, publish_date, status, title, work_path, result_path, created_at, updated_at)
            VALUES (?, '2026-06-25', 'draft', NULL, ?, ?, ?, ?)
            """,
            (
                JOB_ID,
                str(tmp_path / "jobs" / "2026-06-25"),
                str(tmp_path / "jobs" / "2026-06-25" / "output"),
                "2026-06-25T00:00:00.000Z",
                "2026-06-25T00:00:00.000Z",
            ),
        )
    return db


def test_create_attempt_sets_running_and_links_job(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)

    result = repo.create_attempt(
        attempt_id=ATTEMPT_ID,
        job_id=JOB_ID,
        snapshot={"inputs": [{"role": "voice", "path": "/managed/voice.mp3"}]},
    )

    assert result["attemptId"] == ATTEMPT_ID
    assert result["status"] == "running"

    with connect_database(db) as conn:
        attempt = conn.execute("SELECT * FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)).fetchone()
        job = conn.execute("SELECT status, running_attempt_id FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()

    assert attempt["status"] == "running"
    assert attempt["job_id"] == JOB_ID
    assert attempt["ended_at"] is None
    assert job["status"] == "running"
    assert job["running_attempt_id"] == ATTEMPT_ID


def test_create_attempt_blocks_second_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)

    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    with pytest.raises(RuntimeError, match="already has a running attempt"):
        repo.create_attempt(attempt_id=ATTEMPT_ID_2, job_id=JOB_ID, snapshot={"inputs": []})


def test_create_attempt_rejects_unknown_job(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)

    with pytest.raises(ValueError, match="does not exist"):
        repo.create_attempt(
            attempt_id=ATTEMPT_ID,
            job_id="99999999-9999-4999-8999-999999999999",
            snapshot={"inputs": []},
        )


def test_complete_attempt_clears_running_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    artifact = str(tmp_path / "jobs" / "2026-06-25" / "temp" / "attempts" / ATTEMPT_ID / "vertical-slice.mp4")
    repo.complete_attempt(attempt_id=ATTEMPT_ID, artifact_path=artifact)

    with connect_database(db) as conn:
        attempt = conn.execute("SELECT status, artifact_path FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)).fetchone()
        job = conn.execute("SELECT status, running_attempt_id FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()

    assert attempt["status"] == "completed"
    assert attempt["artifact_path"] == artifact
    assert job["status"] == "completed"
    assert job["running_attempt_id"] is None


def test_fail_attempt_clears_running_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    repo.fail_attempt(attempt_id=ATTEMPT_ID, error_code="PROCESS_FAILED")

    with connect_database(db) as conn:
        attempt = conn.execute("SELECT status, error_code FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)).fetchone()
        job = conn.execute("SELECT status, running_attempt_id FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()

    assert attempt["status"] == "failed"
    assert attempt["error_code"] == "PROCESS_FAILED"
    assert job["status"] == "failed"
    assert job["running_attempt_id"] is None


def test_cancel_attempt_clears_running_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    repo.cancel_attempt(attempt_id=ATTEMPT_ID)

    with connect_database(db) as conn:
        attempt = conn.execute("SELECT status FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)).fetchone()
        job = conn.execute("SELECT status, running_attempt_id FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()

    assert attempt["status"] == "cancelled"
    assert job["status"] == "cancelled"
    assert job["running_attempt_id"] is None


def test_after_failed_attempt_can_create_new_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    repo.fail_attempt(attempt_id=ATTEMPT_ID, error_code="PROCESS_FAILED")

    result = repo.create_attempt(attempt_id=ATTEMPT_ID_2, job_id=JOB_ID, snapshot={"inputs": []})
    assert result["attemptId"] == ATTEMPT_ID_2


def test_get_snapshot_returns_stored_snapshot(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    snapshot = {"inputs": [{"role": "voice", "path": "/managed/voice.mp3"}], "resources": {}}
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot=snapshot)

    recovered = repo.get_snapshot(attempt_id=ATTEMPT_ID)
    assert recovered == snapshot


def test_get_snapshot_returns_none_for_unknown_attempt(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    assert repo.get_snapshot(attempt_id=ATTEMPT_ID) is None


def test_fail_attempt_stores_error_stage_id_and_log_path(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    repo.fail_attempt(
        attempt_id=ATTEMPT_ID,
        error_code="PRAYER_BOUNDARY_AMBIGUOUS",
        error_stage_id="speech_alignment",
        log_path="/managed/logs/test-render_log.txt",
    )

    with connect_database(db) as conn:
        attempt = conn.execute(
            "SELECT status, error_code, error_stage_id, log_path FROM job_attempts WHERE id = ?",
            (ATTEMPT_ID,),
        ).fetchone()

    assert attempt["status"] == "failed"
    assert attempt["error_code"] == "PRAYER_BOUNDARY_AMBIGUOUS"
    assert attempt["error_stage_id"] == "speech_alignment"
    assert attempt["log_path"] == "/managed/logs/test-render_log.txt"


def test_interrupt_running_attempts_sets_interrupted_status(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    count = repo.interrupt_running_attempts()

    assert count == 1
    with connect_database(db) as conn:
        attempt = conn.execute(
            "SELECT status FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)
        ).fetchone()
        job = conn.execute(
            "SELECT status, running_attempt_id FROM jobs WHERE id = ?", (JOB_ID,)
        ).fetchone()

    assert attempt["status"] == "interrupted"
    assert job["status"] == "interrupted"
    assert job["running_attempt_id"] is None


def test_interrupt_running_attempts_is_idempotent(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    repo.interrupt_running_attempts()

    count = repo.interrupt_running_attempts()
    assert count == 0


def test_interrupt_running_attempts_skips_completed(tmp_path: Path) -> None:
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    repo.complete_attempt(attempt_id=ATTEMPT_ID, artifact_path="/output/out.mp4")

    count = repo.interrupt_running_attempts()
    assert count == 0

    with connect_database(db) as conn:
        attempt = conn.execute(
            "SELECT status FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)
        ).fetchone()
    assert attempt["status"] == "completed"


# ──────────────── Story 3.3: 재생성 지원 ────────────────


def _setup_db_completed(tmp_path: Path) -> Path:
    """완료 상태의 job이 있는 DB를 설정한다."""
    db = tmp_path / "studio.db"
    apply_migrations(db)
    with connect_database(db) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, publish_date, status, title, work_path, result_path, created_at, updated_at)
            VALUES (?, '2026-06-25', 'completed', 'Test Title', ?, ?, ?, ?)
            """,
            (
                JOB_ID,
                str(tmp_path / "jobs" / "2026-06-25"),
                str(tmp_path / "jobs" / "2026-06-25" / "output"),
                "2026-06-25T00:00:00.000Z",
                "2026-06-25T12:00:00.000Z",
            ),
        )
    return db


def test_create_attempt_rejects_normal_start_when_job_completed(tmp_path: Path) -> None:
    """AC 6: 완료된 job에 일반 생성 요청을 거부한다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)

    with pytest.raises(ValueError, match="already completed"):
        repo.create_attempt(
            attempt_id=ATTEMPT_ID,
            job_id=JOB_ID,
            snapshot={"inputs": []},
            is_regeneration=False,
        )


def test_create_attempt_allows_regeneration_when_job_completed(tmp_path: Path) -> None:
    """AC 3: 완료된 job에 재생성 attempt를 허용한다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)

    result = repo.create_attempt(
        attempt_id=ATTEMPT_ID,
        job_id=JOB_ID,
        snapshot={"inputs": []},
        is_regeneration=True,
    )
    assert result["attemptId"] == ATTEMPT_ID
    assert result["status"] == "running"

    with connect_database(db) as conn:
        attempt = conn.execute(
            "SELECT is_regeneration FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)
        ).fetchone()
    assert attempt["is_regeneration"] == 1


def test_create_attempt_rejects_regeneration_when_job_not_completed(tmp_path: Path) -> None:
    """AC 6: 완료되지 않은 job에 재생성을 거부한다."""
    db = _setup_db(tmp_path)  # draft status
    repo = AttemptRepository(db)

    with pytest.raises(ValueError, match="not completed"):
        repo.create_attempt(
            attempt_id=ATTEMPT_ID,
            job_id=JOB_ID,
            snapshot={"inputs": []},
            is_regeneration=True,
        )


def test_mark_artifact_commit_pending_sets_db_marker(tmp_path: Path) -> None:
    """AC 4: commit 전 crash 복구용 마커를 DB에 기록한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    staging = str(tmp_path / "jobs" / "2026-06-25" / "temp" / "attempts" / ATTEMPT_ID / "vertical-slice.mp4")
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path=staging)

    with connect_database(db) as conn:
        job = conn.execute("SELECT pending_artifact_path FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["pending_artifact_path"] == staging


def test_complete_attempt_clears_pending_artifact_path(tmp_path: Path) -> None:
    """AC 4: complete_attempt가 pending_artifact_path 마커를 초기화한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path="/staging/out.mp4")

    output = str(tmp_path / "jobs" / "2026-06-25" / "output" / "vertical-slice.mp4")
    repo.complete_attempt(attempt_id=ATTEMPT_ID, artifact_path=output)

    with connect_database(db) as conn:
        job = conn.execute("SELECT pending_artifact_path, status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["pending_artifact_path"] is None
    assert job["status"] == "completed"


def test_fail_regen_attempt_restores_completed_status(tmp_path: Path) -> None:
    """AC 5: 재생성 실패 시 job status를 completed로 복원한다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )

    repo.fail_attempt(attempt_id=ATTEMPT_ID, error_code="PROCESS_FAILED")

    with connect_database(db) as conn:
        job = conn.execute("SELECT status, pending_artifact_path FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "completed"
    assert job["pending_artifact_path"] is None


def test_cancel_regen_attempt_restores_completed_status(tmp_path: Path) -> None:
    """AC 5: 재생성 취소 시 job status를 completed로 복원한다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )

    repo.cancel_attempt(attempt_id=ATTEMPT_ID)

    with connect_database(db) as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "completed"


def test_interrupt_regen_attempt_restores_completed_status(tmp_path: Path) -> None:
    """AC 5: 재생성 중 interrupt 시 job status를 completed로 복원한다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )

    count = repo.interrupt_running_attempts()

    assert count == 1
    with connect_database(db) as conn:
        job = conn.execute("SELECT status, pending_artifact_path FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "completed"
    assert job["pending_artifact_path"] is None


def test_reconcile_pending_artifact_completes_when_file_missing(tmp_path: Path) -> None:
    """AC 5: crash 후 파일이 이미 이동되었으면 DB만 업데이트한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    # Simulate crash between file-move and DB update: pending_artifact_path set but file gone
    staging = str(tmp_path / "staging" / "out.mp4")
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path=staging)
    # staging file does NOT exist (simulate: already renamed to output before crash)
    output_path = str(tmp_path / "jobs" / "2026-06-25" / "output" / "out.mp4")

    repo.reconcile_pending_artifacts()

    with connect_database(db) as conn:
        job = conn.execute("SELECT status, pending_artifact_path FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
        attempt = conn.execute("SELECT status FROM job_attempts WHERE id = ?", (ATTEMPT_ID,)).fetchone()
    assert job["pending_artifact_path"] is None
    assert job["status"] == "completed"
    assert attempt["status"] == "completed"


def test_reconcile_pending_artifact_moves_file_when_exists(tmp_path: Path) -> None:
    """AC 5: crash 후 staging 파일이 남아 있으면 output으로 이동한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})
    # Create staging file (crash happened before file move)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    staging = staging_dir / "vertical-slice.mp4"
    staging.write_bytes(b"mp4data")
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path=str(staging))

    work_path = tmp_path / "jobs" / "2026-06-25"
    (work_path / "output").mkdir(parents=True, exist_ok=True)
    repo.reconcile_pending_artifacts()

    assert not staging.exists(), "staging file must be moved"
    assert (work_path / "output" / "vertical-slice.mp4").exists(), "output file must exist"
    with connect_database(db) as conn:
        job = conn.execute("SELECT status, pending_artifact_path FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["pending_artifact_path"] is None
    assert job["status"] == "completed"


# ──────────────── Task 6: fault injection 테스트 ────────────────


def test_duplicate_normal_start_rejected_when_already_running(tmp_path: Path) -> None:
    """AC 6: 이미 running인 job에 두 번째 일반 생성 요청은 RuntimeError로 거부된다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    with pytest.raises(RuntimeError, match="already has a running attempt"):
        repo.create_attempt(attempt_id=ATTEMPT_ID_2, job_id=JOB_ID, snapshot={"inputs": []})


def test_concurrent_regeneration_rejected_when_already_running(tmp_path: Path) -> None:
    """AC 6: 재생성 중 두 번째 재생성 요청은 RuntimeError로 거부된다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )

    with pytest.raises(RuntimeError, match="already has a running attempt"):
        repo.create_attempt(
            attempt_id=ATTEMPT_ID_2, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
        )


def test_fail_regen_clears_pending_artifact_path(tmp_path: Path) -> None:
    """AC 5: 재생성 실패 시 pending_artifact_path 마커도 초기화된다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path="/staging/out.mp4")

    repo.fail_attempt(attempt_id=ATTEMPT_ID, error_code="PROCESS_FAILED")

    with connect_database(db) as conn:
        job = conn.execute("SELECT pending_artifact_path, status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["pending_artifact_path"] is None
    assert job["status"] == "completed"


def test_interrupt_regen_clears_pending_artifact_path(tmp_path: Path) -> None:
    """AC 5: 재생성 중 interrupt 시 pending_artifact_path 마커도 초기화된다."""
    db = _setup_db_completed(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(
        attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []}, is_regeneration=True
    )
    repo.mark_artifact_commit_pending(job_id=JOB_ID, artifact_path="/staging/out.mp4")

    repo.interrupt_running_attempts()

    with connect_database(db) as conn:
        job = conn.execute("SELECT pending_artifact_path, status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["pending_artifact_path"] is None
    assert job["status"] == "completed"


def test_normal_fail_does_not_restore_completed(tmp_path: Path) -> None:
    """AC 5: 일반(비재생성) 실패 시 job status는 failed가 되어야 한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    repo.fail_attempt(attempt_id=ATTEMPT_ID, error_code="PROCESS_FAILED")

    with connect_database(db) as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "failed"


def test_normal_cancel_does_not_restore_completed(tmp_path: Path) -> None:
    """AC 5: 일반(비재생성) 취소 시 job status는 cancelled가 되어야 한다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)
    repo.create_attempt(attempt_id=ATTEMPT_ID, job_id=JOB_ID, snapshot={"inputs": []})

    repo.cancel_attempt(attempt_id=ATTEMPT_ID)

    with connect_database(db) as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "cancelled"


def test_reconcile_no_pending_is_noop(tmp_path: Path) -> None:
    """AC 5: pending_artifact_path가 없으면 reconcile은 아무것도 변경하지 않는다."""
    db = _setup_db(tmp_path)
    repo = AttemptRepository(db)

    repo.reconcile_pending_artifacts()

    with connect_database(db) as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id = ?", (JOB_ID,)).fetchone()
    assert job["status"] == "draft"
