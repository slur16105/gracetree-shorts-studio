"""Tests for gracetree_engine.scripts.validator."""
from __future__ import annotations

from pathlib import Path

import pytest

from gracetree_engine.scripts.validator import validate_script

INPUT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INPUT_VERSION = "sha256:deadbeef"

VALID_SCRIPT = """\
[제목]
은혜의 나무 쇼츠

[말씀]
요한복음 3:16 하나님이 세상을 이처럼 사랑하사
독생자를 주셨으니

[기도]
주님, 감사합니다.
"""


def _write(tmp_path: Path, content: str, name: str = "script.txt") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_script_returns_valid_status(tmp_path: Path) -> None:
    p = _write(tmp_path, VALID_SCRIPT)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "valid"
    assert result["errors"] == []
    assert result["inputId"] == INPUT_ID
    assert result["inputVersion"] == INPUT_VERSION


def test_valid_script_sections_content(tmp_path: Path) -> None:
    p = _write(tmp_path, VALID_SCRIPT)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["sections"]["title"] == "은혜의 나무 쇼츠"
    assert "요한복음" in result["sections"]["scripture"]
    assert "감사합니다" in result["sections"]["prayer"]


def test_one_liner_single_line_title(tmp_path: Path) -> None:
    p = _write(tmp_path, VALID_SCRIPT)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["oneLiner"] == "은혜의 나무 쇼츠"


def test_multi_line_title_joined_with_space(tmp_path: Path) -> None:
    content = "[제목]\n첫째 줄\n둘째 줄\n셋째 줄\n\n[말씀]\n말씀 내용\n\n[기도]\n기도문\n"
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "valid"
    assert result["oneLiner"] == "첫째 줄 둘째 줄 셋째 줄"


# ---------------------------------------------------------------------------
# Encoding / line-ending edge cases
# ---------------------------------------------------------------------------


def test_utf8_bom_file_parses_correctly(tmp_path: Path) -> None:
    bom = b"\xef\xbb\xbf"
    raw = bom + VALID_SCRIPT.encode("utf-8")
    p = tmp_path / "script_bom.txt"
    p.write_bytes(raw)

    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "valid"
    assert result["sections"]["title"] == "은혜의 나무 쇼츠"


def test_crlf_line_endings_parse_correctly(tmp_path: Path) -> None:
    crlf_content = VALID_SCRIPT.replace("\n", "\r\n")
    p = tmp_path / "script_crlf.txt"
    p.write_bytes(crlf_content.encode("utf-8"))

    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "valid"
    assert result["sections"]["title"] == "은혜의 나무 쇼츠"


# ---------------------------------------------------------------------------
# File-level errors
# ---------------------------------------------------------------------------


def test_missing_file_returns_file_unreadable(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.txt"
    result = validate_script(str(missing), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["code"] == "FILE_UNREADABLE"
    assert result["errors"][0]["section"] is None


def test_empty_file_returns_file_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_bytes(b"")
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["code"] == "FILE_EMPTY"
    assert result["errors"][0]["section"] is None


def test_whitespace_only_file_returns_file_empty(tmp_path: Path) -> None:
    p = tmp_path / "spaces.txt"
    p.write_text("   \n\n\t  \n", encoding="utf-8")
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    codes = [e["code"] for e in result["errors"]]
    assert "FILE_EMPTY" in codes


# ---------------------------------------------------------------------------
# SECTION_MISSING
# ---------------------------------------------------------------------------


def test_missing_scripture_section(tmp_path: Path) -> None:
    content = "[제목]\n제목입니다\n\n[기도]\n기도문\n"
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    missing = [e for e in result["errors"] if e["code"] == "SECTION_MISSING"]
    assert len(missing) == 1
    assert missing[0]["section"] == "scripture"


def test_all_three_sections_missing(tmp_path: Path) -> None:
    content = "이 파일에는 마커가 없습니다.\n그냥 텍스트입니다.\n"
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    missing = [e for e in result["errors"] if e["code"] == "SECTION_MISSING"]
    assert len(missing) == 3
    sections_missing = {e["section"] for e in missing}
    assert sections_missing == {"title", "scripture", "prayer"}


# ---------------------------------------------------------------------------
# SECTION_EMPTY
# ---------------------------------------------------------------------------


def test_title_marker_present_but_no_content(tmp_path: Path) -> None:
    content = "[제목]\n\n[말씀]\n말씀 내용\n\n[기도]\n기도문\n"
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    empty_errors = [e for e in result["errors"] if e["code"] == "SECTION_EMPTY"]
    assert len(empty_errors) == 1
    assert empty_errors[0]["section"] == "title"
    assert result["oneLiner"] is None


# ---------------------------------------------------------------------------
# SECTION_DUPLICATE
# ---------------------------------------------------------------------------


def test_duplicate_title_marker(tmp_path: Path) -> None:
    content = (
        "[제목]\n첫 번째 제목\n\n"
        "[말씀]\n말씀 내용\n\n"
        "[기도]\n기도문\n\n"
        "[제목]\n두 번째 제목\n"
    )
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    dup = [e for e in result["errors"] if e["code"] == "SECTION_DUPLICATE"]
    assert len(dup) == 1
    assert dup[0]["section"] == "title"
    # title section should be None when duplicated
    assert result["sections"]["title"] is None


# ---------------------------------------------------------------------------
# inputId / inputVersion pass-through
# ---------------------------------------------------------------------------


def test_input_id_and_version_echoed_in_response(tmp_path: Path) -> None:
    p = _write(tmp_path, VALID_SCRIPT)
    custom_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    custom_version = "sha256:cafebabe"
    result = validate_script(str(p), custom_id, custom_version)

    assert result["inputId"] == custom_id
    assert result["inputVersion"] == custom_version


def test_input_id_and_version_echoed_on_error(tmp_path: Path) -> None:
    missing = tmp_path / "ghost.txt"
    custom_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    custom_version = "v1"
    result = validate_script(str(missing), custom_id, custom_version)

    assert result["inputId"] == custom_id
    assert result["inputVersion"] == custom_version


def test_non_utf8_binary_file_returns_file_unreadable(tmp_path: Path) -> None:
    p = tmp_path / "binary.txt"
    p.write_bytes(b"\xff\xfe\x00binary garbage that is not valid UTF-8\x80\x81")
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    assert any(e["code"] == "FILE_UNREADABLE" for e in result["errors"])


# ---------------------------------------------------------------------------
# AST field (Story 2.2)
# ---------------------------------------------------------------------------


def test_valid_script_embeds_ast(tmp_path: Path) -> None:
    p = _write(tmp_path, VALID_SCRIPT)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "valid"
    assert "ast" in result
    ast = result["ast"]
    assert ast is not None
    assert ast["title"] == "은혜의 나무 쇼츠"
    assert "요한복음" in ast["scripture"]
    blocks = ast["subtitleBlocks"]
    assert len(blocks) >= 1
    assert "감사합니다" in blocks[0]["text"]


def test_invalid_script_has_no_ast(tmp_path: Path) -> None:
    content = "[말씀]\n내용\n[기도]\n기도"
    p = _write(tmp_path, content)
    result = validate_script(str(p), INPUT_ID, INPUT_VERSION)

    assert result["status"] == "invalid"
    assert result.get("ast") is None
