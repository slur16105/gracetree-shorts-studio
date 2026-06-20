from __future__ import annotations

import sqlite3
from pathlib import Path

from gracetree_engine.storage.migrations import apply_migrations, connect_database


def test_applies_migrations_once_to_an_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "studio.db"

    assert apply_migrations(database_path) == [1]
    assert apply_migrations(database_path) == []

    with connect_database(database_path) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
        columns = connection.execute("PRAGMA table_info(jobs)").fetchall()

    assert [tuple(row) for row in versions] == [(1,)]
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

    assert apply_migrations(database_path) == [1]
