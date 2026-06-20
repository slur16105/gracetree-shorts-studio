from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from gracetree_engine.storage.input_repository import InputRepository
from gracetree_engine.storage.job_repository import JobRepository

JOB_ID = "11111111-1111-4111-8111-111111111111"


def setup_job(tmp_path: Path) -> tuple[Path, InputRepository]:
    root = tmp_path / "GraceTreeData"
    JobRepository(root).get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id=JOB_ID,
        expected_work_path=root / "jobs" / "2026-06-20",
    )
    return root, InputRepository(root)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_partial_success_preserves_sources_and_records_only_success(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    valid = tmp_path / "voice.mp3"
    unsupported = tmp_path / "notes.exe"
    valid.write_bytes(b"audio")
    unsupported.write_bytes(b"binary")
    original_hash = digest(valid)

    results = repository.register_batch(JOB_ID, [valid, unsupported])

    assert [item["status"] for item in results] == ["registered", "rejected"]
    assert results[1]["errorCode"] == "UNSUPPORTED_TYPE"
    assert digest(valid) == original_hash
    managed = root / "jobs" / "2026-06-20" / "input" / "voice.mp3"
    assert managed.read_bytes() == b"audio"
    with sqlite3.connect(root / "studio.db") as connection:
        rows = connection.execute(
            "SELECT original_name, managed_path, status FROM job_inputs"
        ).fetchall()
    assert rows == [("voice.mp3", str(managed), "registered")]


def test_name_conflict_does_not_overwrite_existing_copy(tmp_path: Path) -> None:
    _, repository = setup_job(tmp_path)
    first = tmp_path / "one" / "voice.mp3"
    second = tmp_path / "two" / "voice.mp3"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    repository.register_batch(JOB_ID, [first])
    conflict = repository.register_batch(JOB_ID, [second])[0]

    assert conflict["status"] == "conflict"
    assert conflict["errorCode"] == "NAME_CONFLICT"
    assert Path(conflict["managedPath"]).read_bytes() == b"first"


def test_rejects_symlink_missing_and_managed_root_source_independently(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    real = tmp_path / "real.txt"
    link = tmp_path / "link.txt"
    real.write_text("real", encoding="utf-8")
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlinks unavailable")
    inside = root / "resources" / "inside.txt"
    inside.parent.mkdir()
    inside.write_text("inside", encoding="utf-8")

    results = repository.register_batch(
        JOB_ID, [link, tmp_path / "missing.txt", inside]
    )

    assert [item["errorCode"] for item in results] == [
        "SYMLINK_NOT_ALLOWED",
        "SOURCE_UNREADABLE",
        "SOURCE_INSIDE_MANAGED_ROOT",
    ]


def test_copy_failure_leaves_no_metadata_or_final_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "voice.mp3"
    source.write_bytes(b"audio")

    def fail_copy(_source: Path, _target: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(repository, "_copy_to_temp", fail_copy)
    result = repository.register_batch(JOB_ID, [source])[0]

    assert result["errorCode"] == "COPY_FAILED"
    assert not (root / "jobs" / "2026-06-20" / "input" / "voice.mp3").exists()
    with sqlite3.connect(root / "studio.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_inputs").fetchone() == (0,)


def test_fk_cascade_unique_and_index(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "voice.mp3"
    source.write_bytes(b"audio")
    repository.register_batch(JOB_ID, [source])

    with sqlite3.connect(root / "studio.db") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        indexes = connection.execute("PRAGMA index_list(job_inputs)").fetchall()
        connection.execute("DELETE FROM jobs WHERE id = ?", (JOB_ID,))
        count = connection.execute("SELECT COUNT(*) FROM job_inputs").fetchone()

    assert any(row[1] == "idx_job_inputs_job_id" for row in indexes)
    assert any(row[2] for row in indexes if row[1] != "idx_job_inputs_job_id")
    assert count == (0,)


def test_registered_metadata_is_restored_with_the_job(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    source.write_text("script", encoding="utf-8")
    repository.register_batch(JOB_ID, [source])

    job = JobRepository(root).get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="22222222-2222-4222-8222-222222222222",
        expected_work_path=root / "jobs" / "2026-06-20",
    )

    assert len(job["inputMetadata"]) == 1
    assert job["inputMetadata"][0]["originalName"] == "script.txt"
