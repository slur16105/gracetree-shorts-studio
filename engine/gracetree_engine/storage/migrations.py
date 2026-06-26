from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..resource_resolver import migrations_dir as _migrations_dir

MIGRATIONS_DIR = _migrations_dir()


def connect_database(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def apply_migrations(
    database_path: Path, *, migrations_dir: Path = MIGRATIONS_DIR
) -> list[int]:
    migrations: list[tuple[int, Path]] = []
    versions: set[int] = set()
    for migration_path in sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(migration_path.name.split("_", 1)[0])
        if version in versions:
            raise ValueError(f"duplicate migration version {version}")
        versions.add(version)
        migrations.append((version, migration_path))

    applied: list[int] = []
    with connect_database(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        existing = {
            int(row["version"])
            for row in connection.execute("SELECT version FROM schema_migrations")
        }

        for version, migration_path in migrations:
            if version in existing:
                continue

            sql = migration_path.read_text(encoding="utf-8")
            applied_at = (
                datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                f"{sql}\n"
                "INSERT INTO schema_migrations(version, applied_at) "
                f"VALUES ({version}, '{applied_at}');\n"
                "COMMIT;"
            )
            applied.append(version)

    return applied
