from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gracetree_engine.storage.migrations import apply_migrations, connect_database
from gracetree_engine.storage.resource_repository import get_all_resources, get_resource
from gracetree_engine.inputs.resource_service import update_resource


def _setup(tmp_path: Path):
    """Create managed_root with DB and return (managed_root, conn)."""
    root = tmp_path / "GraceTreeData"
    root.mkdir()
    db_path = root / "studio.db"
    apply_migrations(db_path)
    conn = connect_database(db_path)
    return root, conn


def test_successful_copy_sets_status_ready(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "bgm.mp3"
    source.write_bytes(b"audio data")

    result = update_resource(conn, str(root), "default_bgm", str(source))

    assert result["error"] is None
    resources = result["resources"]
    bgm = next(r for r in resources if r["type"] == "default_bgm")
    assert bgm["status"] == "ready"
    assert bgm["managedPath"] is not None
    assert Path(bgm["managedPath"]).exists()
    assert Path(bgm["managedPath"]).read_bytes() == b"audio data"
    conn.close()


def test_successful_copy_reflects_all_resources(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "font.ttf"
    source.write_bytes(b"font bytes")

    result = update_resource(conn, str(root), "subtitle_font", str(source))

    assert result["error"] is None
    assert len(result["resources"]) == 4
    conn.close()


def test_unreadable_source_returns_source_unreadable_error(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    missing = tmp_path / "missing.mp3"

    result = update_resource(conn, str(root), "default_bgm", str(missing))

    assert result["error"] is not None
    assert result["error"]["code"] == "SOURCE_UNREADABLE"
    assert result["error"]["resourceType"] == "default_bgm"
    # DB unchanged — still missing
    db_resource = get_resource(conn, "default_bgm")
    assert db_resource is not None
    assert db_resource["status"] == "missing"
    conn.close()


def test_unreadable_source_no_permission_returns_source_unreadable_error(
    tmp_path: Path,
) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "bgm.mp3"
    source.write_bytes(b"audio")
    os.chmod(source, 0o000)

    try:
        result = update_resource(conn, str(root), "default_bgm", str(source))
        assert result["error"] is not None
        assert result["error"]["code"] == "SOURCE_UNREADABLE"
    finally:
        os.chmod(source, 0o644)
    conn.close()


def test_unsupported_extension_returns_error(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "bgm.exe"
    source.write_bytes(b"binary")

    result = update_resource(conn, str(root), "default_bgm", str(source))

    assert result["error"] is not None
    assert result["error"]["code"] == "UNSUPPORTED_FORMAT"
    db_resource = get_resource(conn, "default_bgm")
    assert db_resource is not None
    assert db_resource["status"] == "missing"
    conn.close()


def test_unsupported_extension_for_video_type(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "video.mp3"  # mp3 not allowed for video type
    source.write_bytes(b"audio")

    result = update_resource(conn, str(root), "title_scripture_video", str(source))

    assert result["error"] is not None
    assert result["error"]["code"] == "UNSUPPORTED_FORMAT"
    conn.close()


def test_managed_root_missing_returns_error(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "bgm.mp3"
    source.write_bytes(b"audio")
    non_existent_root = tmp_path / "nonexistent"

    result = update_resource(conn, str(non_existent_root), "default_bgm", str(source))

    assert result["error"] is not None
    assert result["error"]["code"] == "MANAGED_ROOT_MISSING"
    conn.close()


def test_successful_replacement_overwrites_previous_file(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)

    # First upload
    first = tmp_path / "bgm_v1.mp3"
    first.write_bytes(b"version one")
    r1 = update_resource(conn, str(root), "default_bgm", str(first))
    assert r1["error"] is None
    first_path = next(
        r["managedPath"] for r in r1["resources"] if r["type"] == "default_bgm"
    )

    # Second upload (same type, different source)
    second = tmp_path / "bgm_v2.mp3"
    second.write_bytes(b"version two")
    r2 = update_resource(conn, str(root), "default_bgm", str(second))
    assert r2["error"] is None

    second_path = next(
        r["managedPath"] for r in r2["resources"] if r["type"] == "default_bgm"
    )
    # Destination path may be the same file (same resource_type + ext)
    assert Path(second_path).read_bytes() == b"version two"
    # Old backup should be cleaned up
    backup = Path(second_path + ".backup")
    assert not backup.exists()
    conn.close()


def test_copy_failure_preserves_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, conn = _setup(tmp_path)

    # First upload succeeds
    first = tmp_path / "bgm_v1.mp3"
    first.write_bytes(b"original")
    r1 = update_resource(conn, str(root), "default_bgm", str(first))
    assert r1["error"] is None
    dest_path = Path(
        next(r["managedPath"] for r in r1["resources"] if r["type"] == "default_bgm")
    )

    # Second upload — simulate copy failure
    second = tmp_path / "bgm_v2.mp3"
    second.write_bytes(b"new version")

    import shutil as shutil_mod

    original_copy2 = shutil_mod.copy2

    def fail_copy2(src: Any, dst: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(shutil_mod, "copy2", fail_copy2)

    r2 = update_resource(conn, str(root), "default_bgm", str(second))

    assert r2["error"] is not None
    assert r2["error"]["code"] == "COPY_FAILED"
    # Original file preserved
    assert dest_path.exists()
    assert dest_path.read_bytes() == b"original"
    # DB still shows ready with old path
    db_resource = get_resource(conn, "default_bgm")
    assert db_resource is not None
    assert db_resource["status"] == "ready"
    assert db_resource["managedPath"] == str(dest_path)
    conn.close()


def test_resources_dir_created_automatically(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    resources_dir = root / "resources"
    assert not resources_dir.exists()

    source = tmp_path / "bgm.mp3"
    source.write_bytes(b"audio")
    update_resource(conn, str(root), "default_bgm", str(source))

    assert resources_dir.is_dir()
    conn.close()


def test_destination_filename_uses_resource_type_plus_extension(tmp_path: Path) -> None:
    root, conn = _setup(tmp_path)
    source = tmp_path / "my_bgm_track.mp3"
    source.write_bytes(b"audio")

    result = update_resource(conn, str(root), "default_bgm", str(source))

    assert result["error"] is None
    dest = Path(
        next(r["managedPath"] for r in result["resources"] if r["type"] == "default_bgm")
    )
    assert dest.name == "default_bgm.mp3"
    conn.close()
