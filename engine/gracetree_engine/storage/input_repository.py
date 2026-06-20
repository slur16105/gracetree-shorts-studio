from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .migrations import apply_migrations, connect_database

SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".txt",
}
MAX_INPUT_BYTES = 4 * 1024 * 1024 * 1024


def _utc_now() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _valid_uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value.lower()
    except ValueError:
        return False


def _has_symlink_component(path: Path) -> bool:
    for component in (path, *path.parents):
        if component.parent == Path(component.anchor):
            continue
        if component.is_symlink():
            return True
    return False


def _same_file_state(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_size,
        first.st_mtime_ns,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_size,
        second.st_mtime_ns,
    )


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


class InputRepository:
    def __init__(self, managed_root: Path) -> None:
        if not managed_root.is_absolute() or managed_root != managed_root.resolve():
            raise ValueError("managed root must be canonical and absolute")
        self.managed_root = managed_root
        self.database_path = managed_root / "studio.db"
        apply_migrations(self.database_path)

    def register_batch(self, job_id: str, source_paths: list[Path]) -> list[dict[str, Any]]:
        if not _valid_uuid(job_id):
            raise ValueError("job_id must be a canonical UUID")
        with connect_database(self.database_path) as connection:
            job = connection.execute(
                "SELECT work_path FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if job is None:
            raise ValueError("job does not exist")
        work_path = Path(str(job["work_path"]))
        expected_work = work_path.resolve()
        if (
            not work_path.is_absolute()
            or work_path != expected_work
            or not expected_work.is_relative_to(self.managed_root)
        ):
            raise ValueError("job work path is invalid")
        input_dir = expected_work / "input"
        temp_dir = expected_work / "temp"
        for directory in (input_dir, temp_dir):
            try:
                if (
                    _has_symlink_component(directory)
                    or directory.resolve(strict=True) != directory
                    or not directory.is_dir()
                    or not directory.is_relative_to(self.managed_root)
                ):
                    raise ValueError("job storage directory is invalid")
            except OSError as error:
                raise ValueError("job storage directory is invalid") from error
        return [
            self._register_one(job_id, source_path, input_dir, temp_dir)
            for source_path in source_paths
        ]

    def _register_one(
        self, job_id: str, source_path: Path, input_dir: Path, temp_dir: Path
    ) -> dict[str, Any]:
        original_name = source_path.name or str(source_path)
        base = {
            "originalName": original_name,
            "managedPath": None,
            "role": "unclassified",
        }
        if _has_symlink_component(source_path):
            return {**base, "status": "rejected", "errorCode": "SYMLINK_NOT_ALLOWED"}
        if not source_path.is_absolute():
            return {**base, "status": "rejected", "errorCode": "SOURCE_UNREADABLE"}
        try:
            canonical_source = source_path.resolve(strict=True)
            stat = canonical_source.stat()
        except OSError:
            return {**base, "status": "rejected", "errorCode": "SOURCE_UNREADABLE"}
        if canonical_source.is_relative_to(self.managed_root):
            return {
                **base,
                "status": "rejected",
                "errorCode": "SOURCE_INSIDE_MANAGED_ROOT",
            }
        if not canonical_source.is_file() or stat.st_size <= 0:
            return {**base, "status": "rejected", "errorCode": "SOURCE_UNREADABLE"}
        if stat.st_size > MAX_INPUT_BYTES:
            return {**base, "status": "rejected", "errorCode": "FILE_TOO_LARGE"}
        if canonical_source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return {**base, "status": "rejected", "errorCode": "UNSUPPORTED_TYPE"}

        target = input_dir / canonical_source.name
        if target.exists():
            return {
                **base,
                "managedPath": str(target),
                "status": "conflict",
                "errorCode": "NAME_CONFLICT",
            }
        temp_path = temp_dir / f"{uuid4()}.input-copy"
        created_target = False
        try:
            copied_stat = self._copy_to_temp(canonical_source, temp_path, stat)
            if copied_stat.st_size != stat.st_size:
                raise OSError("copy size mismatch")
            try:
                os.link(temp_path, target)
                created_target = True
            except FileExistsError:
                return {
                    **base,
                    "managedPath": str(target),
                    "status": "conflict",
                    "errorCode": "NAME_CONFLICT",
                }
            now = _utc_now()
            with connect_database(self.database_path) as connection:
                input_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO job_inputs (
                        id, job_id, role, original_name, managed_path, status,
                        created_at, updated_at
                    ) VALUES (?, ?, 'unclassified', ?, ?, 'registered', ?, ?)
                    """,
                    (input_id, job_id, canonical_source.name, str(target), now, now),
                )
        except (OSError, sqlite3.Error):
            if created_target:
                _unlink_quietly(target)
            return {**base, "status": "rejected", "errorCode": "COPY_FAILED"}
        finally:
            _unlink_quietly(temp_path)
        return {
            **base,
            "managedPath": str(target),
            "status": "registered",
            "errorCode": None,
            "input": {
                "id": input_id,
                "jobId": job_id,
                "role": "unclassified",
                "originalName": canonical_source.name,
                "managedPath": str(target),
                "status": "registered",
                "createdAt": now,
                "updatedAt": now,
            },
        }

    def _copy_to_temp(
        self, source: Path, target: Path, expected_stat: os.stat_result
    ) -> os.stat_result:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as source_file, target.open("xb") as target_file:
            opened_stat = os.fstat(source_file.fileno())
            if not _same_file_state(expected_stat, opened_stat):
                raise OSError("source changed before copy")
            shutil.copyfileobj(source_file, target_file)
            target_file.flush()
            os.fsync(target_file.fileno())
            copied_source_stat = os.fstat(source_file.fileno())
            if not _same_file_state(opened_stat, copied_source_stat):
                raise OSError("source changed during copy")
        return target.stat()
