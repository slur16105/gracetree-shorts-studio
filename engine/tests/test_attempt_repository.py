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
