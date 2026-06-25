"""
Minimal script validator for Story 1.6.
Story 2.2 will extend this with timing contracts and subtitle blocks.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Section markers in display order (title, scripture, prayer)
_SECTION_MARKERS: list[tuple[str, str]] = [
    ("[제목]", "title"),
    ("[말씀]", "scripture"),
    ("[기도]", "prayer"),
]

_MARKER_TO_KEY: dict[str, str] = {marker: key for marker, key in _SECTION_MARKERS}
_KEY_TO_MARKER: dict[str, str] = {key: marker for marker, key in _SECTION_MARKERS}
_KEY_TO_LABEL: dict[str, str] = {key: marker for marker, key in _SECTION_MARKERS}


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
    }


def _make_error(
    code: str,
    section: str | None,
    message: str,
) -> dict[str, Any]:
    return {"code": code, "section": section, "message": message}


def _parse_sections(text: str) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    """Parse section blocks from normalised text.

    Returns a mapping of section key → list of raw content strings (one per
    occurrence of the marker) and a list of error dicts for SECTION_DUPLICATE
    violations detected here.
    """
    # Split on marker lines; a marker line is a line whose stripped content is
    # exactly one of our markers.
    sections_raw: dict[str, list[str]] = {key: [] for _, key in _SECTION_MARKERS}
    errors: list[dict[str, Any]] = []

    known_markers = set(_MARKER_TO_KEY.keys())

    # Walk the lines, collecting content between markers.
    current_key: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_key is not None:
            sections_raw[current_key].append("\n".join(current_lines).strip())

    for line in text.splitlines():
        stripped = line.strip()
        if stripped in known_markers:
            _flush()
            current_key = _MARKER_TO_KEY[stripped]
            current_lines = []
        else:
            current_lines.append(line)

    _flush()

    # Detect duplicates.
    for _, key in _SECTION_MARKERS:
        if len(sections_raw[key]) > 1:
            label = _KEY_TO_LABEL[key]
            errors.append(
                _make_error(
                    "SECTION_DUPLICATE",
                    key,
                    f"{label} 구역이 여러 번 나타납니다.",
                )
            )

    return sections_raw, errors


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
    dict with keys: inputId, inputVersion, status, oneLiner, sections, errors.
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

    # Decode: strip UTF-8 BOM if present, normalise CRLF → LF.
    text = raw_bytes.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")

    # --- empty check ---
    if not text.strip():
        result["errors"].append(
            _make_error("FILE_EMPTY", None, "스크립트 파일이 비어 있습니다.")
        )
        return result

    # --- parse sections ---
    sections_raw, duplicate_errors = _parse_sections(text)
    result["errors"].extend(duplicate_errors)

    # Determine which keys have duplicates (they contribute SECTION_DUPLICATE,
    # not SECTION_MISSING / SECTION_EMPTY).
    duplicate_keys = {err["section"] for err in duplicate_errors}

    final_sections: dict[str, str | None] = {"title": None, "scripture": None, "prayer": None}

    for _, key in _SECTION_MARKERS:
        label = _KEY_TO_LABEL[key]
        occurrences = sections_raw[key]

        if key in duplicate_keys:
            # Content is ambiguous; leave section as None.
            continue

        if not occurrences:
            result["errors"].append(
                _make_error("SECTION_MISSING", key, f"{label} 구역이 없습니다.")
            )
            continue

        content = occurrences[0]  # exactly one occurrence
        if not content:
            result["errors"].append(
                _make_error("SECTION_EMPTY", key, f"{label} 구역에 내용이 없습니다.")
            )
            continue

        final_sections[key] = content

    result["sections"] = final_sections

    # --- oneLiner ---
    title_content = final_sections.get("title")
    if title_content:
        one_liner = re.sub(r"\s+", " ", title_content.replace("\n", " ")).strip()
        result["oneLiner"] = one_liner

    # --- status ---
    result["status"] = "valid" if not result["errors"] else "invalid"

    return result
