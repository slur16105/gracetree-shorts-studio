"""Resource repository — manages common shared resources (videos, BGM, font)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _to_dto(row: Any) -> dict[str, Any]:
    return {
        "type": row["resource_type"],
        "managedPath": row["managed_path"],
        "status": row["status"],
        "updatedAt": row["updated_at"],
    }


def get_all_resources(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all resource rows as camelCase DTOs."""
    rows = conn.execute(
        "SELECT resource_type, managed_path, status, updated_at FROM resources"
        " ORDER BY resource_type"
    ).fetchall()
    return [_to_dto(row) for row in rows]


def upsert_resource(
    conn: sqlite3.Connection,
    resource_type: str,
    managed_path: str | None,
    status: str,
) -> dict[str, Any]:
    """Insert or replace a resource row and return the resulting DTO."""
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO resources (resource_type, managed_path, status, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(resource_type) DO UPDATE SET
            managed_path = excluded.managed_path,
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (resource_type, managed_path, status, now),
    )
    row = conn.execute(
        "SELECT resource_type, managed_path, status, updated_at FROM resources"
        " WHERE resource_type = ?",
        (resource_type,),
    ).fetchone()
    return _to_dto(row)


def get_resource(
    conn: sqlite3.Connection, resource_type: str
) -> dict[str, Any] | None:
    """Return a single resource DTO, or None if not found."""
    row = conn.execute(
        "SELECT resource_type, managed_path, status, updated_at FROM resources"
        " WHERE resource_type = ?",
        (resource_type,),
    ).fetchone()
    return _to_dto(row) if row is not None else None
