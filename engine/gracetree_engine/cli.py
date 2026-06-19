from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

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
            event = _health_checked(command["jobId"])
        except ValidationError as error:
            schema_path = ".".join(str(part) for part in error.schema_path)
            print(
                f"INTERNAL_EVENT_INVALID: schema path {schema_path}",
                file=stderr,
                flush=True,
            )
            return 1

        stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
        stdout.flush()

    return 1 if had_error else 0


def main() -> int:
    return run(sys.stdin, sys.stdout, sys.stderr)
