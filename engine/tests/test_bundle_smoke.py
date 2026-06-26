"""Story 2.12: Smoke tests that validate the CLI works end-to-end in dev mode.

These tests simulate what the packaged binary executes: the run() loop reads
JSON commands from stdin, resolves resources via resource_resolver, and emits
events to stdout. A clean Python-missing environment test requires building the
onedir bundle separately (see scripts/build-engine.mjs).
"""
from __future__ import annotations

import io
import json

import pytest

from gracetree_engine.cli import run

_HEALTH_COMMAND = {
    "protocolVersion": 1,
    "type": "check_health",
    "jobId": "smoke-001",
    "timestamp": "2026-06-26T00:00:00.000Z",
    "payload": {},
}


def _run_commands(*commands: dict) -> tuple[int, list[dict]]:
    """Run one or more commands through the CLI loop; return (exit_code, events)."""
    stdin = io.StringIO("\n".join(json.dumps(c) for c in commands) + "\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = run(stdin, stdout, stderr)
    events = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
    return code, events


def test_health_check_returns_ok():
    code, events = _run_commands(_HEALTH_COMMAND)
    assert code == 0
    assert len(events) == 1
    assert events[0]["type"] == "health_checked"
    assert events[0]["payload"]["status"] == "ok"
    assert events[0]["jobId"] == "smoke-001"


def test_health_check_event_schema_valid():
    """health_checked event must pass the built-in EVENT_VALIDATOR."""
    from gracetree_engine.cli import EVENT_VALIDATOR

    _, events = _run_commands({**_HEALTH_COMMAND, "jobId": "smoke-002"})
    EVENT_VALIDATOR.validate(events[0])


def test_resource_resolver_contracts_reachable():
    """CLI can load schemas (resource_resolver works in dev mode)."""
    from gracetree_engine.resource_resolver import contracts_dir
    schemas = contracts_dir() / "schemas"
    assert (schemas / "engine-command.schema.json").is_file()
    assert (schemas / "engine-event.schema.json").is_file()


def test_resource_resolver_migrations_reachable():
    """Migrations dir resolves and contains SQL files."""
    from gracetree_engine.resource_resolver import migrations_dir
    sql_files = list(migrations_dir().glob("*.sql"))
    assert len(sql_files) >= 5


def test_invalid_json_returns_error_and_continues():
    """CLI must survive malformed JSON and still exit with had_error=True."""
    stdin = io.StringIO("not-json\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = run(stdin, stdout, stderr)
    assert code == 1
    assert "INVALID_COMMAND" in stderr.getvalue()
