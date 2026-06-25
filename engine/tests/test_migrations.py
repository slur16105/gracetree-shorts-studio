from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gracetree_engine.storage.migrations import apply_migrations, connect_database


def test_applies_migrations_once_to_an_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.db"

    assert apply_migrations(database_path) == [1, 2, 3, 4]
    assert apply_migrations(database_path) == []

    with connect_database(database_path) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
        columns = connection.execute("PRAGMA table_info(jobs)").fetchall()

    assert [tuple(row) for row in versions] == [(1,), (2,), (3,), (4,)]
    assert tuple(foreign_keys) == (1,)
    assert {column[1] for column in columns} >= {
        "id",
        "publish_date",
        "status",
        "title",
        "work_path",
        "result_path",
        "created_at",
        "updated_at",
    }


def test_upgrades_a_previous_schema_database(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )

    assert apply_migrations(database_path) == [1, 2, 3, 4]


def test_applies_002_to_a_story_1_3_database(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    source_dir = Path(__file__).resolve().parents[1] / "migrations"
    for name in ("001_create_jobs.sql",):
        (migrations_dir / name).write_text(
            (source_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    database_path = tmp_path / "studio.db"
    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [1]
    (migrations_dir / "002_create_job_inputs.sql").write_text(
        (source_dir / "002_create_job_inputs.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [2]
    assert apply_migrations(database_path, migrations_dir=migrations_dir) == []



def test_applies_003_to_a_story_1_4_database_and_preserves_rows(
    tmp_path: Path,
) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    source_dir = Path(__file__).resolve().parents[1] / "migrations"
    for name in ("001_create_jobs.sql", "002_create_job_inputs.sql"):
        (migrations_dir / name).write_text(
            (source_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    database_path = tmp_path / "studio.db"
    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [1, 2]
    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                id, publish_date, status, title, work_path, result_path,
                created_at, updated_at
            ) VALUES (?, '2026-06-20', 'draft', NULL, ?, ?, ?, ?)
            """,
            (
                "11111111-1111-4111-8111-111111111111",
                str(tmp_path / "jobs" / "2026-06-20"),
                str(tmp_path / "jobs" / "2026-06-20" / "output"),
                "2026-06-20T00:00:00.000Z",
                "2026-06-20T00:00:00.000Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO job_inputs (
                id, job_id, role, original_name, managed_path, status,
                created_at, updated_at
            ) VALUES (?, ?, 'unclassified', 'recording.mp3', ?, 'registered', ?, ?)
            """,
            (
                "22222222-2222-4222-8222-222222222222",
                "11111111-1111-4111-8111-111111111111",
                str(tmp_path / "jobs" / "2026-06-20" / "input" / "recording.mp3"),
                "2026-06-20T00:00:00.000Z",
                "2026-06-20T00:00:00.000Z",
            ),
        )
    (migrations_dir / "003_classify_job_inputs.sql").write_text(
        (source_dir / "003_classify_job_inputs.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [3]
    with connect_database(database_path) as connection:
        row = connection.execute("SELECT role, status FROM job_inputs").fetchone()
    assert tuple(row) == ("unclassified", "unclassified")


def test_applies_004_to_a_story_1_5_database_and_preserves_rows(
    tmp_path: Path,
) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    source_dir = Path(__file__).resolve().parents[1] / "migrations"
    for name in (
        "001_create_jobs.sql",
        "002_create_job_inputs.sql",
        "003_classify_job_inputs.sql",
    ):
        (migrations_dir / name).write_text(
            (source_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    database_path = tmp_path / "studio.db"
    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [1, 2, 3]

    # Insert a job and an input to verify data is preserved
    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                id, publish_date, status, title, work_path, result_path,
                created_at, updated_at
            ) VALUES (?, '2026-06-20', 'draft', NULL, ?, ?, ?, ?)
            """,
            (
                "11111111-1111-4111-8111-111111111111",
                str(tmp_path / "jobs" / "2026-06-20"),
                str(tmp_path / "jobs" / "2026-06-20" / "output"),
                "2026-06-20T00:00:00.000Z",
                "2026-06-20T00:00:00.000Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO job_inputs (
                id, job_id, role, original_name, managed_path, status,
                created_at, updated_at
            ) VALUES (?, ?, 'voice', 'voice.mp3', ?, 'ready', ?, ?)
            """,
            (
                "22222222-2222-4222-8222-222222222222",
                "11111111-1111-4111-8111-111111111111",
                str(tmp_path / "jobs" / "2026-06-20" / "input" / "voice.mp3"),
                "2026-06-20T00:00:00.000Z",
                "2026-06-20T00:00:00.000Z",
            ),
        )

    # Apply migration 004
    (migrations_dir / "004_create_resources.sql").write_text(
        (source_dir / "004_create_resources.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert apply_migrations(database_path, migrations_dir=migrations_dir) == [4]

    with connect_database(database_path) as connection:
        # Existing data preserved
        job_row = connection.execute("SELECT id FROM jobs").fetchone()
        input_row = connection.execute(
            "SELECT role, status FROM job_inputs"
        ).fetchone()
        # New resources table has 4 missing rows
        resource_rows = connection.execute(
            "SELECT resource_type, status FROM resources ORDER BY resource_type"
        ).fetchall()

    assert job_row is not None
    assert tuple(input_row) == ("voice", "ready")
    assert len(resource_rows) == 4
    for row in resource_rows:
        assert row["status"] == "missing"
    resource_types = {row["resource_type"] for row in resource_rows}
    assert resource_types == {
        "title_scripture_video",
        "prayer_loop_video",
        "default_bgm",
        "subtitle_font",
    }


def test_rejects_duplicate_migration_versions_before_opening_database(
    tmp_path: Path,
) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_create_first.sql").write_text(
        "CREATE TABLE first_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    (migrations_dir / "001_create_second.sql").write_text(
        "CREATE TABLE second_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    database_path = tmp_path / "data" / "studio.db"

    with pytest.raises(ValueError, match="duplicate migration version 1"):
        apply_migrations(database_path, migrations_dir=migrations_dir)

    assert not database_path.exists()
