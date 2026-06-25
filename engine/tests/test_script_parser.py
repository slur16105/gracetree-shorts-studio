"""Story 2.2: 스크립트 파서 AST 및 subtitle block 골든 픽스처 테스트."""
from __future__ import annotations

import pytest

from gracetree_engine.scripts.parser import SubtitleBlock, parse_script


# ─────────────────────── helpers ────────────────────────

def _valid_script(
    title: str = "오늘의 말씀",
    scripture: str = "주님을 사랑하라 하셨네",
    prayer: str = "주님 감사합니다.\n오늘도 지켜주세요.",
) -> str:
    return f"[제목]\n{title}\n[말씀]\n{scripture}\n[기도]\n{prayer}\n"


# ─────────────────────── Task 1: AST 구조 ────────────────────────

class TestParseScriptAst:
    def test_valid_script_returns_ast(self):
        result = parse_script(_valid_script())
        assert result["status"] == "valid"
        assert result["ast"] is not None

    def test_ast_has_title_and_scripture(self):
        result = parse_script(_valid_script(title="제목1", scripture="말씀내용"))
        ast = result["ast"]
        assert ast["title"] == "제목1"
        assert ast["scripture"] == "말씀내용"

    def test_single_prayer_block(self):
        result = parse_script(_valid_script(prayer="첫째 줄\n둘째 줄"))
        blocks = result["ast"]["subtitleBlocks"]
        assert len(blocks) == 1
        assert blocks[0]["text"] == "첫째 줄\n둘째 줄"
        assert blocks[0]["lines"] == ["첫째 줄", "둘째 줄"]
        assert blocks[0]["index"] == 0

    def test_blank_line_splits_prayer_into_blocks(self):
        prayer = "첫 번째 문장입니다.\n두 번째 문장입니다.\n\n세 번째 문장입니다."
        result = parse_script(_valid_script(prayer=prayer))
        blocks = result["ast"]["subtitleBlocks"]
        assert len(blocks) == 2
        assert blocks[0]["text"] == "첫 번째 문장입니다.\n두 번째 문장입니다."
        assert blocks[0]["lines"] == ["첫 번째 문장입니다.", "두 번째 문장입니다."]
        assert blocks[1]["text"] == "세 번째 문장입니다."
        assert blocks[1]["index"] == 1

    def test_multiple_blank_lines_counted_as_one_delimiter(self):
        prayer = "블록A\n\n\n블록B"
        result = parse_script(_valid_script(prayer=prayer))
        blocks = result["ast"]["subtitleBlocks"]
        assert len(blocks) == 2
        assert blocks[0]["text"] == "블록A"
        assert blocks[1]["text"] == "블록B"

    def test_trailing_blank_lines_ignored(self):
        prayer = "블록A\n\n"
        result = parse_script(_valid_script(prayer=prayer))
        blocks = result["ast"]["subtitleBlocks"]
        assert len(blocks) == 1
        assert blocks[0]["text"] == "블록A"

    def test_invalid_script_has_no_ast(self):
        result = parse_script("[말씀]\n내용\n[기도]\n기도")  # 제목 없음
        assert result["status"] == "invalid"
        assert result["ast"] is None


# ─────────────────────── Task 2: 정규화 규칙 ────────────────────────

class TestNormalization:
    def test_utf8_bom_stripped(self):
        raw = "﻿[제목]\n제목\n[말씀]\n말씀\n[기도]\n기도"
        result = parse_script(raw)
        assert result["status"] == "valid"
        assert result["ast"]["title"] == "제목"

    def test_crlf_normalized_to_lf(self):
        raw = "[제목]\r\n제목\r\n[말씀]\r\n말씀\r\n[기도]\r\n기도"
        result = parse_script(raw)
        assert result["status"] == "valid"
        assert result["ast"]["title"] == "제목"

    def test_cr_only_normalized_to_lf(self):
        raw = "[제목]\r제목\r[말씀]\r말씀\r[기도]\r기도"
        result = parse_script(raw)
        assert result["status"] == "valid"

    def test_internal_lines_not_stripped(self):
        """기도 구역 내 줄 내부 공백은 보존한다."""
        prayer = "  들여쓰기 있는 줄\n일반 줄"
        result = parse_script(_valid_script(prayer=prayer))
        assert result["ast"]["subtitleBlocks"][0]["lines"][0] == "  들여쓰기 있는 줄"

    def test_deterministic_same_input_same_output(self):
        script = _valid_script(prayer="기도합니다.\n\n아멘.")
        r1 = parse_script(script)
        r2 = parse_script(script)
        assert r1 == r2


# ─────────────────────── Task 3: 오류 계약 ────────────────────────

class TestErrorContract:
    def test_missing_title_gives_script_invalid(self):
        result = parse_script("[말씀]\n말씀\n[기도]\n기도")
        assert result["status"] == "invalid"
        codes = [e["code"] for e in result["errors"]]
        assert "SECTION_MISSING" in codes

    def test_empty_title_gives_script_invalid(self):
        result = parse_script("[제목]\n\n[말씀]\n말씀\n[기도]\n기도")
        assert result["status"] == "invalid"
        codes = [e["code"] for e in result["errors"]]
        assert "SECTION_EMPTY" in codes

    def test_duplicate_section_gives_script_invalid(self):
        result = parse_script("[제목]\n제목\n[제목]\n중복\n[말씀]\n말씀\n[기도]\n기도")
        assert result["status"] == "invalid"
        codes = [e["code"] for e in result["errors"]]
        assert "SECTION_DUPLICATE" in codes

    def test_errors_have_required_fields(self):
        result = parse_script("[말씀]\n말씀\n[기도]\n기도")
        for err in result["errors"]:
            assert "code" in err
            assert "section" in err
            assert "message" in err


# ─────────────────────── Task 5: golden fixture ────────────────────────

class TestGoldenFixtures:
    def test_korean_multiline_prayer(self):
        script = (
            "[제목]\n오늘의 기도\n"
            "[말씀]\n주를 사랑하고 이웃을 사랑하라.\n"
            "[기도]\n주님, 오늘도 감사합니다.\n"
            "당신의 사랑이 넘칩니다.\n\n"
            "이 나라와 민족을 위해 기도합니다.\n"
            "아멘.\n"
        )
        result = parse_script(script)
        assert result["status"] == "valid"
        blocks = result["ast"]["subtitleBlocks"]
        assert len(blocks) == 2
        assert blocks[0]["lines"] == [
            "주님, 오늘도 감사합니다.",
            "당신의 사랑이 넘칩니다.",
        ]
        assert blocks[1]["lines"] == [
            "이 나라와 민족을 위해 기도합니다.",
            "아멘.",
        ]

    def test_crlf_fixture_matches_lf_fixture(self):
        lf = _valid_script(prayer="기도합니다.\n\n아멘.")
        crlf = lf.replace("\n", "\r\n")
        r_lf = parse_script(lf)
        r_crlf = parse_script(crlf)
        assert r_lf["ast"] == r_crlf["ast"]
        assert r_lf["errors"] == r_crlf["errors"]

    def test_bom_fixture_matches_no_bom_fixture(self):
        plain = _valid_script()
        bom = "﻿" + plain
        r_plain = parse_script(plain)
        r_bom = parse_script(bom)
        assert r_plain["ast"] == r_bom["ast"]

    def test_missing_all_sections(self):
        result = parse_script("아무 구역도 없는 텍스트입니다.")
        assert result["status"] == "invalid"
        codes = [e["code"] for e in result["errors"]]
        assert codes.count("SECTION_MISSING") == 3  # 제목, 말씀, 기도 모두 없음
