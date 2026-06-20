from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from gracetree_engine.cli import COMMAND_VALIDATOR, EVENT_VALIDATOR

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "packages" / "contracts" / "fixtures"


def fixture(name: str) -> object:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_accepts_valid_command_and_event() -> None:
    COMMAND_VALIDATOR.validate(fixture("valid-check-health.json"))
    EVENT_VALIDATOR.validate(fixture("valid-health-checked.json"))
    COMMAND_VALIDATOR.validate(fixture("valid-get-or-create-job.json"))
    EVENT_VALIDATOR.validate(fixture("valid-job-loaded.json"))


@pytest.mark.parametrize(
    "name",
    [
        "invalid-command-missing-job-id.json",
        "invalid-command-wrong-version.json",
        "invalid-command-unknown-type.json",
        "invalid-command-bad-timestamp.json",
        "invalid-command-non-utc-timestamp.json",
    ],
)
def test_rejects_invalid_commands(name: str) -> None:
    with pytest.raises(ValidationError):
        COMMAND_VALIDATOR.validate(fixture(name))
