from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from gracetree_engine.storage.job_repository import JobRepository, get_completed_jobs
from gracetree_engine.storage.migrations import apply_migrations, connect_database


def repository(tmp_path: Path) -> JobRepository:
    return JobRepository(tmp_path / "GraceTreeData")


def test_creates_one_job_per_publish_date_and_restores_it(tmp_path: Path) -> None:
    jobs = repository(tmp_path)

    created = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="11111111-1111-4111-8111-111111111111",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )
    restored = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="22222222-2222-4222-8222-222222222222",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )

    assert restored == created
    assert created["id"] == "11111111-1111-4111-8111-111111111111"
    assert created["publishDate"] == "2026-06-20"
    assert created["status"] == "draft"
    assert created["inputMetadata"] == []
    assert created["pathState"] == "ready"
    assert Path(created["workPath"]).name == "2026-06-20"
    assert created["id"] != Path(created["workPath"]).name
    for directory in ("input", "output", "temp", "logs"):
        assert (Path(created["workPath"]) / directory).is_dir()

    with sqlite3.connect(tmp_path / "GraceTreeData" / "studio.db") as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE publish_date = ?", ("2026-06-20",)
        ).fetchone()
    assert count == (1,)


@pytest.mark.parametrize(
    ("publish_date", "job_id"),
    [
        ("2026-02-30", "11111111-1111-4111-8111-111111111111"),
        ("2026/06/20", "11111111-1111-4111-8111-111111111111"),
        ("2026-06-20", "not-a-uuid"),
    ],
)
def test_rejects_invalid_date_or_job_id(
    tmp_path: Path, publish_date: str, job_id: str
) -> None:
    with pytest.raises(ValueError):
        repository(tmp_path).get_or_create_for_date(
            publish_date=publish_date,
            proposed_job_id=job_id,
            expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
        )


def test_rejects_a_work_path_outside_the_managed_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        repository(tmp_path).get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id="11111111-1111-4111-8111-111111111111",
            expected_work_path=tmp_path / "outside",
        )


def test_reports_missing_managed_directories_on_restore(tmp_path: Path) -> None:
    jobs = repository(tmp_path)
    created = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="11111111-1111-4111-8111-111111111111",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )
    (Path(created["workPath"]) / "input").rmdir()

    restored = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="22222222-2222-4222-8222-222222222222",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )

    assert restored["pathState"] == "missing"


def test_concurrent_get_or_create_restores_the_single_persisted_job(
    tmp_path: Path,
) -> None:
    managed_root = tmp_path / "GraceTreeData"
    first = JobRepository(managed_root)
    second = JobRepository(managed_root)

    def load(jobs: JobRepository, job_id: str) -> dict[str, object]:
        return jobs.get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id=job_id,
            expected_work_path=managed_root / "jobs" / "2026-06-20",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                load, first, "11111111-1111-4111-8111-111111111111"
            ),
            executor.submit(
                load, second, "22222222-2222-4222-8222-222222222222"
            ),
        ]

    created, restored = [future.result() for future in futures]
    assert restored == created

    with sqlite3.connect(managed_root / "studio.db") as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE publish_date = ?", ("2026-06-20",)
        ).fetchone()
    assert count == (1,)


def test_insert_failure_removes_only_new_empty_job_directories(tmp_path: Path) -> None:
    jobs = repository(tmp_path)
    work_path = tmp_path / "GraceTreeData" / "jobs" / "2026-06-20"
    with sqlite3.connect(tmp_path / "GraceTreeData" / "studio.db") as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_job_insert
            BEFORE INSERT ON jobs
            BEGIN
                SELECT RAISE(ABORT, 'forced insert failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        jobs.get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id="11111111-1111-4111-8111-111111111111",
            expected_work_path=work_path,
        )

    assert not work_path.exists()


@pytest.mark.parametrize(
    ("column", "invalid_value"),
    [
        ("work_path", "jobs/2026-06-20"),
        ("result_path", "output"),
    ],
)
def test_rejects_noncanonical_stored_paths(
    tmp_path: Path, column: str, invalid_value: str
) -> None:
    jobs = repository(tmp_path)
    created = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="11111111-1111-4111-8111-111111111111",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )
    with sqlite3.connect(tmp_path / "GraceTreeData" / "studio.db") as connection:
        connection.execute(
            f"UPDATE jobs SET {column} = ? WHERE id = ?",
            (invalid_value, created["id"]),
        )

    with pytest.raises(ValueError, match="stored .* path"):
        jobs.get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id="22222222-2222-4222-8222-222222222222",
            expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
        )


