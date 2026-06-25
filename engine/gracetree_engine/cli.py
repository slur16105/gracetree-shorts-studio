from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .storage.job_repository import JobRepository, get_completed_jobs
from .inputs.input_service import InputService
from .storage.resource_repository import get_all_resources
from .inputs.resource_service import update_resource
from .storage.migrations import apply_migrations, connect_database

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "packages" / "contracts"


def _load_schema(name: str) -> dict[str, Any]:
    with (CONTRACTS_DIR / "schemas" / name).open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    Draft202012Validator.check_schema(schema)
    return schema


FORMAT_CHECKER = FormatChecker()
COMMAND_VALIDATOR = Draft202012Validator(
    _load_schema("engine-command.schema.json"),
    format_checker=FORMAT_CHECKER,
)
EVENT_VALIDATOR = Draft202012Validator(
    _load_schema("engine-event.schema.json"),
    format_checker=FORMAT_CHECKER,
)


def _health_checked(job_id: str) -> dict[str, Any]:
    event = {
        "protocolVersion": 1,
        "type": "health_checked",
        "jobId": job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        ),
        "payload": {"status": "ok"},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _job_loaded(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value:
        raise ValueError("approved managed root is unavailable")
    approved_root = Path(approved_root_value)
    command_root = Path(payload["managedRoot"])
    if command_root != approved_root:
        raise ValueError("command managed root does not match the approved root")
    repository = JobRepository(approved_root)
    job = repository.get_or_create_for_date(
        publish_date=payload["publishDate"],
        proposed_job_id=command["jobId"],
        expected_work_path=Path(payload["workPath"]),
    )
    event = {
        "protocolVersion": 1,
        "type": "job_loaded",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": {"job": job},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _input_files_registered(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value or Path(payload["managedRoot"]) != Path(approved_root_value):
        raise ValueError("command managed root does not match the approved root")
    service = InputService(Path(approved_root_value))
    event = {
        "protocolVersion": 1,
        "type": "input_files_registered",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": service.register(command["jobId"], payload["sourcePaths"]),
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _input_state_changed(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value or Path(payload["managedRoot"]) != Path(approved_root_value):
        raise ValueError("command managed root does not match the approved root")
    inputs = InputService(Path(approved_root_value)).manage(command["jobId"], payload)
    event = {
        "protocolVersion": 1,
        "type": "input_state_changed",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": {"inputs": inputs},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _resources_loaded(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value or Path(payload["managedRoot"]) != Path(approved_root_value):
        raise ValueError("command managed root does not match the approved root")
    approved_root = Path(approved_root_value)
    database_path = approved_root / "studio.db"
    apply_migrations(database_path)
    with connect_database(database_path) as conn:
        resources = get_all_resources(conn)
    event = {
        "protocolVersion": 1,
        "type": "resources_loaded",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": {"resources": resources},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _resource_updated(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value or Path(payload["managedRoot"]) != Path(approved_root_value):
        raise ValueError("command managed root does not match the approved root")
    approved_root = Path(approved_root_value)
    database_path = approved_root / "studio.db"
    apply_migrations(database_path)
    with connect_database(database_path) as conn:
        result = update_resource(
            conn,
            managed_root=str(approved_root),
            resource_type=payload["resourceType"],
            source_path=payload["sourcePath"],
        )
    event = {
        "protocolVersion": 1,
        "type": "resource_updated",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": result,
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _completed_jobs_listed(command: dict[str, Any]) -> dict[str, Any]:
    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value or Path(payload["managedRoot"]) != Path(approved_root_value):
        raise ValueError("command managed root does not match the approved root")
    approved_root = Path(approved_root_value)
    database_path = approved_root / "studio.db"
    apply_migrations(database_path)
    with connect_database(database_path) as conn:
        jobs = get_completed_jobs(conn)
    event = {
        "protocolVersion": 1,
        "type": "completed_jobs_listed",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": {"jobs": jobs},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _script_validated(command: dict[str, Any]) -> dict[str, Any]:
    from gracetree_engine.scripts.validator import validate_script

    payload = command["payload"]
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value:
        raise ValueError("approved managed root is unavailable")
    approved_root = Path(approved_root_value)
    managed_path = Path(payload["managedPath"])
    try:
        if not managed_path.resolve().is_relative_to(approved_root.resolve()):
            raise ValueError("managedPath escapes the approved managed root")
    except ValueError:
        raise
    result = validate_script(
        managed_path=payload["managedPath"],
        input_id=payload["inputId"],
        input_version=payload["inputVersion"],
    )
    event = {
        "protocolVersion": 1,
        "type": "script_validated",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": result,
    }
    EVENT_VALIDATOR.validate(event)
    return event


def run(stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    had_error = False

    for raw_line in stdin:
        try:
            command = json.loads(raw_line)
            COMMAND_VALIDATOR.validate(command)
        except json.JSONDecodeError as error:
            had_error = True
            print(
                f"INVALID_COMMAND: malformed JSON at line {error.lineno}",
                file=stderr,
                flush=True,
            )
            continue
        except ValidationError as error:
            had_error = True
            schema_path = ".".join(str(part) for part in error.schema_path)
            print(
                f"INVALID_COMMAND: schema path {schema_path}",
                file=stderr,
                flush=True,
            )
            continue

        try:
            if command["type"] == "check_health":
                event = _health_checked(command["jobId"])
            elif command["type"] == "get_or_create_job":
                event = _job_loaded(command)
            elif command["type"] == "register_input_files":
                event = _input_files_registered(command)
            elif command["type"] == "validate_script":
                event = _script_validated(command)
            elif command["type"] == "get_resources":
                event = _resources_loaded(command)
            elif command["type"] == "update_resource":
                event = _resource_updated(command)
            elif command["type"] == "list_completed_jobs":
                event = _completed_jobs_listed(command)
            else:
                event = _input_state_changed(command)
        except (ValidationError, ValueError) as error:
            if isinstance(error, ValidationError):
                schema_path = ".".join(str(part) for part in error.schema_path)
            else:
                schema_path = "job_request"
            print(
                f"INTERNAL_EVENT_INVALID: schema path {schema_path}",
                file=stderr,
                flush=True,
            )
            return 1
        except (OSError, sqlite3.Error):
            print(
                "STORAGE_ERROR: managed storage is unavailable",
                file=stderr,
                flush=True,
            )
            return 1

        stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
        stdout.flush()

    return 1 if had_error else 0


def main() -> int:
    return run(sys.stdin, sys.stdout, sys.stderr)
