"""Script validator (Story 1.6) extended with AST output (Story 2.2).

File I/O and encoding handling live here; all text parsing is delegated to
parser.parse_script() to avoid a second parse pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .parser import _make_error, parse_script as _parse_script


def _empty_result(
    input_id: str,
    input_version: str,
) -> dict[str, Any]:
    return {
        "inputId": input_id,
        "inputVersion": input_version,
        "status": "invalid",
        "oneLiner": None,
        "sections": {"title": None, "scripture": None, "prayer": None},
        "errors": [],
        "ast": None,
    }


def validate_script(
    managed_path: str,
    input_id: str,
    input_version: str,
) -> dict[str, Any]:
    """Validate a script file and return a ScriptValidationDto-shaped dict.

    Parameters
    ----------
    managed_path:
        Absolute path to the managed script file.
    input_id:
        UUID string of the input record.
    input_version:
        Opaque version token (e.g. SHA-256 digest) used for cache busting.

    Returns
    -------
    dict with keys: inputId, inputVersion, status, oneLiner, sections, errors, ast.
    """
    result = _empty_result(input_id, input_version)

    # --- read file ---
    path = Path(managed_path)
    try:
        raw_bytes = path.read_bytes()
    except OSError:
        result["errors"].append(
            _make_error("FILE_UNREADABLE", None, "스크립트 파일을 읽을 수 없습니다.")
        )
        return result

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        result["errors"].append(
            _make_error("FILE_UNREADABLE", None, "스크립트 파일을 읽을 수 없습니다.")
        )
        return result

    # --- empty check ---
    if not text.strip():
        result["errors"].append(
            _make_error("FILE_EMPTY", None, "스크립트 파일이 비어 있습니다.")
        )
        return result

    # --- parse (single pass via parser) ---
    parsed = _parse_script(text)
    result["status"] = parsed["status"]
    result["errors"] = parsed["errors"]
    result["sections"] = parsed["sections"]
    result["oneLiner"] = parsed["oneLiner"]
    result["ast"] = parsed["ast"]

    return result
