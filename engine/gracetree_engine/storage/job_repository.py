from __future__ import annotations

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
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JobRepository:
    def __init__(self, managed_root: Path) -> None:
        self.managed_root = managed_root.resolve()
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
        supplied_work_path = expected_work_path.resolve()
        if supplied_work_path != canonical_work_path:
            raise ValueError("work path does not match the managed date path")
        if not canonical_work_path.is_relative_to(self.managed_root):
            raise ValueError("work path escapes the managed root")

        with connect_database(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE publish_date = ?", (valid_date,)
            ).fetchone()
            if row is None:
                for child in ("input", "output", "temp", "logs"):
                    (canonical_work_path / child).mkdir(parents=True, exist_ok=True)
                now = _utc_now()
                result_path = canonical_work_path / "output"
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
                row = connection.execute(
                    "SELECT * FROM jobs WHERE publish_date = ?", (valid_date,)
                ).fetchone()

        if row is None:
            raise RuntimeError("job could not be loaded after creation")
        return self._to_dto(row)

    def _to_dto(self, row: Any) -> JobDto:
        work_path = Path(str(row["work_path"]))
        required_paths = [work_path / child for child in ("input", "output", "temp", "logs")]
        path_state = "ready" if all(path.is_dir() for path in required_paths) else "missing"
        return {
            "id": str(row["id"]),
            "publishDate": str(row["publish_date"]),
            "status": str(row["status"]),
            "title": row["title"],
            "workPath": str(row["work_path"]),
            "resultPath": str(row["result_path"]),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
            "pathState": path_state,
            "inputMetadata": [],
        }
