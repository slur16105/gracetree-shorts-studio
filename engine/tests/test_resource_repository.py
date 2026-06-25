from __future__ import annotations

from pathlib import Path

import pytest

from gracetree_engine.storage.migrations import apply_migrations, connect_database
from gracetree_engine.storage.resource_repository import (
    get_all_resources,
    get_resource,
    upsert_resource,
)


def _open_db(tmp_path: Path):
    db_path = tmp_path / "studio.db"
    apply_migrations(db_path)
    return connect_database(db_path)


def test_get_all_resources_returns_four_missing_rows_after_migration(
    tmp_path: Path,
) -> None:
    with _open_db(tmp_path) as conn:
        resources = get_all_resources(conn)

    assert len(resources) == 4
    types = {r["type"] for r in resources}
    assert types == {
        "title_scripture_video",
        "prayer_loop_video",
        "default_bgm",
        "subtitle_font",
    }
    for resource in resources:
        assert resource["status"] == "missing"
        assert resource["managedPath"] is None
        assert resource["updatedAt"]  # non-empty


def test_upsert_resource_updates_path_and_status(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        result = upsert_resource(
            conn,
            resource_type="default_bgm",
            managed_path="/data/resources/default_bgm.mp3",
            status="ready",
        )
        conn.commit()

        assert result["type"] == "default_bgm"
        assert result["managedPath"] == "/data/resources/default_bgm.mp3"
        assert result["status"] == "ready"

        # verify persisted
        row = get_resource(conn, "default_bgm")
        assert row is not None
        assert row["managedPath"] == "/data/resources/default_bgm.mp3"
        assert row["status"] == "ready"


def test_upsert_resource_replaces_existing_row(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        upsert_resource(conn, "subtitle_font", "/old/path.ttf", "ready")
        conn.commit()

        result = upsert_resource(conn, "subtitle_font", "/new/path.otf", "ready")
        conn.commit()

        assert result["managedPath"] == "/new/path.otf"
        # only one row per type
        all_resources = get_all_resources(conn)
        font_rows = [r for r in all_resources if r["type"] == "subtitle_font"]
        assert len(font_rows) == 1
        assert font_rows[0]["managedPath"] == "/new/path.otf"


def test_get_resource_returns_specific_type(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        upsert_resource(
            conn, "prayer_loop_video", "/prayer.mp4", "ready"
        )
        conn.commit()

        result = get_resource(conn, "prayer_loop_video")
        assert result is not None
        assert result["type"] == "prayer_loop_video"
        assert result["managedPath"] == "/prayer.mp4"
        assert result["status"] == "ready"


def test_get_resource_returns_none_for_unknown_type(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        result = get_resource(conn, "nonexistent_type")
    assert result is None


def test_get_all_resources_reflects_upsert_state(tmp_path: Path) -> None:
    with _open_db(tmp_path) as conn:
        upsert_resource(conn, "default_bgm", "/bgm.mp3", "ready")
        upsert_resource(conn, "subtitle_font", "/font.ttf", "ready")
        conn.commit()

        all_resources = get_all_resources(conn)

    ready_types = {r["type"] for r in all_resources if r["status"] == "ready"}
    assert ready_types == {"default_bgm", "subtitle_font"}
    missing_types = {r["type"] for r in all_resources if r["status"] == "missing"}
    assert missing_types == {"title_scripture_video", "prayer_loop_video"}
