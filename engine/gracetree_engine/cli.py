from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .storage.job_repository import JobRepository, get_completed_jobs
from .inputs.input_service import InputService
from .storage.resource_repository import get_all_resources
from .inputs.resource_service import update_resource
from .storage.migrations import apply_migrations, connect_database
from .resource_resolver import contracts_dir as _contracts_dir

CONTRACTS_DIR = _contracts_dir()


def _load_schema(name: str) -> dict[str, Any]:
    schema_path = CONTRACTS_DIR / "schemas" / name
    try:
        with schema_path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
    except OSError as exc:
        raise RuntimeError(
            f"Engine schema file not found: {schema_path}\n"
            "Ensure the contracts package is present (source tree) or "
            "that this is a complete PyInstaller bundle."
        ) from exc
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


def _job_cancelled(command: dict[str, Any]) -> dict[str, Any]:
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value:
        raise ValueError("approved managed root is unavailable")
    approved_root = Path(approved_root_value)
    database_path = approved_root / "studio.db"
    apply_migrations(database_path)
    from .jobs.attempt_repository import AttemptRepository
    attempt_id = command["payload"]["attemptId"]
    AttemptRepository(database_path).cancel_attempt(attempt_id=attempt_id)
    event = {
        "protocolVersion": 1,
        "type": "job_cancelled",
        "jobId": command["jobId"],
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "payload": {"attemptId": attempt_id},
    }
    EVENT_VALIDATOR.validate(event)
    return event


def _handle_start_job_streaming(
    command: dict[str, Any],
    stdout: TextIO,
    lock: threading.Lock,
    cancel_event: threading.Event,
) -> None:
    """start_job을 처리하며 여러 이벤트를 thread-safe하게 stdout에 기록한다."""
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value:
        raise ValueError("approved managed root is unavailable")

    def _emit(event: dict[str, Any]) -> None:
        EVENT_VALIDATOR.validate(event)
        with lock:
            stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
            stdout.flush()

    from .jobs.orchestrator import start_job as _start_job
    _start_job(
        command=command,
        approved_root=Path(approved_root_value),
        emit=_emit,
        cancel_event=cancel_event,
    )


def _startup_reconciliation() -> None:
    """비정상 종료 후 running 상태 attempt를 interrupted로 전환한다."""
    approved_root_value = os.environ.get("GRACETREE_MANAGED_ROOT")
    if not approved_root_value:
        return
    database_path = Path(approved_root_value) / "studio.db"
    if not database_path.is_file():
        return
    try:
        from .jobs.attempt_repository import AttemptRepository
        from .jobs.session_cleanup import sweep_session_workspaces
        apply_migrations(database_path)
        repo = AttemptRepository(database_path)
        repo.reconcile_pending_artifacts()
        repo.interrupt_running_attempts()
        # 세션 한정 작업 데이터 정리: 이전 세션의 jobs/ 작업 폴더와 행을 비운다.
        # (resources/와 studio.db 파일은 보존. 완성 영상은 다운로드 폴더 사본이 남는다.)
        # 앱 실행당 한 번만 정리하도록 main이 첫 spawn에만 이 환경변수를 설정한다.
        # 엔진이 세션 도중 crash로 재시작돼도(respawn) 현재 작업이 지워지지 않게 한다.
        if os.environ.get("GRACETREE_SWEEP_SESSION") == "1":
            sweep_session_workspaces(Path(approved_root_value))
    except Exception as exc:
        print(f"STARTUP_RECONCILIATION_FAILED: {exc}", file=sys.stderr, flush=True)


def run(stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    _startup_reconciliation()
    had_error = False
    lock = threading.Lock()
    # job_id -> cancel_event; populated while start_job thread is active
    active_cancel_events: dict[str, threading.Event] = {}

    def _write_event(event: dict[str, Any]) -> None:
        EVENT_VALIDATOR.validate(event)
        with lock:
            stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
            stdout.flush()

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
            if command["type"] == "start_job":
                job_id = command["jobId"]
                cancel_event = threading.Event()
                with lock:
                    active_cancel_events[job_id] = cancel_event

                def _run_start_job(cmd=command, jid=job_id, ce=cancel_event) -> None:
                    try:
                        _handle_start_job_streaming(cmd, stdout, lock, ce)
                    except Exception as exc:
                        print(
                            f"UNHANDLED_ERROR: start_job thread failed: {exc}",
                            file=stderr,
                            flush=True,
                        )
                        # Emit job_failed so the stream listener resolves immediately
                        # instead of waiting the full 10-minute timeout.
                        try:
                            import uuid as _uuid
                            _now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                            _err_event = {
                                "protocolVersion": 1,
                                "type": "job_failed",
                                "jobId": jid,
                                "timestamp": _now,
                                "payload": {
                                    "attemptId": str(_uuid.uuid4()),
                                    "errorCode": "PROCESS_FAILED",
                                    "stageId": None,
                                    "recoverable": False,
                                    "details": str(exc),
                                },
                            }
                            with lock:
                                stdout.write(json.dumps(_err_event, separators=(",", ":")) + "\n")
                                stdout.flush()
                        except Exception:
                            pass
                    finally:
                        with lock:
                            active_cancel_events.pop(jid, None)

                t = threading.Thread(target=_run_start_job, daemon=True)
                t.start()
                continue

            elif command["type"] == "cancel_job":
                job_id = command["jobId"]
                with lock:
                    cancel_event = active_cancel_events.get(job_id)
                if cancel_event is not None:
                    cancel_event.set()
                    # Immediately acknowledge so the IPC caller doesn't wait 30 s.
                    # If the generation thread also emits job_cancelled the duplicate
                    # is silently absorbed by engine-client.ts routing.
                    now_ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    event = {
                        "protocolVersion": 1,
                        "type": "job_cancelled",
                        "jobId": command["jobId"],
                        "timestamp": now_ts,
                        "payload": {"attemptId": command["payload"]["attemptId"]},
                    }
                else:
                    # Job already completed or never started — acknowledge directly
                    event = _job_cancelled(command)

            elif command["type"] == "check_health":
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

        _write_event(event)

    return 1 if had_error else 0


def main() -> int:
    return run(sys.stdin, sys.stdout, sys.stderr)
