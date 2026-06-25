from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

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
            "SELECT role, original_name, managed_path, status FROM job_inputs"
        ).fetchall()
    assert rows == [("voice", "voice.mp3", str(managed), "ready")]


def test_classifies_candidates_and_marks_every_duplicate_role_as_conflict(
    tmp_path: Path,
) -> None:
    _root, repository = setup_job(tmp_path)
    first_voice = tmp_path / "voice.first.mp3"
    second_voice = tmp_path / "VOICE.second.WAV"
    script = tmp_path / "notes.final.txt"
    unknown = tmp_path / "recording.mp3"
    for path in (first_voice, second_voice, script, unknown):
        path.write_bytes(b"content")

    repository.register_batch(JOB_ID, [first_voice, script, unknown])
    repository.register_batch(JOB_ID, [second_voice])

    inputs = repository.list_inputs(JOB_ID)
    assert [(item["role"], item["status"]) for item in inputs] == [
        ("voice", "conflict"),
        ("script", "ready"),
        ("unclassified", "unclassified"),
        ("voice", "conflict"),
    ]


def test_manual_role_assignment_recalculates_conflicts(tmp_path: Path) -> None:
    _root, repository = setup_job(tmp_path)
    first = tmp_path / "recording.mp3"
    second = tmp_path / "other.mp3"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    results = repository.register_batch(JOB_ID, [first, second])

    repository.assign_role(JOB_ID, results[0]["input"]["id"], "voice")
    inputs = repository.assign_role(JOB_ID, results[1]["input"]["id"], "voice")
    assert [item["status"] for item in inputs] == ["conflict", "conflict"]

    inputs = repository.assign_role(JOB_ID, results[1]["input"]["id"], "bgm")
    assert [(item["role"], item["status"]) for item in inputs] == [
        ("voice", "ready"),
        ("bgm", "ready"),
    ]


def test_rejects_unknown_manual_role(tmp_path: Path) -> None:
    _root, repository = setup_job(tmp_path)
    source = tmp_path / "recording.mp3"
    source.write_bytes(b"audio")
    result = repository.register_batch(JOB_ID, [source])[0]

    with pytest.raises(ValueError, match="role"):
        repository.assign_role(JOB_ID, result["input"]["id"], "other")


def test_remove_deletes_managed_copy_and_metadata_then_recalculates(
    tmp_path: Path,
) -> None:
    root, repository = setup_job(tmp_path)
    first = tmp_path / "voice.first.mp3"
    second = tmp_path / "voice.second.mp3"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    registered = repository.register_batch(JOB_ID, [first, second])

    inputs = repository.remove_input(JOB_ID, registered[1]["input"]["id"])

    assert [(item["role"], item["status"]) for item in inputs] == [
        ("voice", "ready")
    ]
    assert not (root / "jobs" / "2026-06-20" / "input" / second.name).exists()


def test_remove_rejects_stored_path_outside_managed_input_without_deleting(
    tmp_path: Path,
) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    outside = tmp_path / "outside.txt"
    source.write_text("script", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    registered = repository.register_batch(JOB_ID, [source])[0]
    with sqlite3.connect(root / "studio.db") as connection:
        connection.execute(
            "UPDATE job_inputs SET managed_path = ? WHERE id = ?",
            (str(outside), registered["input"]["id"]),
        )

    with pytest.raises(ValueError, match="managed input"):
        repository.remove_input(JOB_ID, registered["input"]["id"])

    assert outside.read_text(encoding="utf-8") == "outside"
    with sqlite3.connect(root / "studio.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_inputs").fetchone() == (1,)


def test_remove_file_failure_keeps_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    source.write_text("script", encoding="utf-8")
    registered = repository.register_batch(JOB_ID, [source])[0]
    managed = Path(registered["managedPath"])
    original_unlink = Path.unlink

    def fail_managed_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == managed:
            raise OSError("locked")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_managed_unlink)

    with pytest.raises(OSError, match="locked"):
        repository.remove_input(JOB_ID, registered["input"]["id"])

    assert managed.exists()
    with sqlite3.connect(root / "studio.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_inputs").fetchone() == (1,)


