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


def run_engine(stdin: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "engine")
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

    result = run_engine(json.dumps(command) + "\n")

    assert result.returncode == 0
    assert result.stderr == ""
    event = json.loads(result.stdout)
    assert event["type"] == "job_loaded"
    assert event["jobId"] == job_id
    assert event["payload"]["job"]["id"] == job_id
    assert event["payload"]["job"]["publishDate"] == "2026-06-20"
