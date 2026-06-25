from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALID_COMMAND = json.loads(
    (ROOT / "packages" / "contracts" / "fixtures" / "valid-check-health.json").read_text(
        encoding="utf-8"
    )
)


def run_engine(
    stdin: str, *, managed_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "engine")
    if managed_root is not None:
        environment["GRACETREE_MANAGED_ROOT"] = str(managed_root)
    return subprocess.run(
        [sys.executable, "-m", "gracetree_engine"],
        cwd=ROOT,
        env=environment,
        input=stdin,
        capture_output=True,
        check=False,
        text=True,
        timeout=5,
    )


def test_long_running_process_handles_multiple_commands() -> None:
    second = {**VALID_COMMAND}
    second["jobId"] = "health-check-2"

    result = run_engine(json.dumps(VALID_COMMAND) + "\n" + json.dumps(second) + "\n")

    assert result.returncode == 0
    assert result.stderr == ""
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [event["jobId"] for event in events] == ["health-check-1", "health-check-2"]
    assert all(event["type"] == "health_checked" for event in events)


def test_invalid_input_stays_out_of_stdout() -> None:
    result = run_engine("{not-json}\n")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "INVALID_COMMAND" in result.stderr


def test_schema_invalid_input_stays_out_of_stdout_and_logs_no_value() -> None:
    invalid = {
        **VALID_COMMAND,
        "timestamp": "sentinel-secret-not-a-date",
    }

    result = run_engine(json.dumps(invalid) + "\n")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "INVALID_COMMAND" in result.stderr
    assert "sentinel-secret" not in result.stderr


def test_get_or_create_job_round_trip(tmp_path: Path) -> None:
    job_id = "11111111-1111-4111-8111-111111111111"
    managed_root = tmp_path / "GraceTreeData"
    command = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": str(managed_root),
            "workPath": str(managed_root / "jobs" / "2026-06-20"),
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=managed_root)

    assert result.returncode == 0
    assert result.stderr == ""
    event = json.loads(result.stdout)
    assert event["type"] == "job_loaded"
    assert event["jobId"] == job_id
    assert event["payload"]["job"]["id"] == job_id
    assert event["payload"]["job"]["publishDate"] == "2026-06-20"


def test_rejects_noncanonical_managed_root_without_creating_storage(
    tmp_path: Path,
) -> None:
    relative_root = f"relative-{tmp_path.name}/GraceTreeData"
    command = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": "11111111-1111-4111-8111-111111111111",
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": relative_root,
            "workPath": f"{relative_root}/jobs/2026-06-20",
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=tmp_path / "approved")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "INTERNAL_EVENT_INVALID" in result.stderr
    assert not (ROOT / relative_root).exists()


def test_sqlite_error_is_reported_without_traceback(tmp_path: Path) -> None:
    managed_root = tmp_path / "GraceTreeData"
    managed_root.mkdir()
    (managed_root / "studio.db").mkdir()
    command = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": "11111111-1111-4111-8111-111111111111",
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": str(managed_root),
            "workPath": str(managed_root / "jobs" / "2026-06-20"),
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=managed_root)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "STORAGE_ERROR: managed storage is unavailable\n"
    assert "Traceback" not in result.stderr


def test_rejects_command_root_that_differs_from_the_approved_root(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved" / "GraceTreeData"
    command_root = tmp_path / "unapproved" / "GraceTreeData"
    command = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": "11111111-1111-4111-8111-111111111111",
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": str(command_root),
            "workPath": str(command_root / "jobs" / "2026-06-20"),
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=approved_root)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "INTERNAL_EVENT_INVALID" in result.stderr
    assert not command_root.exists()


def test_register_input_files_round_trip_preserves_partial_success(tmp_path: Path) -> None:
    managed_root = tmp_path / "GraceTreeData"
    source = tmp_path / "voice.mp3"
    unsupported = tmp_path / "bad.exe"
    source.write_bytes(b"audio")
    unsupported.write_bytes(b"binary")
    job_id = "11111111-1111-4111-8111-111111111111"
    create = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": str(managed_root),
            "workPath": str(managed_root / "jobs" / "2026-06-20"),
        },
    }
    register = {
        "protocolVersion": 1,
        "type": "register_input_files",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:01.000Z",
        "payload": {
            "sourcePaths": [str(source), str(unsupported)],
            "managedRoot": str(managed_root),
        },
    }

    result = run_engine(
        json.dumps(create) + "\n" + json.dumps(register) + "\n",
        managed_root=managed_root,
    )

    assert result.returncode == 0
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[1]["type"] == "input_files_registered"
    assert [item["status"] for item in events[1]["payload"]["results"]] == [
        "registered",
        "rejected",
    ]
    assert source.read_bytes() == b"audio"


