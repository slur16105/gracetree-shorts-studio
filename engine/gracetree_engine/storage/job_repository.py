from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from .migrations import apply_migrations, connect_database

JobDto = dict[str, Any]


def _validate_publish_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("publish_date must be a valid YYYY-MM-DD date") from error
    if parsed.isoformat() != value:
        raise ValueError("publish_date must be a valid YYYY-MM-DD date")
    return value


def _validate_job_id(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise ValueError("job_id must be a UUID") from error
    if str(parsed) != value.lower():
        raise ValueError("job_id must use canonical UUID form")
    return value


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _require_canonical_absolute_path(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    resolved = path.resolve()
    if path != resolved:
        raise ValueError(f"{label} must use canonical path form")
    return resolved


def _create_job_directories(work_path: Path) -> list[Path]:
    created: list[Path] = []
    paths = [
        work_path.parent,
        work_path,
        *(work_path / child for child in ("input", "output", "temp", "logs")),
    ]
    for path in paths:
        if path.exists():
            continue
        path.mkdir()
        created.append(path)
    return created


def _remove_empty_directories(paths: list[Path]) -> None:
    for path in reversed(paths):
        try:
            path.rmdir()
        except OSError:
            pass


class JobRepository:
    def __init__(self, managed_root: Path) -> None:
        self.managed_root = _require_canonical_absolute_path(
            managed_root, "managed root"
        )
        self.database_path = self.managed_root / "studio.db"
        apply_migrations(self.database_path)

    def get_or_create_for_date(
        self,
        *,
        publish_date: str,
        proposed_job_id: str,
        expected_work_path: Path,
    ) -> JobDto:
        valid_date = _validate_publish_date(publish_date)
        valid_job_id = _validate_job_id(proposed_job_id)
        canonical_work_path = (self.managed_root / "jobs" / valid_date).resolve()
        supplied_work_path = _require_canonical_absolute_path(
            expected_work_path, "work path"
        )
        if supplied_work_path != canonical_work_path:
            raise ValueError("work path does not match the managed date path")
        if not canonical_work_path.is_relative_to(self.managed_root):
            raise ValueError("work path escapes the managed root")

        created_directories: list[Path] = []
        with connect_database(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE publish_date = ?", (valid_date,)
            ).fetchone()
            if row is None:
                created_directories = _create_job_directories(canonical_work_path)
                now = _utc_now()
                result_path = canonical_work_path / "output"
                try:
                    connection.execute(
                        """
                        INSERT INTO jobs (
                            id, publish_date, status, title, work_path, result_path,
                            created_at, updated_at
                        ) VALUES (?, ?, 'draft', NULL, ?, ?, ?, ?)
                        """,
                        (
                            valid_job_id,
                            valid_date,
                            str(canonical_work_path),
                            str(result_path),
                            now,
                            now,
                        ),
                    )
                except sqlite3.IntegrityError:
                    connection.rollback()
                    row = connection.execute(
                        "SELECT * FROM jobs WHERE publish_date = ?", (valid_date,)
                    ).fetchone()
                    if row is None:
                        _remove_empty_directories(created_directories)
                        raise
                except sqlite3.Error:
                    connection.rollback()
                    _remove_empty_directories(created_directories)
                    raise
                row = connection.execute(
                    "SELECT * FROM jobs WHERE publish_date = ?", (valid_date,)
                ).fetchone()

        if row is None:
            raise RuntimeError("job could not be loaded after creation")
        return self._to_dto(row)

    def _to_dto(self, row: Any) -> JobDto:
        publish_date = _validate_publish_date(str(row["publish_date"]))
        expected_work_path = (self.managed_root / "jobs" / publish_date).resolve()
        work_path = _require_canonical_absolute_path(
            Path(str(row["work_path"])), "stored work path"
        )
        if work_path != expected_work_path:
            raise ValueError("stored work path does not match the managed date path")
        result_path = _require_canonical_absolute_path(
            Path(str(row["result_path"])), "stored result path"
        )
        if result_path != work_path / "output":
            raise ValueError("stored result path is not the canonical output path")
        required_paths = [
            work_path / child for child in ("input", "output", "temp", "logs")
        ]
        path_state = "ready" if all(path.is_dir() for path in required_paths) else "missing"
        return {
            "id": str(row["id"]),
            "publishDate": publish_date,
            "status": str(row["status"]),
            "title": row["title"],
            "workPath": str(work_path),
            "resultPath": str(result_path),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
            "pathState": path_state,
            "inputMetadata": [],
        }
