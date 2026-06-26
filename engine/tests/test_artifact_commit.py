"""Story 2.9: 최종 산출물 검증과 원자적 커밋 테스트."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gracetree_engine.media.validation import (
    ValidationError,
    validate_final_artifacts,
)
from gracetree_engine.storage.commit import (
    CommitError,
    ARTIFACT_NAMES,
    commit_artifacts,
)


# ─────────────────────── 공통 픽스처 ────────────────────────

_FFPROBE_VALID_OUTPUT = json.dumps({
    "streams": [
        {
            "codec_type": "video",
            "width": 1080,
            "height": 1920,
            "r_frame_rate": "30/1",
            "duration": "30.0",
        },
        {
            "codec_type": "audio",
            "duration": "30.0",
        },
    ],
    "format": {"duration": "30.0"},
})


def _make_valid_attempt_dir(tmp_path: Path) -> Path:
    """유효한 산출물이 들어 있는 attempt 디렉터리를 만든다."""
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "final.mp4").write_bytes(b"x" * 100)
    (attempt / "subtitles.ass").write_text("[Script Info]\n", encoding="utf-8")
    (attempt / "timing.json").write_text('{"version": 1}', encoding="utf-8")
    (attempt / "pipeline-diagnostics.json").write_text('{"stages":[]}', encoding="utf-8")
    return attempt


def _ffprobe_result(stdout: str, returncode: int = 0) -> MagicMock:
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = ""
    return r


# ─────────────────────── Task 1: validate_final_artifacts ────────────────────────

class TestValidateFinalArtifacts:
    def test_valid_attempt_dir_passes(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        with patch("subprocess.run", return_value=_ffprobe_result(_FFPROBE_VALID_OUTPUT)):
            validate_final_artifacts(attempt)  # should not raise

    def test_raises_if_final_mp4_missing(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        (attempt / "final.mp4").unlink()
        with pytest.raises(ValidationError) as exc:
            validate_final_artifacts(attempt)
        assert exc.value.error_code == "MISSING_ARTIFACT"

    def test_raises_if_final_mp4_empty(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        (attempt / "final.mp4").write_bytes(b"")
        with pytest.raises(ValidationError) as exc:
            validate_final_artifacts(attempt)
        assert exc.value.error_code == "MISSING_ARTIFACT"

    def test_raises_if_subtitles_missing(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        (attempt / "subtitles.ass").unlink()
        with patch("subprocess.run", return_value=_ffprobe_result(_FFPROBE_VALID_OUTPUT)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "MISSING_ARTIFACT"

    def test_raises_if_timing_json_missing(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        (attempt / "timing.json").unlink()
        with patch("subprocess.run", return_value=_ffprobe_result(_FFPROBE_VALID_OUTPUT)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "MISSING_ARTIFACT"

    def test_raises_if_timing_json_invalid(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        (attempt / "timing.json").write_text("not json!", encoding="utf-8")
        with patch("subprocess.run", return_value=_ffprobe_result(_FFPROBE_VALID_OUTPUT)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "INVALID_ARTIFACT"

    def test_raises_if_wrong_dimensions(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        wrong_dim = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080,
                 "r_frame_rate": "30/1", "duration": "30.0"},
                {"codec_type": "audio", "duration": "30.0"},
            ],
            "format": {"duration": "30.0"},
        })
        with patch("subprocess.run", return_value=_ffprobe_result(wrong_dim)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "WRONG_DIMENSIONS"

    def test_raises_if_no_video_stream(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        audio_only = json.dumps({
            "streams": [{"codec_type": "audio", "duration": "30.0"}],
            "format": {"duration": "30.0"},
        })
        with patch("subprocess.run", return_value=_ffprobe_result(audio_only)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "NO_VIDEO_STREAM"

    def test_raises_if_no_audio_stream(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        video_only = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "r_frame_rate": "30/1", "duration": "30.0"},
            ],
            "format": {"duration": "30.0"},
        })
        with patch("subprocess.run", return_value=_ffprobe_result(video_only)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "NO_AUDIO_STREAM"

    def test_raises_if_duration_too_short(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        short_dur = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "r_frame_rate": "30/1", "duration": "0.5"},
                {"codec_type": "audio", "duration": "0.5"},
            ],
            "format": {"duration": "0.5"},
        })
        with patch("subprocess.run", return_value=_ffprobe_result(short_dur)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "DURATION_TOO_SHORT"

    def test_raises_if_wrong_fps(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        wrong_fps = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920,
                 "r_frame_rate": "24/1", "duration": "30.0"},
                {"codec_type": "audio", "duration": "30.0"},
            ],
            "format": {"duration": "30.0"},
        })
        with patch("subprocess.run", return_value=_ffprobe_result(wrong_fps)):
            with pytest.raises(ValidationError) as exc:
                validate_final_artifacts(attempt)
        assert exc.value.error_code == "WRONG_FPS"

    def test_does_not_modify_source_files(self, tmp_path):
        attempt = _make_valid_attempt_dir(tmp_path)
        mtime_before = (attempt / "final.mp4").stat().st_mtime
        with patch("subprocess.run", return_value=_ffprobe_result(_FFPROBE_VALID_OUTPUT)):
            validate_final_artifacts(attempt)
        assert (attempt / "final.mp4").stat().st_mtime == mtime_before


# ─────────────────────── Task 2: staging + atomic rename ────────────────────────

class TestCommitArtifacts:
    def _make_dirs(self, tmp_path: Path):
        attempt = _make_valid_attempt_dir(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        return attempt, output, log_dir

    def _mock_repo(self):
        repo = MagicMock()
        repo.complete_attempt = MagicMock()
        return repo

    def test_artifacts_appear_in_output_dir(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=self._mock_repo(),
        )
        for name in ARTIFACT_NAMES:
            assert (output / name).is_file(), f"{name} missing in output"

    def test_complete_attempt_called(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        repo = self._mock_repo()
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=repo,
        )
        repo.complete_attempt.assert_called_once()
        call_kwargs = repo.complete_attempt.call_args[1]
        assert call_kwargs["attempt_id"] == "test-001"
        assert "final.mp4" in call_kwargs["artifact_path"]

    def test_log_copied_to_logs_dir(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=self._mock_repo(),
        )
        assert (log_dir / "test-001-render_log.txt").is_file()

    def test_attempt_dir_cleaned_up(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=self._mock_repo(),
        )
        assert not attempt.exists()

    def test_no_staging_dir_left_after_success(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=self._mock_repo(),
        )
        # No pending/staging dirs should remain
        staging_dirs = list(tmp_path.glob("output.pending.*"))
        assert not staging_dirs, f"Staging dir not cleaned up: {staging_dirs}"

    def test_source_files_not_modified(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        # Confirm originals are removed (moved), not in place
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="test-001",
            attempt_repo=self._mock_repo(),
        )
        # Output should have the files (moved from staging)
        assert (output / "final.mp4").read_bytes() == b"x" * 100


# ─────────────────────── Task 3: 실패 보상 순서 ────────────────────────

class TestFailureCompensation:
    def _make_dirs(self, tmp_path: Path):
        attempt = _make_valid_attempt_dir(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        return attempt, output, log_dir

    def test_staging_failure_leaves_output_unchanged(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        (output / "existing.mp4").write_bytes(b"existing")

        with patch("shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(CommitError) as exc:
                commit_artifacts(
                    attempt_dir=attempt,
                    output_dir=output,
                    log_dir=log_dir,
                    attempt_id="fail-001",
                    attempt_repo=MagicMock(),
                )
        assert exc.value.error_code == "STAGING_FAILED"
        # Output untouched
        assert (output / "existing.mp4").read_bytes() == b"existing"
        assert not (output / "final.mp4").exists()
        # No orphan staging dirs
        assert not list(tmp_path.glob("output.pending.*"))

    def test_db_not_called_if_staging_fails(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        repo = MagicMock()
        with patch("shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(CommitError):
                commit_artifacts(
                    attempt_dir=attempt,
                    output_dir=output,
                    log_dir=log_dir,
                    attempt_id="fail-001",
                    attempt_repo=repo,
                )
        repo.complete_attempt.assert_not_called()

    def test_db_called_once_on_success(self, tmp_path):
        attempt, output, log_dir = self._make_dirs(tmp_path)
        repo = MagicMock()
        commit_artifacts(
            attempt_dir=attempt,
            output_dir=output,
            log_dir=log_dir,
            attempt_id="ok-001",
            attempt_repo=repo,
        )
        assert repo.complete_attempt.call_count == 1


# ─────────────────────── Task 5: 크래시/실패 주입 ────────────────────────

class TestCrashInjection:
    def _make_dirs(self, tmp_path: Path):
        attempt = _make_valid_attempt_dir(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        return attempt, output, log_dir

    def test_existing_output_preserved_if_staging_fails(self, tmp_path):
        """기존 output 파일은 staging 실패 시 보존된다."""
        attempt, output, log_dir = self._make_dirs(tmp_path)
        (output / "final.mp4").write_bytes(b"old-video")

        with patch("shutil.copy2", side_effect=OSError("no space")):
            with pytest.raises(CommitError):
                commit_artifacts(attempt, output, log_dir, "crash-1", MagicMock())

        assert (output / "final.mp4").read_bytes() == b"old-video"

    def test_validation_failure_does_not_touch_output(self, tmp_path):
        """validate 실패 시 output 디렉터리가 변경되면 안 된다."""
        attempt = tmp_path / "attempt"
        attempt.mkdir()
        # final.mp4 누락 → validate_final_artifacts 실패
        (attempt / "subtitles.ass").write_text("x")
        (attempt / "timing.json").write_text("{}")
        output = tmp_path / "output"
        output.mkdir()
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        with pytest.raises(ValidationError):
            validate_final_artifacts(attempt)

        assert list(output.iterdir()) == []

    def test_orphan_staging_dir_not_left_after_rename_failure(self, tmp_path):
        """rename 실패 시 staging 디렉터리가 정리된다."""
        attempt, output, log_dir = self._make_dirs(tmp_path)

        with patch("os.replace", side_effect=OSError("rename failed")):
            with pytest.raises(CommitError) as exc:
                commit_artifacts(attempt, output, log_dir, "crash-2", MagicMock())

        assert exc.value.error_code == "RENAME_FAILED"
        assert not list(tmp_path.glob("output.pending.*"))
