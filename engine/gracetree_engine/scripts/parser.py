"""Story 2.2: Script parser producing AST with subtitle blocks.

parse_script() accepts raw text (not a file path) and returns a deterministic
dict with {status, ast, errors, sections, oneLiner}.  Same bytes → same output;
no platform-clock or locale dependency.
"""
from __future__ import annotations

import re
from typing import Any

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # type: ignore[no-redef]

_SECTION_MARKERS: list[tuple[str, str]] = [
    ("[제목]", "title"),
    ("[말씀]", "scripture"),
    ("[기도]", "prayer"),
]
_MARKER_TO_KEY: dict[str, str] = {m: k for m, k in _SECTION_MARKERS}
_KEY_TO_LABEL: dict[str, str] = {k: m for m, k in _SECTION_MARKERS}


class SubtitleBlock(TypedDict):
    """Typed shape for a subtitle block dict returned by parse_script."""
    index: int
    text: str
    lines: list[str]


def _normalize(text: str) -> str:
    return text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")


def _strip_surrounding_blanks(lines: list[str]) -> list[str]:
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return lines


def _split_subtitle_blocks(lines: list[str]) -> list[SubtitleBlock]:
    blocks: list[SubtitleBlock] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append(SubtitleBlock(
                    index=len(blocks),
                    text="\n".join(current),
                    lines=list(current),
                ))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(SubtitleBlock(
            index=len(blocks),
            text="\n".join(current),
            lines=list(current),
        ))
    return blocks


def _make_error(code: str, section: str | None, message: str) -> dict[str, Any]:
    return {"code": code, "section": section, "message": message}


def parse_script(text: str) -> dict[str, Any]:
    """Parse raw script text and return structured result.

    Returns dict with keys:
        status    – "valid" | "invalid"
        ast       – ScriptAstDto dict when valid, None when invalid
        errors    – list of ScriptSectionError dicts
        sections  – partial section content (present for both valid and invalid)
        oneLiner  – title collapsed to one line, or None
    """
    text = _normalize(text)
    errors: list[dict[str, Any]] = []

    sections_lines: dict[str, list[list[str]]] = {k: [] for _, k in _SECTION_MARKERS}
    known_markers = set(_MARKER_TO_KEY.keys())
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped in known_markers:
            if current_key is not None:
                sections_lines[current_key].append(list(current_lines))
            current_key = _MARKER_TO_KEY[stripped]
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections_lines[current_key].append(list(current_lines))

    # Detect duplicates.
    duplicate_keys: set[str] = set()
    for _, key in _SECTION_MARKERS:
        if len(sections_lines[key]) > 1:
            label = _KEY_TO_LABEL[key]
            errors.append(_make_error("SECTION_DUPLICATE", key, f"{label} 구역이 여러 번 나타납니다."))
            duplicate_keys.add(key)

    # Extract each section; build partial sections even for invalid scripts.
    final_sections: dict[str, str | None] = {"title": None, "scripture": None, "prayer": None}
    prayer_lines: list[str] = []

    for _, key in _SECTION_MARKERS:
        label = _KEY_TO_LABEL[key]
        occurrences = sections_lines[key]

        if key in duplicate_keys:
            continue

        if not occurrences:
            errors.append(_make_error("SECTION_MISSING", key, f"{label} 구역이 없습니다."))
            continue

        raw_lines = occurrences[0]

        if key in ("title", "scripture"):
            content = "\n".join(raw_lines).strip()
            if not content:
                errors.append(_make_error("SECTION_EMPTY", key, f"{label} 구역에 내용이 없습니다."))
                continue
            final_sections[key] = content
        else:  # prayer — preserve per-line whitespace, strip surrounding blanks only
            cleaned = _strip_surrounding_blanks(list(raw_lines))
            if not any(ln.strip() for ln in cleaned):
                errors.append(_make_error("SECTION_EMPTY", key, f"{label} 구역에 내용이 없습니다."))
                continue
            final_sections["prayer"] = "\n".join(cleaned)
            prayer_lines = cleaned

    # Compute oneLiner from title (even when overall status is invalid).
    one_liner: str | None = None
    if final_sections["title"]:
        one_liner = re.sub(r"\s+", " ", final_sections["title"].replace("\n", " ")).strip()

    if errors:
        return {
            "status": "invalid",
            "ast": None,
            "errors": errors,
            "sections": final_sections,
            "oneLiner": one_liner,
        }

    ast = {
        "title": final_sections["title"],
        "scripture": final_sections["scripture"],
        "subtitleBlocks": _split_subtitle_blocks(prayer_lines),
    }
    return {
        "status": "valid",
        "ast": ast,
        "errors": [],
        "sections": final_sections,
        "oneLiner": one_liner,
    }