def test_rejects_a_stored_result_path_other_than_canonical_output(
    tmp_path: Path,
) -> None:
    jobs = repository(tmp_path)
    created = jobs.get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="11111111-1111-4111-8111-111111111111",
        expected_work_path=tmp_path / "GraceTreeData" / "jobs" / "2026-06-20",
    )
    work_path = Path(created["workPath"])
    with sqlite3.connect(tmp_path / "GraceTreeData" / "studio.db") as connection:
        connection.execute(
            "UPDATE jobs SET result_path = ? WHERE id = ?",
            (str(work_path / "input"), created["id"]),
        )

    with pytest.raises(ValueError, match="canonical output"):
        jobs.get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id="22222222-2222-4222-8222-222222222222",
            expected_work_path=work_path,
        )


def test_rejects_noncanonical_managed_root(tmp_path: Path) -> None:
    relative_root = Path("relative") / "GraceTreeData"

    with pytest.raises(ValueError, match="managed root"):
        JobRepository(relative_root)


# ---------------------------------------------------------------------------
# get_completed_jobs 테스트
# ---------------------------------------------------------------------------

def _open_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "studio.db"
    apply_migrations(db_path)
    return connect_database(db_path)


def _insert_job(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    publish_date: str,
    status: str,
    title: str | None = None,
    result_path: str = "/some/output",
    updated_at: str = "2026-06-25T10:00:00.000Z",
) -> None:
    conn.execute(
        """
        INSERT INTO jobs (id, publish_date, status, title, work_path, result_path,
                          created_at, updated_at)
        VALUES (?, ?, ?, ?, '/some/work', ?, '2026-06-25T09:00:00.000Z', ?)
        """,
        (job_id, publish_date, status, title, result_path, updated_at),
    )
    conn.commit()


def test_get_completed_jobs_empty_db(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        result = get_completed_jobs(conn)
    assert result == []


def test_get_completed_jobs_only_draft_returns_empty(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        _insert_job(
            conn,
            job_id="11111111-1111-4111-8111-111111111111",
            publish_date="2026-06-20",
            status="draft",
        )
        result = get_completed_jobs(conn)
    assert result == []


def test_get_completed_jobs_single_completed(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        _insert_job(
            conn,
            job_id="11111111-1111-4111-8111-111111111111",
            publish_date="2026-06-20",
            status="completed",
            title="오늘의 말씀",
            result_path="/data/output",
            updated_at="2026-06-20T10:00:00.000Z",
        )
        result = get_completed_jobs(conn)

    assert len(result) == 1
    assert result[0]["id"] == "11111111-1111-4111-8111-111111111111"
    assert result[0]["publishDate"] == "2026-06-20"
    assert result[0]["title"] == "오늘의 말씀"
    assert result[0]["completedAt"] == "2026-06-20T10:00:00.000Z"
    assert result[0]["resultPath"] == "/data/output"


def test_get_completed_jobs_ordered_by_publish_date_desc(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        _insert_job(
            conn,
            job_id="11111111-1111-4111-8111-111111111111",
            publish_date="2026-06-18",
            status="completed",
            updated_at="2026-06-18T10:00:00.000Z",
        )
        _insert_job(
            conn,
            job_id="22222222-2222-4222-8222-222222222222",
            publish_date="2026-06-25",
            status="completed",
            updated_at="2026-06-25T10:00:00.000Z",
        )
        _insert_job(
            conn,
            job_id="33333333-3333-4333-8333-333333333333",
            publish_date="2026-06-20",
            status="completed",
            updated_at="2026-06-20T10:00:00.000Z",
        )
        result = get_completed_jobs(conn)

    assert len(result) == 3
    assert result[0]["publishDate"] == "2026-06-25"
    assert result[1]["publishDate"] == "2026-06-20"
    assert result[2]["publishDate"] == "2026-06-18"


def test_get_completed_jobs_mixed_statuses_returns_only_completed(
    tmp_path: Path,
) -> None:
    with _open_db(tmp_path) as conn:
        _insert_job(
            conn,
            job_id="11111111-1111-4111-8111-111111111111",
            publish_date="2026-06-20",
            status="completed",
        )
        _insert_job(
            conn,
            job_id="22222222-2222-4222-8222-222222222222",
            publish_date="2026-06-21",
            status="draft",
        )
        _insert_job(
            conn,
            job_id="33333333-3333-4333-8333-333333333333",
            publish_date="2026-06-22",
            status="failed",
        )
        _insert_job(
            conn,
            job_id="44444444-4444-4444-8444-444444444444",
            publish_date="2026-06-23",
            status="running",
        )
        result = get_completed_jobs(conn)

    assert len(result) == 1
    assert result[0]["id"] == "11111111-1111-4111-8111-111111111111"


def test_get_completed_jobs_title_none(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        _insert_job(
            conn,
            job_id="11111111-1111-4111-8111-111111111111",
            publish_date="2026-06-20",
            status="completed",
            title=None,
        )
        result = get_completed_jobs(conn)

    assert len(result) == 1
    assert result[0]["title"] is None
