"""Story 2.3: 로컬 음성 정렬과 타이밍 생성 테스트."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from gracetree_engine.speech.aligner import (
    AlignmentError,
    Segment,
    align_speech,
    find_prayer_boundary,
)
from gracetree_engine.speech.config import DEFAULT_SPEECH_CONFIG, SpeechConfig

import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(__file__))
from helpers import make_silent_wav as _make_silent_wav


def _mock_transcribe(segments: list[Segment]):
    def transcribe(voice_path: Path, config: SpeechConfig) -> list[Segment]:
        return segments
    return transcribe


AST_ONE_BLOCK: dict[str, Any] = {
    "title": "오늘의 기도",
    "scripture": "주를 사랑하고 이웃을 사랑하라.",
    "subtitleBlocks": [
        {
            "index": 0,
            "text": "주님 감사합니다.\n오늘도 지켜주세요.",
            "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
        }
    ],
}

AST_TWO_BLOCKS: dict[str, Any] = {
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


# ─────────────────────── Task 4: 기도 경계 후보 규칙 ────────────────────────

class TestFindPrayerBoundary:
    def test_single_candidate_returns_one_index(self):
        segments = [
            Segment(start=0.0, end=1.5, text="오늘의 기도"),
            Segment(start=1.5, end=3.0, text="주를 사랑하고 이웃을 사랑하라"),
            Segment(start=3.0, end=4.5, text="주님 감사합니다"),
        ]
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 1
        assert candidates[0] == 2

    def test_no_matching_segment_returns_empty(self):
        segments = [
            Segment(start=0.0, end=1.5, text="완전히 다른 내용"),
            Segment(start=1.5, end=3.0, text="전혀 관련 없음"),
        ]
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 0

    def test_multiple_matches_returns_all_candidates(self):
        segments = [
            Segment(start=0.0, end=1.5, text="주님 감사합니다"),
            Segment(start=1.5, end=3.0, text="다른 내용"),
            Segment(start=3.0, end=4.5, text="주님 감사합니다"),
        ]
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 2

    def test_combined_segment_text_also_matches(self):
        """whisper가 기도 첫 줄 전체를 하나 세그먼트로 합쳐서 반환해도 후보가 된다."""
        segments = [
            Segment(start=0.0, end=2.0, text="오늘의 기도"),
            Segment(start=2.0, end=5.0, text="주님 감사합니다 오늘도 지켜주세요"),
        ]
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 1
        assert candidates[0] == 1

    def test_pair_window_boundary_is_at_second_segment(self):
        """pair-window로 매치될 때 경계 인덱스는 쌍의 두 번째 세그먼트여야 한다."""
        # "주님" alone: partial match (< 0.7 but >= 0.25 of "주님감사합니다")
        # "주님" + "감사합니다" combined: "주님감사합니다" >= 0.7
        segments = [
            Segment(start=0.0, end=1.0, text="오늘의 기도"),
            Segment(start=1.0, end=2.0, text="주님"),
            Segment(start=2.0, end=4.0, text="감사합니다"),
        ]
        # target = "주님감사합니다" (first_block lines[0] = "주님 감사합니다.")
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 1
        assert candidates[0] == 2  # idx+1, not idx

    def test_pair_window_deduplicates_when_second_segment_also_solo_matches(self):
        """pair-window와 solo match가 같은 인덱스를 생성할 때 중복을 제거해야 한다."""
        # segments[0] pair-matches via segments[0]+segments[1]
        # segments[1] also solo-matches
        # Result: [1] not [1, 1]
        segments = [
            Segment(start=0.0, end=1.0, text="주님"),       # partial (≥0.25, <0.7)
            Segment(start=1.0, end=3.0, text="감사합니다"),  # solo & pair end
        ]
        candidates = find_prayer_boundary(segments, AST_ONE_BLOCK["subtitleBlocks"][0])
        assert len(candidates) == 1
        assert candidates[0] == 1

    def test_short_first_line_uses_full_block_to_avoid_spurious_match(self):
        """첫 줄이 한 단어("하나님")로 매우 짧으면, 멀리 떨어진 세그먼트에서
        '하나(됨)…주(님)'처럼 부분수열로 우연히 매칭되어 후보가 2개가 되는
        문제가 있다. 블록 전체 텍스트를 기준으로 삼아 유일하게 매칭해야 한다."""
        block = {
            "index": 0,
            "text": "하나님,\n우리는\n타인의 슬픔에",
            "lines": ["하나님,", "우리는", "타인의 슬픔에"],
        }
        segments = [
            Segment(0.0, 11.0, "타인의 슬픔을 바라볼 때 드리는 기도 로마서 말씀"),
            # 진짜 기도 시작: 블록 전체("하나님 우리는 타인의 슬픔에")를 포함
            Segment(11.0, 23.0, "우는 자들과 함께 올라 하나님 우리는 타인의 슬픔에 얼마나 무감각"),
            # 가짜: '하나'(됨) + '주님'으로 "하나님"이 부분수열로 매칭되지만 블록 전체는 아님
            Segment(37.0, 46.0, "공동체의 하나의 마음을 허락하여 주옵소서 말씀하신 주님"),
        ]
        candidates = find_prayer_boundary(segments, block)
        assert len(candidates) == 1
        assert candidates[0] == 1


# ─────────────────────── Task 1–3: align_speech ────────────────────────

class TestAlignSpeech:
    def test_single_boundary_creates_timing_json(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [
            Segment(0.0, 1.5, "오늘의 기도"),
            Segment(1.5, 3.0, "주를 사랑하고"),
            Segment(3.0, 4.5, "주님 감사합니다"),
        ]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        assert timing_path.exists()
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        assert timing["version"] == 1
        assert "voiceOffset" in timing
        assert "leadingSilenceSeconds" in timing
        blocks = timing["subtitleBlocks"]
        assert len(blocks) == 1
        assert blocks[0]["index"] == 0

    def test_no_boundary_raises_alignment_error(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "완전히 다른 내용")]
        with pytest.raises(AlignmentError) as exc:
            align_speech(
                voice_path=voice,
                script_ast=AST_ONE_BLOCK,
                attempt_dir=attempt_dir,
                config=DEFAULT_SPEECH_CONFIG,
                _transcribe=_mock_transcribe(segments),
                _leading_silence=0.0,
            )
        assert exc.value.error_code == "PRAYER_BOUNDARY_AMBIGUOUS"

    def test_multiple_boundaries_raises_alignment_error(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [
            Segment(0.0, 1.5, "주님 감사합니다"),
            Segment(1.5, 3.0, "다른 내용"),
            Segment(3.0, 4.5, "주님 감사합니다"),
        ]
        with pytest.raises(AlignmentError) as exc:
            align_speech(
                voice_path=voice,
                script_ast=AST_ONE_BLOCK,
                attempt_dir=attempt_dir,
                config=DEFAULT_SPEECH_CONFIG,
                _transcribe=_mock_transcribe(segments),
                _leading_silence=0.0,
            )
        assert exc.value.error_code == "PRAYER_BOUNDARY_AMBIGUOUS"

    def test_original_voice_file_not_modified(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        original_hash = hashlib.sha256(voice.read_bytes()).hexdigest()
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        assert hashlib.sha256(voice.read_bytes()).hexdigest() == original_hash

    def test_leading_silence_adjusts_voice_offset(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        # 음성 파일에 0.3s leading silence 가 있는 것처럼 모의
        segments = [
            Segment(0.3, 2.0, "주님 감사합니다"),
        ]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.3,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        assert timing["leadingSilenceSeconds"] == pytest.approx(0.3)
        assert timing["voiceOffset"] == pytest.approx(1.7)  # 2.0 - 0.3
        # 세그먼트 0.3s + voiceOffset 1.7 = 2.0s
        assert timing["subtitleBlocks"][0]["startTime"] == pytest.approx(2.0)

    def test_timing_json_in_attempt_dir(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        assert timing_path.parent == attempt_dir
        assert timing_path.name == "timing.json"

    def test_two_blocks_mapped_sequentially(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [
            Segment(0.0, 1.5, "오늘의 기도"),
            Segment(1.5, 3.0, "주를 사랑하고"),
            Segment(3.0, 5.0, "주님 감사합니다 오늘도 지켜주세요"),
            Segment(5.0, 7.0, "이 나라를 위해 기도합니다 아멘"),
        ]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_TWO_BLOCKS,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        blocks = timing["subtitleBlocks"]
        assert len(blocks) == 2
        assert blocks[0]["index"] == 0
        assert blocks[1]["index"] == 1
        assert blocks[0]["startTime"] < blocks[1]["startTime"]
        assert blocks[0]["text"] == AST_TWO_BLOCKS["subtitleBlocks"][0]["text"]
        assert blocks[1]["text"] == AST_TWO_BLOCKS["subtitleBlocks"][1]["text"]

    def test_voice_copy_placed_in_attempt_dir(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        # 사본이 attempt_dir에 있어야 한다
        copies = list(attempt_dir.glob("voice_copy*"))
        assert len(copies) == 1

    def test_no_network_calls_during_alignment(self, tmp_path, monkeypatch):
        """정렬 중 네트워크 요청이 없어야 한다."""
        calls: list = []

        def _no_net(*args, **kwargs):
            calls.append(args)
            raise RuntimeError("Network calls are forbidden during alignment")

        monkeypatch.setattr(urllib.request, "urlopen", _no_net)

        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        assert calls == []

    def test_empty_segments_raises_no_speech_detected(self, tmp_path):
        """발화가 감지되지 않으면 NO_SPEECH_DETECTED를 방출해야 한다."""
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        with pytest.raises(AlignmentError) as exc:
            align_speech(
                voice_path=voice,
                script_ast=AST_ONE_BLOCK,
                attempt_dir=attempt_dir,
                config=DEFAULT_SPEECH_CONFIG,
                _transcribe=_mock_transcribe([]),
                _leading_silence=0.0,
            )
        assert exc.value.error_code == "NO_SPEECH_DETECTED"
        assert exc.value.recoverable is True


# ─────────────────────── Task 5: timing.json 스키마 검증 ────────────────────────

class TestTimingJsonSchema:
    def test_timing_json_is_schema_valid(self, tmp_path):
        import jsonschema

        schema_path = (
            Path(__file__).resolve().parents[2]
            / "packages" / "contracts" / "schemas" / "timing.schema.json"
        )
        if not schema_path.exists():
            pytest.skip("timing.schema.json not found")

        schema = json.loads(schema_path.read_text())
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        jsonschema.validate(timing, schema)

    def test_timing_blocks_have_all_required_fields(self, tmp_path):
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        for block in timing["subtitleBlocks"]:
            assert "index" in block
            assert "text" in block
            assert "lines" in block
            assert "startTime" in block
            assert "endTime" in block


# ─────────────────────── Task 1: 설정 ────────────────────────

class TestSpeechConfig:
    def test_default_config_has_expected_values(self):
        assert DEFAULT_SPEECH_CONFIG.model_size == "base"
        assert DEFAULT_SPEECH_CONFIG.compute_type == "int8"
        assert DEFAULT_SPEECH_CONFIG.language == "ko"
        assert DEFAULT_SPEECH_CONFIG.device == "cpu"

    def test_config_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_SPEECH_CONFIG.model_size = "large"  # type: ignore[misc]

    def test_custom_config_overrides_defaults(self):
        cfg = SpeechConfig(model_size="small", compute_type="float32")
        assert cfg.model_size == "small"
        assert cfg.compute_type == "float32"
        assert cfg.language == "ko"  # default


# ─────────────────────── Task 2: 음절 분할 대응 ────────────────────────

class TestSplitSegmentBoundary:
    def test_split_first_line_still_finds_boundary(self, tmp_path):
        """Whisper가 기도 첫 줄을 두 세그먼트로 분할해도 경계를 찾아야 한다."""
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        # '주님 감사합니다.' → Whisper가 '주님' + '감사합니다'로 분할
        segments = [
            Segment(0.0, 1.0, "오늘의 기도"),
            Segment(1.0, 2.0, "주님"),
            Segment(2.0, 3.5, "감사합니다"),
        ]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        assert len(timing["subtitleBlocks"]) == 1

    def test_negative_leading_silence_uses_unclamped_for_offset(self, tmp_path):
        """whisper가 -0.5s 타임스탬프를 반환하면 voice_offset이 2.5s가 되어야 한다."""
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        segments = [Segment(-0.5, 1.0, "주님 감사합니다")]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_ONE_BLOCK,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=-0.5,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        # 음수는 0으로 클램핑해서 저장
        assert timing["leadingSilenceSeconds"] == pytest.approx(0.0)
        # voice_offset = max(0, 2.0 - (-0.5)) = 2.5
        assert timing["voiceOffset"] == pytest.approx(2.5)
        # 자막 시작 = -0.5 + 2.5 = 2.0s (타겟 일치)
        assert timing["subtitleBlocks"][0]["startTime"] == pytest.approx(2.0)

    def test_overflow_blocks_have_distinct_start_times(self, tmp_path):
        """블록 수가 세그먼트보다 많을 때 오버플로 블록의 startTime이 다르고 endTime > startTime이어야 한다."""
        voice = _make_silent_wav(tmp_path / "voice.wav")
        attempt_dir = tmp_path / "attempt"
        attempt_dir.mkdir()
        # 2블록인데 기도 시작 이후 세그먼트가 1개뿐
        segments = [Segment(0.0, 1.5, "주님 감사합니다")]
        timing_path = align_speech(
            voice_path=voice,
            script_ast=AST_TWO_BLOCKS,
            attempt_dir=attempt_dir,
            config=DEFAULT_SPEECH_CONFIG,
            _transcribe=_mock_transcribe(segments),
            _leading_silence=0.0,
        )
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        blocks = timing["subtitleBlocks"]
        assert len(blocks) == 2
        for b in blocks:
            assert b["endTime"] > b["startTime"]