def test_replace_commits_only_after_new_copy_is_valid(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    old_source = tmp_path / "old" / "voice.mp3"
    new_source = tmp_path / "new" / "voice-new.mp3"
    old_source.parent.mkdir()
    new_source.parent.mkdir()
    old_source.write_bytes(b"old")
    new_source.write_bytes(b"new")
    registered = repository.register_batch(JOB_ID, [old_source])[0]

    inputs = repository.replace_input(
        JOB_ID, registered["input"]["id"], new_source
    )

    assert len(inputs) == 1
    assert inputs[0]["role"] == "voice"
    assert inputs[0]["originalName"] == "voice-new.mp3"
    assert Path(inputs[0]["managedPath"]).read_bytes() == b"new"
    assert not (root / "jobs" / "2026-06-20" / "input" / "voice.mp3").exists()


def test_replace_copy_failure_preserves_old_file_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, repository = setup_job(tmp_path)
    old_source = tmp_path / "old" / "voice.mp3"
    new_source = tmp_path / "new" / "voice-new.mp3"
    old_source.parent.mkdir()
    new_source.parent.mkdir()
    old_source.write_bytes(b"old")
    new_source.write_bytes(b"new")
    registered = repository.register_batch(JOB_ID, [old_source])[0]

    def fail_copy(
        _source: Path, _target: Path, _expected_stat: os.stat_result
    ) -> os.stat_result:
        raise OSError("disk full")

    monkeypatch.setattr(repository, "_copy_to_temp", fail_copy)

    with pytest.raises(OSError, match="disk full"):
        repository.replace_input(JOB_ID, registered["input"]["id"], new_source)

    managed = root / "jobs" / "2026-06-20" / "input" / "voice.mp3"
    assert managed.read_bytes() == b"old"
    with sqlite3.connect(root / "studio.db") as connection:
        row = connection.execute(
            "SELECT original_name, managed_path FROM job_inputs"
        ).fetchone()
    assert row == ("voice.mp3", str(managed))


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

    def fail_copy(
        _source: Path, _target: Path, _expected_stat: os.stat_result
    ) -> os.stat_result:
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
        unique_index = next(row for row in indexes if row[2] and row[3] == "u")
        unique_columns = connection.execute(
            f"PRAGMA index_info({unique_index[1]})"
        ).fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO job_inputs (
                    id, job_id, role, original_name, managed_path, status,
                    created_at, updated_at
                ) SELECT ?, job_id, role, original_name, managed_path, status,
                         created_at, updated_at
                  FROM job_inputs LIMIT 1
                """,
                ("22222222-2222-4222-8222-222222222222",),
            )
        connection.execute("DELETE FROM jobs WHERE id = ?", (JOB_ID,))
        count = connection.execute("SELECT COUNT(*) FROM job_inputs").fetchone()

    assert any(row[1] == "idx_job_inputs_job_id" for row in indexes)
    assert [row[2] for row in unique_columns] == ["job_id", "managed_path"]
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


def test_rejects_source_with_symlinked_parent(tmp_path: Path) -> None:
    _root, repository = setup_job(tmp_path)
    real_dir = tmp_path / "real"
    linked_dir = tmp_path / "linked"
    real_dir.mkdir()
    (real_dir / "script.txt").write_text("script", encoding="utf-8")
    try:
        linked_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    result = repository.register_batch(JOB_ID, [linked_dir / "script.txt"])[0]

    assert result["errorCode"] == "SYMLINK_NOT_ALLOWED"


def test_rejects_symlinked_managed_storage_directory(tmp_path: Path) -> None:
    root, repository = setup_job(tmp_path)
    input_dir = root / "jobs" / "2026-06-20" / "input"
    outside = tmp_path / "outside"
    outside.mkdir()
    input_dir.rmdir()
    try:
        input_dir.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    source = tmp_path / "script.txt"
    source.write_text("script", encoding="utf-8")

    with pytest.raises(ValueError, match="storage directory"):
        repository.register_batch(JOB_ID, [source])

    assert list(outside.iterdir()) == []


def test_source_change_during_copy_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    source.write_text("first", encoding="utf-8")
    original_copy = shutil.copyfileobj

    def mutate_after_copy(source_file: Any, target_file: Any) -> None:
        original_copy(source_file, target_file)
        source.write_text("other", encoding="utf-8")

    monkeypatch.setattr(shutil, "copyfileobj", mutate_after_copy)

    result = repository.register_batch(JOB_ID, [source])[0]

    assert result["errorCode"] == "COPY_FAILED"
    assert not (root / "jobs" / "2026-06-20" / "input" / "script.txt").exists()


def test_temp_cleanup_failure_does_not_change_committed_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    source.write_text("script", encoding="utf-8")
    original_unlink = Path.unlink

    def fail_temp_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.suffix == ".input-copy":
            raise OSError("cleanup failed")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temp_unlink)

    result = repository.register_batch(JOB_ID, [source])[0]

    assert result["status"] == "registered"


def test_restored_input_metadata_marks_missing_file_and_rejects_external_path(
    tmp_path: Path,
) -> None:
    root, repository = setup_job(tmp_path)
    source = tmp_path / "script.txt"
    source.write_text("script", encoding="utf-8")
    registered = repository.register_batch(JOB_ID, [source])[0]
    Path(registered["managedPath"]).unlink()

    missing = JobRepository(root).get_or_create_for_date(
        publish_date="2026-06-20",
        proposed_job_id="22222222-2222-4222-8222-222222222222",
        expected_work_path=root / "jobs" / "2026-06-20",
    )
    assert missing["pathState"] == "missing"

    with sqlite3.connect(root / "studio.db") as connection:
        connection.execute(
            "UPDATE job_inputs SET managed_path = ? WHERE job_id = ?",
            (str(tmp_path / "external.txt"), JOB_ID),
        )

    with pytest.raises(ValueError, match="managed input directory"):
        JobRepository(root).get_or_create_for_date(
            publish_date="2026-06-20",
            proposed_job_id="22222222-2222-4222-8222-222222222222",
            expected_work_path=root / "jobs" / "2026-06-20",
        )
