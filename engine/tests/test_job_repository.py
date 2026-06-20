from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gracetree_engine.storage.job_repository import JobRepository


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
