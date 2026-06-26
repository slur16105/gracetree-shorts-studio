"""Story 2.5: 스타일 ASS 자막 생성 테스트."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from gracetree_engine.subtitles.generator import (
    SubtitleError,
    generate_ass,
    generate_subtitles,
)
from gracetree_engine.subtitles.config import SubtitleConfig, DEFAULT_SUBTITLE_CONFIG


# ─────────────────────── 공통 픽스처 ────────────────────────

SCRIPT_AST: dict[str, Any] = {
    "title": "오늘의 기도",
    "scripture": "주를 사랑하고 이웃을 사랑하라.",
    "subtitleBlocks": [
        {
            "index": 0,
            "text": "주님 감사합니다.\n오늘도 지켜주세요.",
            "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
        },
        {
            "index": 1,
            "text": "이 나라를 위해 기도합니다.\n아멘.",
            "lines": ["이 나라를 위해 기도합니다.", "아멘."],
        },
    ],
}

TIMING: dict[str, Any] = {
    "version": 1,
    "voiceOffset": 2.0,
    "leadingSilenceSeconds": 0.0,
    "subtitleBlocks": [
        {
            "index": 0,
            "text": "주님 감사합니다.\n오늘도 지켜주세요.",
            "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
            "startTime": 2.0,
            "endTime": 6.0,
        },
        {
            "index": 1,
            "text": "이 나라를 위해 기도합니다.\n아멘.",
            "lines": ["이 나라를 위해 기도합니다.", "아멘."],
            "startTime": 6.0,
            "endTime": 10.0,
        },
    ],
}


# ─────────────────────── Task 1: ASS 이벤트 생성 ────────────────────────

class TestGenerateAss:
    def test_output_is_string(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert isinstance(content, str)

    def test_has_script_info_header(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "[Script Info]" in content
        assert "PlayResX: 1080" in content
        assert "PlayResY: 1920" in content

    def test_has_styles_section(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "[V4+ Styles]" in content

    def test_has_events_section(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "[Events]" in content
        assert "Dialogue:" in content

    def test_title_appears_in_events(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "오늘의 기도" in content

    def test_scripture_appears_in_events(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "주를 사랑하고 이웃을 사랑하라." in content

    def test_prayer_blocks_appear_in_events(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert "주님 감사합니다." in content

    def test_title_uses_top_alignment(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        lines = [l for l in content.splitlines() if "Style: Title" in l]
        assert len(lines) == 1
        # Alignment 8 = top-center
        parts = lines[0].split(",")
        alignment_idx = 18  # 0-indexed field in Style line
        assert parts[alignment_idx].strip() == "8"

    def test_prayer_uses_center_alignment(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        lines = [l for l in content.splitlines() if "Style: Prayer" in l]
        assert len(lines) == 1
        parts = lines[0].split(",")
        alignment_idx = 18
        assert parts[alignment_idx].strip() == "5"


# ─────────────────────── Task 2: 설정 (typed config) ────────────────────────

class TestSubtitleConfig:
    def test_default_resolution_is_1080x1920(self):
        assert DEFAULT_SUBTITLE_CONFIG.play_res_x == 1080
        assert DEFAULT_SUBTITLE_CONFIG.play_res_y == 1920

    def test_safe_area_margins_are_set(self):
        assert DEFAULT_SUBTITLE_CONFIG.margin_h > 0
        assert DEFAULT_SUBTITLE_CONFIG.margin_v_top > 0

    def test_config_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_SUBTITLE_CONFIG.play_res_x = 720  # type: ignore[misc]

    def test_amen_hold_and_fade_configured(self):
        assert DEFAULT_SUBTITLE_CONFIG.amen_hold_seconds > 0
        assert DEFAULT_SUBTITLE_CONFIG.amen_fade_out_ms > 0


# ─────────────────────── Task 3: ASS 특수문자 이스케이프 ────────────────────────

class TestASSEscape:
    def test_newline_converted_to_ass_newline(self):
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {
                "index": 0,
                "text": "주님 감사합니다.\n오늘도 지켜주세요.",
                "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
            }
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {
                "index": 0,
                "text": "주님 감사합니다.\n오늘도 지켜주세요.",
                "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
                "startTime": 2.0,
                "endTime": 5.0,
            }
        ]}
        content = generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        # ASS newline is \N (literal backslash-N in the text field)
        assert r"\N" in content

    def test_curly_braces_in_text_are_escaped(self):
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": "주님 {감사}합니다.", "lines": ["주님 {감사}합니다."]}
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "주님 {감사}합니다.", "lines": ["주님 {감사}합니다."], "startTime": 2.0, "endTime": 5.0}
        ]}
        content = generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        # Raw { and } should be escaped in dialogue text
        # ASS uses \{ and \} to display literal braces
        dialogue_lines = [l for l in content.splitlines() if "Dialogue:" in l and "감사" in l]
        assert any(r"\{" in l or r"\}" in l for l in dialogue_lines)

    def test_output_is_utf8_encodable(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        encoded = content.encode("utf-8")
        assert len(encoded) > 0
        assert content == encoded.decode("utf-8")

    def test_crlf_in_text_does_not_leave_carriage_return(self):
        """CRLF 입력에서 \\r이 Dialogue 텍스트 필드에 남지 않아야 한다."""
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": "주님 감사합니다.\r\n오늘도 지켜주세요.", "lines": ["주님 감사합니다.", "오늘도 지켜주세요."]}
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "주님 감사합니다.\r\n오늘도 지켜주세요.",
             "lines": ["주님 감사합니다.", "오늘도 지켜주세요."], "startTime": 2.0, "endTime": 5.0}
        ]}
        content = generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        assert "\r" not in content


# ─────────────────────── Task 4: glyph·safe area 검증 ────────────────────────

class TestValidation:
    def test_non_existent_font_raises_error(self, tmp_path):
        with pytest.raises(SubtitleError) as exc:
            generate_ass(
                SCRIPT_AST,
                TIMING,
                DEFAULT_SUBTITLE_CONFIG,
                font_path=tmp_path / "nonexistent.ttf",
            )
        assert exc.value.error_code == "FONT_NOT_FOUND"

    def test_valid_font_path_none_skips_font_check(self):
        # font_path=None means "use system font, skip file check"
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG, font_path=None)
        assert isinstance(content, str)

    def test_non_korean_glyph_in_prayer_text_raises_error(self):
        """한국 폰트가 지원하지 않는 한자(CJK Unified Ideographs)가 기도 블록에 포함된 경우."""
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": "你好 주님", "lines": ["你好 주님"]}  # Chinese
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "你好 주님", "lines": ["你好 주님"], "startTime": 2.0, "endTime": 5.0}
        ]}
        with pytest.raises(SubtitleError) as exc:
            generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "GLYPH_NOT_SUPPORTED"

    def test_non_korean_glyph_in_title_raises_error(self):
        """한자가 title에 포함된 경우도 glyph 검증이 잡아야 한다."""
        ast = {**SCRIPT_AST, "title": "主의 기도"}  # 主 = CJK
        with pytest.raises(SubtitleError) as exc:
            generate_ass(ast, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "GLYPH_NOT_SUPPORTED"

    def test_non_korean_glyph_in_scripture_raises_error(self):
        """한자가 scripture에 포함된 경우도 glyph 검증이 잡아야 한다."""
        ast = {**SCRIPT_AST, "scripture": "主를 사랑하고"}  # 主 = CJK
        with pytest.raises(SubtitleError) as exc:
            generate_ass(ast, TIMING, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "GLYPH_NOT_SUPPORTED"

    def test_ascii_control_char_in_text_raises_error(self):
        """제어 문자(NULL 등)는 GLYPH_NOT_SUPPORTED를 발생시켜야 한다."""
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": "주님\x00감사", "lines": ["주님\x00감사"]}
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "주님\x00감사", "lines": ["주님\x00감사"], "startTime": 2.0, "endTime": 5.0}
        ]}
        with pytest.raises(SubtitleError) as exc:
            generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "GLYPH_NOT_SUPPORTED"

    def test_safe_area_exceeded_raises_error(self):
        """라인 수가 너무 많아 safe area를 초과하는 블록은 에러를 발생시킨다."""
        many_lines = "\n".join(f"라인{i}" for i in range(30))
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": many_lines, "lines": many_lines.split("\n")}
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": many_lines, "lines": many_lines.split("\n"), "startTime": 2.0, "endTime": 5.0}
        ]}
        with pytest.raises(SubtitleError) as exc:
            generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "SAFE_AREA_EXCEEDED"


# ─────────────────────── Task 5: 아멘 duration/fade ────────────────────────

class TestAmenHandling:
    def _get_last_dialogue_time(self, content: str) -> float:
        """마지막 Dialogue 행의 End 시간을 초로 반환한다."""
        dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
        last = dialogue_lines[-1]
        # Format: Dialogue: Layer,Start,End,...
        parts = last.split(",")
        end_str = parts[2].strip()  # H:MM:SS.CC
        h, m, s = end_str.split(":")
        s_main, cs = s.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s_main) + int(cs) / 100

    def test_last_amen_block_holds_extra_2s(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        # Original last block endTime = 10.0, hold = 2.0 → end at 12.0
        last_end = self._get_last_dialogue_time(content)
        assert last_end == pytest.approx(12.0, abs=0.05)

    def test_non_amen_last_block_not_extended(self):
        ast = {**SCRIPT_AST, "subtitleBlocks": [
            {"index": 0, "text": "주님 감사합니다.", "lines": ["주님 감사합니다."]}
        ]}
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "주님 감사합니다.", "lines": ["주님 감사합니다."],
             "startTime": 2.0, "endTime": 6.0}
        ]}
        content = generate_ass(ast, timing, DEFAULT_SUBTITLE_CONFIG)
        last_end = self._get_last_dialogue_time(content)
        # endTime should not be extended (no amen hold)
        assert last_end == pytest.approx(6.0, abs=0.05)

    def test_amen_fade_out_is_500ms(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        # Find the last prayer dialogue
        prayer_dialogues = [l for l in content.splitlines()
                            if "Dialogue:" in l and "아멘" in l]
        assert len(prayer_dialogues) >= 1
        # Should contain \fad(...,500)
        last_prayer = prayer_dialogues[-1]
        assert re.search(r"\\fad\(\d+,500\)", last_prayer)


# ─────────────────────── Task 5: generate_subtitles (file I/O) ────────────────────────

class TestGenerateSubtitles:
    def test_writes_subtitles_ass_to_attempt_dir(self, tmp_path):
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        path = generate_subtitles(SCRIPT_AST, TIMING, attempt_dir, DEFAULT_SUBTITLE_CONFIG)
        assert path.name == "subtitles.ass"
        assert path.parent == attempt_dir
        assert path.exists()

    def test_file_is_utf8_encoded(self, tmp_path):
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        path = generate_subtitles(SCRIPT_AST, TIMING, attempt_dir, DEFAULT_SUBTITLE_CONFIG)
        content = path.read_text(encoding="utf-8")
        assert "오늘의 기도" in content

    def test_returns_path_to_written_file(self, tmp_path):
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        result = generate_subtitles(SCRIPT_AST, TIMING, attempt_dir, DEFAULT_SUBTITLE_CONFIG)
        assert isinstance(result, Path)
        assert result.is_file()

    def test_raises_subtitle_error_if_attempt_dir_missing(self, tmp_path):
        with pytest.raises(SubtitleError) as exc:
            generate_subtitles(SCRIPT_AST, TIMING, tmp_path / "nonexistent", DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "OUTPUT_DIR_MISSING"


# ─────────────────────── Golden fixture ────────────────────────

class TestGoldenFixture:
    GOLDEN_DIR = Path(__file__).parent / "fixtures" / "subtitles"

    def test_golden_ass_structure(self, tmp_path):
        """생성된 ASS가 황금 구조를 만족하는지 검증한다."""
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        sections = re.findall(r"\[(.+?)\]", content)
        # Must have these three sections in order
        assert "Script Info" in sections
        assert "V4+ Styles" in sections
        assert "Events" in sections
        assert sections.index("Script Info") < sections.index("V4+ Styles")
        assert sections.index("V4+ Styles") < sections.index("Events")

    def test_all_dialogue_events_have_valid_time_format(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        time_pattern = re.compile(r"\d:\d{2}:\d{2}\.\d{2}")
        for line in content.splitlines():
            if line.startswith("Dialogue:"):
                parts = line.split(",")
                assert time_pattern.match(parts[1].strip()), f"Invalid start time: {parts[1]}"
                assert time_pattern.match(parts[2].strip()), f"Invalid end time: {parts[2]}"

    def test_title_starts_before_first_prayer(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        title_lines = [l for l in content.splitlines()
                       if "Dialogue:" in l and "오늘의 기도" in l]
        assert len(title_lines) >= 1
        # Title start should be at 0:00:00.00
        parts = title_lines[0].split(",")
        assert parts[1].strip() == "0:00:00.00"

    def test_prayer_start_matches_timing(self):
        content = generate_ass(SCRIPT_AST, TIMING, DEFAULT_SUBTITLE_CONFIG)
        prayer_lines = [l for l in content.splitlines()
                        if "Dialogue:" in l and "주님 감사합니다" in l]
        assert len(prayer_lines) >= 1
        parts = prayer_lines[0].split(",")
        # startTime = 2.0 → 0:00:02.00
        assert parts[1].strip() == "0:00:02.00"

    def test_negative_timestamp_clamped_to_zero(self):
        """음수 startTime은 0으로 clamp되어 유효한 ASS 타임스탬프를 생성해야 한다."""
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "startTime": -0.5, "endTime": 5.0, "text": "주님", "lines": ["주님"]},
        ]}
        content = generate_ass(SCRIPT_AST, timing, DEFAULT_SUBTITLE_CONFIG)
        # Negative timestamp should be clamped: 0:00:00.00
        prayer_lines = [l for l in content.splitlines()
                        if "Dialogue:" in l and "주님" in l and "Prayer" in l]
        assert len(prayer_lines) >= 1
        parts = prayer_lines[0].split(",")
        assert parts[1].strip() == "0:00:00.00"

    def test_missing_timing_key_raises_subtitle_error(self):
        """timing block에 startTime/endTime이 없으면 KeyError 대신 SubtitleError를 발생시킨다."""
        timing = {**TIMING, "subtitleBlocks": [
            {"index": 0, "text": "주님"},  # startTime/endTime 없음
        ]}
        with pytest.raises(SubtitleError) as exc:
            generate_ass(SCRIPT_AST, timing, DEFAULT_SUBTITLE_CONFIG)
        assert exc.value.error_code == "MISSING_TIMING"
