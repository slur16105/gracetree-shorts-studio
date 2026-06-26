"""Story 2.8: FFmpeg 파이프라인 통합 검증 — 진단 유닛 테스트.

통합 테스트(ffmpeg 설치 필요)는 tests/integration/test_media_pipeline.py에 있습니다.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest

from gracetree_engine.diagnostics.logger import (
    PipelineDiagnostics,
    StageResult,
    redact_paths,
)


# ─────────────────────── Task 4: 진단 로거 ────────────────────────

class TestRedactPaths:
    def test_removes_absolute_path_leaving_basename(self):
        result = redact_paths("/Users/alice/project/data/intro.mp4")
        assert "/Users" not in result
        assert "intro.mp4" in result

    def test_removes_multiple_paths(self):
        text = "input /home/user/voice.wav output /tmp/out.mp4"
        result = redact_paths(text)
        assert "/home/user" not in result
        assert "/tmp" not in result
        assert "voice.wav" in result
        assert "out.mp4" in result

    def test_non_path_text_unchanged(self):
        text = "ffmpeg -version"
        assert redact_paths(text) == text

    def test_windows_path_redacted(self):
        text = r"C:\Users\user\AppData\file.mp4"
        result = redact_paths(text)
        assert r"C:\Users\user\AppData" not in result


class TestPipelineDiagnostics:
    def test_record_stage_captures_wall_time(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("parse_script", wall_time=0.05)
        stages = diag.stages
        assert len(stages) == 1
        assert stages[0].name == "parse_script"
        assert stages[0].wall_time == pytest.approx(0.05)

    def test_record_stage_redacts_cmd(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("compose", wall_time=1.0,
                          cmd=["ffmpeg", "-i", "/home/user/intro.mp4", "out.mp4"])
        assert diag.stages[0].redacted_cmd is not None
        assert "/home/user" not in diag.stages[0].redacted_cmd

    def test_record_stage_none_cmd_stays_none(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("align", wall_time=2.3)
        assert diag.stages[0].redacted_cmd is None

    def test_write_log_creates_json_file(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("parse_script", wall_time=0.01)
        diag.write_log()
        log_file = tmp_path / "pipeline-diagnostics.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert "stages" in data
        assert data["stages"][0]["name"] == "parse_script"

    def test_total_wall_time_is_sum_of_stages(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("a", wall_time=1.0)
        diag.record_stage("b", wall_time=2.0)
        assert diag.total_wall_time == pytest.approx(3.0)

    def test_context_manager_measures_time(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        with diag.stage("parse_script"):
            time.sleep(0.01)
        assert diag.stages[0].wall_time >= 0.01

    def test_multiple_stages_recorded(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag.record_stage("stage1", wall_time=0.1)
        diag.record_stage("stage2", wall_time=0.2)
        diag.record_stage("stage3", wall_time=0.3)
        assert len(diag.stages) == 3
        assert diag.stages[2].name == "stage3"


# ─────────────────────── Task 1: 픽스처 세트 ────────────────────────

class TestFixtureGeneration:
    def test_fixture_manifest_exists(self):
        manifest_path = Path(__file__).parent / "fixtures" / "integration" / "fixture-manifest.json"
        assert manifest_path.exists(), "fixture-manifest.json이 없습니다"

    def test_fixture_manifest_has_required_fields(self):
        manifest_path = Path(__file__).parent / "fixtures" / "integration" / "fixture-manifest.json"
        data = json.loads(manifest_path.read_text())
        assert "description" in data
        assert "license" in data
        assert "fixtures" in data

    def test_fixture_manifest_lists_all_required_types(self):
        manifest_path = Path(__file__).parent / "fixtures" / "integration" / "fixture-manifest.json"
        data = json.loads(manifest_path.read_text())
        fixture_types = {f["type"] for f in data["fixtures"]}
        required = {"script", "voice", "thumbnail", "bgm", "intro_video", "loop_video"}
        assert required.issubset(fixture_types)


# ─────────────────────── Task 3: ffprobe 검증 (단위) ────────────────────────

class TestPipelineVerification:
    def test_verify_streams_detects_no_video(self):
        from gracetree_engine.diagnostics.verifier import VerificationError, verify_streams
        # Audio-only stream info (no video)
        stream_info = {"streams": [{"codec_type": "audio"}], "format": {"duration": "5.0"}}
        with pytest.raises(VerificationError) as exc:
            verify_streams(stream_info, require_video=True, require_audio=True)
        assert exc.value.error_code == "NO_VIDEO_STREAM"

    def test_verify_streams_detects_no_audio(self):
        from gracetree_engine.diagnostics.verifier import VerificationError, verify_streams
        stream_info = {"streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
                       "format": {"duration": "5.0"}}
        with pytest.raises(VerificationError) as exc:
            verify_streams(stream_info, require_video=True, require_audio=True)
        assert exc.value.error_code == "NO_AUDIO_STREAM"

    def test_verify_streams_passes_with_both(self):
        from gracetree_engine.diagnostics.verifier import verify_streams
        stream_info = {
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920, "r_frame_rate": "30/1"},
                {"codec_type": "audio"},
            ],
            "format": {"duration": "5.0"},
        }
        verify_streams(stream_info, require_video=True, require_audio=True)  # should not raise

    def test_verify_dimensions_rejects_wrong_resolution(self):
        from gracetree_engine.diagnostics.verifier import VerificationError, verify_dimensions
        with pytest.raises(VerificationError) as exc:
            verify_dimensions(width=1920, height=1080, expected_width=1080, expected_height=1920)
        assert exc.value.error_code == "WRONG_DIMENSIONS"

    def test_verify_dimensions_accepts_correct_resolution(self):
        from gracetree_engine.diagnostics.verifier import verify_dimensions
        verify_dimensions(1080, 1920, 1080, 1920)  # should not raise

    def test_verify_duration_rejects_too_short(self):
        from gracetree_engine.diagnostics.verifier import VerificationError, verify_duration
        with pytest.raises(VerificationError) as exc:
            verify_duration(actual=0.5, minimum=1.0)
        assert exc.value.error_code == "DURATION_TOO_SHORT"

    def test_verify_duration_accepts_sufficient(self):
        from gracetree_engine.diagnostics.verifier import verify_duration
        verify_duration(actual=10.0, minimum=1.0)  # should not raise


# ─────────────────────── Task 5: 실패 시 partial output 격리 ────────────────────────

class TestFailureIsolation:
    def test_partial_output_does_not_exist_when_stage_fails(self, tmp_path):
        """중간 단계가 실패하면 final.mp4가 attempt_dir에 존재하면 안 된다."""
        from gracetree_engine.media.compose import ComposeError, compose_video_audio
        from unittest.mock import patch, MagicMock

        bg = tmp_path / "background.mp4"; bg.write_bytes(b"x")
        voice = tmp_path / "voice.mp3"; voice.write_bytes(b"x")
        bgm = tmp_path / "bgm.mp3"; bgm.write_bytes(b"x")
        thumb = tmp_path / "thumb.jpg"; thumb.write_bytes(b"x")
        attempt = tmp_path / "attempt"; attempt.mkdir()

        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]
            mock_run.return_value = MagicMock(returncode=1, stderr="fail")
            with pytest.raises(ComposeError):
                compose_video_audio(bg, voice, bgm, thumb, attempt)

        # final.mp4 should NOT exist (ffmpeg failed, so file not written)
        assert not (attempt / "final.mp4").exists()

    def test_subtitles_not_written_on_validation_failure(self, tmp_path):
        """자막 검증 실패 시 subtitles.ass가 생성되면 안 된다."""
        from gracetree_engine.subtitles.generator import SubtitleError, generate_subtitles

        attempt = tmp_path / "attempt"; attempt.mkdir()
        bad_ast = {"title": "주님", "scripture": "주님", "subtitleBlocks": []}
        bad_timing = {"subtitleBlocks": [
            {"index": 0, "text": "主", "lines": ["主"], "startTime": 1.0, "endTime": 2.0}  # CJK
        ]}
        with pytest.raises(SubtitleError):
            generate_subtitles(bad_ast, bad_timing, attempt)

        assert not (attempt / "subtitles.ass").exists()
