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
