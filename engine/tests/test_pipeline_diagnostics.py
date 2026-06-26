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

    def test_redact_paths_does_not_corrupt_na_tokens(self):
        result = redact_paths("N/A kbits/s ratio=1/25")
        assert result == "N/A kbits/s ratio=1/25"

    def test_redact_paths_handles_quoted_paths(self):
        result = redact_paths("open '/home/user/video.mp4': No such file")
        assert "/home/user" not in result
        assert "video.mp4" in result


class TestPipelineDiagnostics:
    def test_record_stage_captures_wall_time(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("parse_script", wall_time=0.05)
        stages = diag.stages
        assert len(stages) == 1
        assert stages[0].name == "parse_script"
        assert stages[0].wall_time == pytest.approx(0.05)

    def test_record_stage_redacts_cmd(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("compose", wall_time=1.0,
                          cmd=["ffmpeg", "-i", "/home/user/intro.mp4", "out.mp4"])
        assert diag.stages[0].redacted_cmd is not None
        assert "/home/user" not in diag.stages[0].redacted_cmd

    def test_record_stage_none_cmd_stays_none(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("align", wall_time=2.3)
        assert diag.stages[0].redacted_cmd is None

    def test_write_log_creates_json_file(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("parse_script", wall_time=0.01)
        diag.write_log()
        log_file = tmp_path / "pipeline-diagnostics.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert "stages" in data
        assert data["stages"][0]["name"] == "parse_script"
        assert data["stages"][0]["status"] == "ok"

    def test_total_wall_time_is_sum_of_stages(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("a", wall_time=1.0)
        diag._record_stage("b", wall_time=2.0)
        assert diag.total_wall_time == pytest.approx(3.0)

    def test_context_manager_measures_time(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        with diag.stage("parse_script"):
            time.sleep(0.01)
        assert diag.stages[0].wall_time >= 0.01
        assert diag.stages[0].status == "ok"

    def test_multiple_stages_recorded(self, tmp_path):
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("stage1", wall_time=0.1)
        diag._record_stage("stage2", wall_time=0.2)
        diag._record_stage("stage3", wall_time=0.3)
        assert len(diag.stages) == 3
        assert diag.stages[2].name == "stage3"


# ─────────────────────── Task 1: 픽스처 세트 ────────────────────────

class TestFixtureGeneration:
    _MANIFEST_PATH = Path(__file__).parent / "fixtures" / "integration" / "fixture-manifest.json"

    def test_fixture_manifest_exists(self):
        assert self._MANIFEST_PATH.exists(), "fixture-manifest.json이 없습니다"

    def test_fixture_manifest_has_required_fields(self):
        data = json.loads(self._MANIFEST_PATH.read_text())
        assert "description" in data
        assert "license" in data
        assert "fixtures" in data

    def test_fixture_manifest_lists_all_required_types(self):
        data = json.loads(self._MANIFEST_PATH.read_text())
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


# ─────────────────────── 리뷰 수정 검증 ────────────────────────

class TestReviewFixes:
    def test_stage_context_manager_records_on_exception(self, tmp_path):
        """stage()가 예외 발생 시에도 스테이지를 기록하고 status='error'를 표시해야 한다."""
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        with pytest.raises(ValueError):
            with diag.stage("failing_stage"):
                raise ValueError("boom")
        assert len(diag.stages) == 1
        assert diag.stages[0].name == "failing_stage"
        assert diag.stages[0].wall_time >= 0.0
        assert diag.stages[0].status == "error"

    def test_write_log_is_atomic(self, tmp_path):
        """write_log()은 .tmp를 거쳐 atomic replace한다 — 중간 파일이 남으면 안 된다."""
        diag = PipelineDiagnostics(attempt_dir=tmp_path)
        diag._record_stage("stage1", wall_time=0.1)
        diag.write_log()
        tmp_file = tmp_path / "pipeline-diagnostics.json.tmp"
        assert not tmp_file.exists(), ".tmp 파일이 남아 있으면 안 됩니다"
        assert (tmp_path / "pipeline-diagnostics.json").exists()

    def test_redact_paths_handles_root_level_paths(self):
        """루트 레벨 Unix 경로 /filename.ext도 redact 처리해야 한다."""
        result = redact_paths("output /output.mp4 done")
        assert "/output.mp4" not in result
        assert "output.mp4" in result

    def test_probe_file_raises_verification_error_for_missing_file(self):
        """probe_file()은 파일 없을 때 VerificationError(FILE_NOT_FOUND)를 발생시켜야 한다."""
        from gracetree_engine.diagnostics.verifier import VerificationError, probe_file
        with pytest.raises(VerificationError) as exc:
            probe_file(Path("/no/such/file.mp4"))
        assert exc.value.error_code == "FILE_NOT_FOUND"

    def test_probe_file_raises_on_invalid_json_output(self):
        """probe_file()은 ffprobe stdout이 JSON이 아닐 때 VerificationError(PROBE_FAILED)를 발생시켜야 한다."""
        from gracetree_engine.diagnostics.verifier import VerificationError, probe_file
        from unittest.mock import MagicMock, patch
        mock_result = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("gracetree_engine.diagnostics.verifier.run_safe", return_value=mock_result):
            with pytest.raises(VerificationError) as exc:
                probe_file(Path(__file__))
        assert exc.value.error_code == "PROBE_FAILED"

    def test_blackdetect_raises_on_runner_error(self):
        """run_blackdetect()은 RunnerError를 삼키지 않고 VerificationError(BLACKDETECT_FAILED)로 변환해야 한다."""
        from gracetree_engine.diagnostics.verifier import VerificationError, run_blackdetect
        from gracetree_engine.media.runner import RunnerError
        from unittest.mock import patch
        with patch("gracetree_engine.diagnostics.verifier.run_safe", side_effect=RunnerError("TIMEOUT", "timed out")):
            with pytest.raises(VerificationError) as exc:
                run_blackdetect(Path("/fake/video.mp4"))
        assert exc.value.error_code == "BLACKDETECT_FAILED"

    def test_freezedetect_raises_on_runner_error(self):
        """run_freezedetect()은 RunnerError를 삼키지 않고 VerificationError(FREEZEDETECT_FAILED)로 변환해야 한다."""
        from gracetree_engine.diagnostics.verifier import VerificationError, run_freezedetect
        from gracetree_engine.media.runner import RunnerError
        from unittest.mock import patch
        with patch("gracetree_engine.diagnostics.verifier.run_safe", side_effect=RunnerError("TIMEOUT", "timed out")):
            with pytest.raises(VerificationError) as exc:
                run_freezedetect(Path("/fake/video.mp4"))
        assert exc.value.error_code == "FREEZEDETECT_FAILED"

    def test_freezedetect_handles_eof_freeze(self):
        """freeze_end 없이 끝난 freeze는 end=None으로 인터벌에 추가되어야 한다."""
        from gracetree_engine.diagnostics.verifier import run_freezedetect
        from unittest.mock import MagicMock, patch
        fake_stderr = "[freezedetect @ 0x...] freeze_start: 3.000000\n"
        mock_result = MagicMock(returncode=0, stdout="", stderr=fake_stderr)
        with patch("gracetree_engine.diagnostics.verifier.run_safe", return_value=mock_result):
            intervals = run_freezedetect(Path("/fake/video.mp4"))
        assert len(intervals) == 1
        assert intervals[0]["start"] == pytest.approx(3.0)
        assert intervals[0]["end"] is None

    def test_freezedetect_resets_stale_freeze_start_on_parse_error(self):
        """freeze_start 파싱 ValueError 시 잔류 값을 초기화해 spurious EOF 인터벌을 방지해야 한다."""
        from gracetree_engine.diagnostics.verifier import run_freezedetect
        from unittest.mock import MagicMock, patch
        fake_stderr = (
            "[freezedetect @ 0x...] freeze_start: INVALID\n"
        )
        mock_result = MagicMock(returncode=0, stdout="", stderr=fake_stderr)
        with patch("gracetree_engine.diagnostics.verifier.run_safe", return_value=mock_result):
            intervals = run_freezedetect(Path("/fake/video.mp4"))
        assert intervals == []

    def test_blackdetect_skips_incomplete_interval(self):
        """black_end 또는 black_duration이 없는 인터벌은 조용히 무시해야 한다."""
        from gracetree_engine.diagnostics.verifier import run_blackdetect
        from unittest.mock import MagicMock, patch
        fake_stderr = "[blackdetect @ 0x...] black_start:1.0\n"
        mock_result = MagicMock(returncode=0, stdout="", stderr=fake_stderr)
        with patch("gracetree_engine.diagnostics.verifier.run_safe", return_value=mock_result):
            intervals = run_blackdetect(Path("/fake/video.mp4"))
        assert intervals == []

    def test_freezedetect_tokenizer_parses_space_separated_value(self):
        """run_freezedetect가 'freeze_start: 1.23' 형태(값이 다음 토큰)를 올바르게 파싱한다."""
        from gracetree_engine.diagnostics.verifier import run_freezedetect
        from unittest.mock import MagicMock, patch

        fake_stderr = (
            "frame=  10 fps=30 ...\n"
            "[freezedetect @ 0x...] freeze_start: 2.000000\n"
            "[freezedetect @ 0x...] freeze_end: 5.000000 freeze_duration: 3.000000\n"
        )
        mock_result = MagicMock(returncode=0, stdout="", stderr=fake_stderr)
        with patch("gracetree_engine.diagnostics.verifier.run_safe", return_value=mock_result):
            intervals = run_freezedetect(Path("/fake/video.mp4"))
        assert len(intervals) == 1
        assert intervals[0]["start"] == pytest.approx(2.0)
        assert intervals[0]["end"] == pytest.approx(5.0)
