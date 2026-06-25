from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ..inputs.classifier import INPUT_ROLES, classify_input, resolve_input_states
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
        results = [
            self._register_one(job_id, source_path, input_dir, temp_dir)
            for source_path in source_paths
        ]
        inputs_by_id = {item["id"]: item for item in self.list_inputs(job_id)}
        for result in results:
            input_value = result.get("input")
            if input_value is not None:
                current = inputs_by_id[input_value["id"]]
                result["input"] = current
                result["role"] = current["role"]
        return results

    def list_inputs(self, job_id: str) -> list[dict[str, Any]]:
        if not _valid_uuid(job_id):
            raise ValueError("job_id must be a canonical UUID")
        with connect_database(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, job_id, role, original_name, managed_path, status,
                       created_at, updated_at
                FROM job_inputs
                WHERE job_id = ?
                ORDER BY created_at, id
                """,
                (job_id,),
            ).fetchall()
        return [self._to_dto(row) for row in rows]

    def assign_role(
        self, job_id: str, input_id: str, role: str
    ) -> list[dict[str, Any]]:
        if not _valid_uuid(job_id) or not _valid_uuid(input_id):
            raise ValueError("job_id and input_id must be canonical UUIDs")
        if role not in INPUT_ROLES:
            raise ValueError("role is invalid")
        now = _utc_now()
        with connect_database(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE job_inputs
                SET role = ?, updated_at = ?
                WHERE id = ? AND job_id = ?
                """,
                (role, now, input_id, job_id),
            )
            if updated.rowcount != 1:
                raise ValueError("input does not exist")
            self._recalculate_states(connection, job_id, now)
        return self.list_inputs(job_id)

    def remove_input(self, job_id: str, input_id: str) -> list[dict[str, Any]]:
        row, managed_path, temp_dir = self._load_stored_input(job_id, input_id)
        backup_path = temp_dir / f"{uuid4()}.remove-backup"
        os.link(managed_path, backup_path)
        connection = connect_database(self.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            deleted = connection.execute(
                "DELETE FROM job_inputs WHERE id = ? AND job_id = ?",
                (input_id, job_id),
            )
            if deleted.rowcount != 1:
                raise ValueError("input does not exist")
            managed_path.unlink()
            self._recalculate_states(connection, job_id, _utc_now())
            connection.commit()
        except Exception:
            connection.rollback()
            if not managed_path.exists() and backup_path.exists():
                os.link(backup_path, managed_path)
            raise
        finally:
            connection.close()
            _unlink_quietly(backup_path)
        return self.list_inputs(str(row["job_id"]))

    def replace_input(
        self, job_id: str, input_id: str, source_path: Path
    ) -> list[dict[str, Any]]:
        row, old_path, temp_dir = self._load_stored_input(job_id, input_id)
        canonical_source, source_stat = self._validate_source(source_path)
        new_path = old_path.parent / canonical_source.name
        if new_path != old_path and new_path.exists():
            raise ValueError("replacement target already exists")

        temp_path = temp_dir / f"{uuid4()}.replacement-copy"
        backup_path = temp_dir / f"{uuid4()}.replacement-backup"
        try:
            copied_stat = self._copy_to_temp(canonical_source, temp_path, source_stat)
            if copied_stat.st_size != source_stat.st_size:
                raise OSError("copy size mismatch")
            os.replace(old_path, backup_path)
            try:
                os.link(temp_path, new_path)
                connection = connect_database(self.database_path)
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    now = _utc_now()
                    updated = connection.execute(
                        """
                        UPDATE job_inputs
                        SET original_name = ?, managed_path = ?, updated_at = ?
                        WHERE id = ? AND job_id = ?
                        """,
                        (
                            canonical_source.name,
                            str(new_path),
                            now,
                            input_id,
                            job_id,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise ValueError("input does not exist")
                    self._recalculate_states(connection, job_id, now)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    _unlink_quietly(new_path)
                    os.replace(backup_path, old_path)
                    raise
                finally:
                    connection.close()
            except Exception:
                if backup_path.exists() and not old_path.exists():
                    os.replace(backup_path, old_path)
                raise
            backup_path.unlink()
        finally:
            _unlink_quietly(temp_path)
        return self.list_inputs(str(row["job_id"]))

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
            role = classify_input(canonical_source.name)
            with connect_database(self.database_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                input_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO job_inputs (
                        id, job_id, role, original_name, managed_path, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'unclassified', ?, ?)
                    """,
                    (
                        input_id,
                        job_id,
                        role,
                        canonical_source.name,
                        str(target),
                        now,
                        now,
                    ),
                )
                self._recalculate_states(connection, job_id, now)
                inserted = connection.execute(
                    """
                    SELECT id, job_id, role, original_name, managed_path, status,
                           created_at, updated_at
                    FROM job_inputs WHERE id = ?
                    """,
                    (input_id,),
                ).fetchone()
        except (OSError, sqlite3.Error):
            if created_target:
                _unlink_quietly(target)
            return {**base, "status": "rejected", "errorCode": "COPY_FAILED"}
        finally:
            _unlink_quietly(temp_path)
        return {
            **base,
            "role": role,
            "managedPath": str(target),
            "status": "registered",
            "errorCode": None,
            "input": self._to_dto(inserted),
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

    def _validate_source(self, source_path: Path) -> tuple[Path, os.stat_result]:
        if _has_symlink_component(source_path) or not source_path.is_absolute():
            raise ValueError("replacement source is invalid")
        try:
            canonical_source = source_path.resolve(strict=True)
            stat = canonical_source.stat()
        except OSError as error:
            raise ValueError("replacement source is unreadable") from error
        if (
            canonical_source.is_relative_to(self.managed_root)
            or not canonical_source.is_file()
            or stat.st_size <= 0
            or stat.st_size > MAX_INPUT_BYTES
            or canonical_source.suffix.lower() not in SUPPORTED_EXTENSIONS
        ):
            raise ValueError("replacement source is invalid")
        return canonical_source, stat

    def _load_stored_input(
        self, job_id: str, input_id: str
    ) -> tuple[Any, Path, Path]:
        if not _valid_uuid(job_id) or not _valid_uuid(input_id):
            raise ValueError("job_id and input_id must be canonical UUIDs")
        with connect_database(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT input.*, jobs.work_path
                FROM job_inputs AS input
                JOIN jobs ON jobs.id = input.job_id
                WHERE input.id = ? AND input.job_id = ?
                """,
                (input_id, job_id),
            ).fetchone()
        if row is None:
            raise ValueError("input does not exist")
        work_path = Path(str(row["work_path"]))
        managed_path = Path(str(row["managed_path"]))
        expected_input_dir = work_path / "input"
        temp_dir = work_path / "temp"
        try:
            if (
                not managed_path.is_absolute()
                or managed_path.resolve(strict=True) != managed_path
                or managed_path.parent != expected_input_dir
                or not managed_path.is_relative_to(self.managed_root)
                or _has_symlink_component(managed_path)
                or temp_dir.resolve(strict=True) != temp_dir
                or not temp_dir.is_dir()
                or not temp_dir.is_relative_to(self.managed_root)
            ):
                raise ValueError("stored path is outside the managed input directory")
        except OSError as error:
            raise ValueError("stored path is outside the managed input directory") from error
        return row, managed_path, temp_dir

    def _recalculate_states(
        self, connection: sqlite3.Connection, job_id: str, now: str
    ) -> None:
        rows = connection.execute(
            "SELECT id, role FROM job_inputs WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        states = resolve_input_states(rows)
        connection.executemany(
            "UPDATE job_inputs SET status = ?, updated_at = ? WHERE id = ?",
            [(state, now, input_id) for input_id, state in states.items()],
        )

    def _to_dto(self, row: Any) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "jobId": str(row["job_id"]),
            "role": str(row["role"]),
            "originalName": str(row["original_name"]),
            "managedPath": str(row["managed_path"]),
            "status": str(row["status"]),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
        }
