"""Resource service — business logic for updating common shared resources."""
from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from ..storage.migrations import apply_migrations, connect_database
from ..storage.resource_repository import get_all_resources, upsert_resource

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "title_scripture_video": {".mp4", ".mov", ".avi", ".mkv"},
    "prayer_loop_video": {".mp4", ".mov", ".avi", ".mkv"},
    "default_bgm": {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"},
    "subtitle_font": {".ttf", ".otf", ".woff", ".woff2"},
}


def _make_error(resource_type: str, code: str, message: str) -> dict[str, Any]:
    return {"resourceType": resource_type, "code": code, "message": message}


def update_resource(
    conn: sqlite3.Connection,
    managed_root: str,
    resource_type: str,
    source_path: str,
) -> dict[str, Any]:
    """
    Copy *source_path* into the managed resources directory and record it in DB.

    Returns::

        {
            "resources": [...],   # current state of all resources
            "error": None | {"resourceType": ..., "code": ..., "message": ...}
        }

    Errors do NOT raise — they are returned in the ``error`` field.
    The ``resources`` field always reflects the current DB state.
    """
    root = Path(managed_root)

    # 1. managed_root must exist
    if not root.is_dir():
        resources = get_all_resources(conn)
        return {
            "resources": resources,
            "error": _make_error(
                resource_type,
                "MANAGED_ROOT_MISSING",
                f"managed root does not exist: {managed_root}",
            ),
        }

    # 2. source file must be readable
    source = Path(source_path)
    if not source.is_file() or not os.access(source, os.R_OK):
        resources = get_all_resources(conn)
        return {
            "resources": resources,
            "error": _make_error(
                resource_type,
                "SOURCE_UNREADABLE",
                f"source file is not readable: {source_path}",
            ),
        }

    # 3. extension check
    ext = source.suffix.lower()
    allowed = ALLOWED_EXTENSIONS.get(resource_type, set())
    if ext not in allowed:
        resources = get_all_resources(conn)
        return {
            "resources": resources,
            "error": _make_error(
                resource_type,
                "UNSUPPORTED_FORMAT",
                f"unsupported file extension '{ext}' for resource type '{resource_type}'",
            ),
        }

    # 4. determine destination path
    resources_dir = root / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    dest = resources_dir / f"{resource_type}{ext}"

    # 5. atomic copy — keep old file on failure
    backup: Path | None = None
    if dest.exists():
        backup = dest.with_suffix(dest.suffix + ".backup")
        try:
            os.replace(dest, backup)
        except OSError as exc:
            resources = get_all_resources(conn)
            return {
                "resources": resources,
                "error": _make_error(
                    resource_type,
                    "COPY_FAILED",
                    f"could not move existing resource aside: {exc}",
                ),
            }

    try:
        shutil.copy2(str(source), str(dest))
    except OSError as exc:
        # restore backup if we moved it
        if backup is not None and backup.exists() and not dest.exists():
            try:
                os.replace(backup, dest)
            except OSError:
                pass
        resources = get_all_resources(conn)
        return {
            "resources": resources,
            "error": _make_error(
                resource_type,
                "COPY_FAILED",
                f"failed to copy resource: {exc}",
            ),
        }

    # remove backup only after successful copy
    if backup is not None and backup.exists():
        try:
            backup.unlink()
        except OSError:
            pass  # non-fatal; leave the backup in place

    # 6. persist to DB
    upsert_resource(conn, resource_type, str(dest), "ready")
    conn.commit()

    resources = get_all_resources(conn)
    return {"resources": resources, "error": None}