def test_validate_script_rejects_managed_path_outside_approved_root(tmp_path: Path) -> None:
    """managedPath pointing outside GRACETREE_MANAGED_ROOT must be rejected (path traversal)."""
    managed_root = tmp_path / "GraceTreeData"
    managed_root.mkdir(parents=True)
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("sensitive", encoding="utf-8")

    command = {
        "protocolVersion": 1,
        "type": "validate_script",
        "jobId": "11111111-1111-4111-8111-111111111111",
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "inputId": "22222222-2222-4222-8222-222222222222",
            "inputVersion": "v1",
            "managedPath": str(outside_file),
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=managed_root)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "INTERNAL_EVENT_INVALID" in result.stderr


def test_validate_script_returns_valid_for_script_inside_root(tmp_path: Path) -> None:
    managed_root = tmp_path / "GraceTreeData"
    script_dir = managed_root / "jobs" / "2026-06-20" / "input"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "script.txt"
    script_file.write_text(
        "[제목]\n제목입니다\n\n[말씀]\n말씀내용\n\n[기도]\n기도내용\n",
        encoding="utf-8",
    )

    command = {
        "protocolVersion": 1,
        "type": "validate_script",
        "jobId": "11111111-1111-4111-8111-111111111111",
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "inputId": "22222222-2222-4222-8222-222222222222",
            "inputVersion": "v1",
            "managedPath": str(script_file),
        },
    }

    result = run_engine(json.dumps(command) + "\n", managed_root=managed_root)

    assert result.returncode == 0
    assert result.stderr == ""
    event = json.loads(result.stdout)
    assert event["type"] == "script_validated"
    assert event["payload"]["status"] == "valid"


def test_manage_input_round_trip_assigns_role_and_removes_copy(tmp_path: Path) -> None:
    managed_root = tmp_path / "GraceTreeData"
    source = tmp_path / "recording.mp3"
    source.write_bytes(b"audio")
    job_id = "11111111-1111-4111-8111-111111111111"
    create = {
        "protocolVersion": 1,
        "type": "get_or_create_job",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:00.000Z",
        "payload": {
            "publishDate": "2026-06-20",
            "managedRoot": str(managed_root),
            "workPath": str(managed_root / "jobs" / "2026-06-20"),
        },
    }
    register = {
        "protocolVersion": 1,
        "type": "register_input_files",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:01.000Z",
        "payload": {
            "sourcePaths": [str(source)],
            "managedRoot": str(managed_root),
        },
    }
    registered = run_engine(
        json.dumps(create) + "\n" + json.dumps(register) + "\n",
        managed_root=managed_root,
    )
    input_value = json.loads(registered.stdout.splitlines()[1])["payload"]["results"][0][
        "input"
    ]
    assign = {
        "protocolVersion": 1,
        "type": "manage_input",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:02.000Z",
        "payload": {
            "action": "assign_role",
            "inputId": input_value["id"],
            "role": "voice",
            "managedRoot": str(managed_root),
        },
    }
    assigned = run_engine(json.dumps(assign) + "\n", managed_root=managed_root)
    assigned_event = json.loads(assigned.stdout)
    assert assigned_event["payload"]["inputs"][0]["role"] == "voice"
    assert assigned_event["payload"]["inputs"][0]["status"] == "ready"

    remove = {
        "protocolVersion": 1,
        "type": "manage_input",
        "jobId": job_id,
        "timestamp": "2026-06-20T00:00:03.000Z",
        "payload": {
            "action": "remove",
            "inputId": input_value["id"],
            "managedRoot": str(managed_root),
        },
    }
    removed = run_engine(json.dumps(remove) + "\n", managed_root=managed_root)

    assert json.loads(removed.stdout)["payload"]["inputs"] == []
    assert not Path(input_value["managedPath"]).exists()
