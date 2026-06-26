from __future__ import annotations

import re
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


def _split_sql(sql: str) -> list[str]:
    """세미콜론으로 SQL을 개별 문장으로 분리한다. 단일행 주석은 제거한다."""
    sql = re.sub(r"--[^\n]*", "", sql)
    statements = [s.strip() for s in sql.split(";")]
    return [s for s in statements if s]


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
            # Python의 묵시적 트랜잭션 관리가 ALTER TABLE RENAME 등 DDL 시퀀스를 방해하지
            # 않도록 autocommit 모드(isolation_level=None)에서 직접 BEGIN/COMMIT을 제어한다.
            prev_isolation = connection.isolation_level
            connection.isolation_level = None
            try:
                connection.execute("BEGIN IMMEDIATE")
                for statement in _split_sql(sql):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) "
                    f"VALUES ({version}, '{applied_at}')"
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
            finally:
                connection.isolation_level = prev_isolation
            applied.append(version)

    return applied
