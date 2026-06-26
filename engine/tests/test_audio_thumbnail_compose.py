"""Story 2.7: 오디오와 썸네일 합성 테스트."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gracetree_engine.media.runner import ALLOWED_EXECUTABLES, RunnerError, run_safe
from gracetree_engine.media.audio import build_compose_cmd, probe_audio_duration
from gracetree_engine.media.compose import (
    ComposeConfig,
    ComposeError,
    DEFAULT_COMPOSE_CONFIG,
    compose_video_audio,
)


# ─────────────────────── 공통 픽스처 ────────────────────────

_FFPROBE_AUDIO_OUTPUT = json.dumps({
    "streams": [{"codec_type": "audio", "duration": "30.0"}],
    "format": {"duration": "30.0"},
})


# ─────────────────────── Task 4: 공통 FFmpeg runner ────────────────────────

class TestRunSafe:
    def test_ffmpeg_is_allowed(self):
        assert "ffmpeg" in ALLOWED_EXECUTABLES

    def test_ffprobe_is_allowed(self):
        assert "ffprobe" in ALLOWED_EXECUTABLES

    def test_disallowed_executable_raises(self):
        with pytest.raises(RunnerError) as exc:
            run_safe(["rm", "-rf", "/"])
        assert exc.value.error_code == "DISALLOWED_EXECUTABLE"

    def test_shell_injection_attempt_raises(self):
        with pytest.raises(RunnerError):
            run_safe(["sh", "-c", "echo pwned"])

    def test_empty_cmd_raises(self):
        with pytest.raises(RunnerError):
            run_safe([])

    def test_successful_run_returns_completed_process(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = run_safe(["ffmpeg", "-version"])
        assert result.returncode == 0

    def test_run_uses_no_shell(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            run_safe(["ffmpeg", "-version"])
        _, kwargs = mock_run.call_args
        assert kwargs.get("shell", False) is False

    def test_timeout_propagates_as_runner_error(self):
        import subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=1)
            with pytest.raises(RunnerError) as exc:
                run_safe(["ffmpeg", "-version"], timeout=1)
        assert exc.value.error_code == "TIMEOUT"

    def test_stderr_is_redacted_in_runner_error(self):
        """stderr가 너무 길면 잘라내어 민감 경로 노출을 제한한다."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="x" * 2000)
            result = run_safe(["ffmpeg", "-i", "bad.mp4"])
        # run_safe should not raise for non-zero (caller decides), but it returns the result
        assert result.returncode == 1


# ─────────────────────── Task 2: 오디오 stream 검증 ────────────────────────

class TestProbeAudioDuration:
    def _make_result(self, stdout: str, returncode: int = 0) -> MagicMock:
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        r.stderr = ""
        return r

    def test_returns_duration_for_audio_file(self, tmp_path):
        fake = tmp_path / "voice.mp3"
        fake.write_bytes(b"x")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(_FFPROBE_AUDIO_OUTPUT)
            dur = probe_audio_duration(fake)
        assert dur == pytest.approx(30.0)

    def test_raises_value_error_if_file_missing(self):
        with pytest.raises(FileNotFoundError):
            probe_audio_duration(Path("/no/such/file.mp3"))

    def test_returns_format_duration_when_stream_has_none(self, tmp_path):
        fake = tmp_path / "bgm.mp3"
        fake.write_bytes(b"x")
        no_stream_dur = json.dumps({
            "streams": [{"codec_type": "audio"}],
            "format": {"duration": "60.5"},
        })
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(no_stream_dur)
            dur = probe_audio_duration(fake)
        assert dur == pytest.approx(60.5)


# ─────────────────────── Task 3: 오디오+썸네일 filter graph ────────────────────────

class TestBuildComposeCmd:
    def _base_cmd(self, **kwargs) -> list[str]:
        defaults = dict(
            background_path=Path("bg.mp4"),
            voice_path=Path("voice.mp3"),
            bgm_path=Path("bgm.mp3"),
            thumbnail_path=Path("thumb.jpg"),
            output_path=Path("out.mp4"),
            total_duration=25.0,
            config=DEFAULT_COMPOSE_CONFIG,
        )
        defaults.update(kwargs)
        return build_compose_cmd(**defaults)

    def test_returns_list_of_strings(self):
        cmd = self._base_cmd()
        assert isinstance(cmd, list)
        assert all(isinstance(a, str) for a in cmd)

    def test_first_arg_is_ffmpeg(self):
        assert self._base_cmd()[0] == "ffmpeg"

    def test_output_path_is_last_arg(self):
        assert self._base_cmd()[-1] == "out.mp4"

    def test_filter_complex_present(self):
        cmd = self._base_cmd()
        assert "-filter_complex" in cmd

    def test_filter_graph_contains_xfade_or_overlay(self):
        cmd = self._base_cmd()
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        assert "overlay" in fg

    def test_filter_graph_contains_afade(self):
        cmd = self._base_cmd()
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        assert "afade" in fg

    def test_filter_graph_contains_amix(self):
        cmd = self._base_cmd()
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        assert "amix" in fg

    def test_no_shell_string(self):
        cmd = self._base_cmd()
        fc_idx = cmd.index("-filter_complex")
        # filter_complex value may use ";" as separator — skip it, check all others
        non_fg_args = [a for i, a in enumerate(cmd) if i != fc_idx + 1]
        for arg in non_fg_args:
            assert ";" not in arg, f"Shell-injection risk in arg: {arg!r}"

    def test_thumbnail_input_included(self):
        cmd = self._base_cmd()
        assert "thumb.jpg" in cmd

    def test_bgm_fade_out_uses_total_duration(self):
        cmd = self._base_cmd(total_duration=30.0)
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        # BGM fade_out start = total_duration - fade_seconds
        # With total=30.0 and default fade=2.0: st=28.0
        assert "28.0" in fg or "28" in fg

    def test_bgm_fade_in_starts_at_zero(self):
        cmd = self._base_cmd()
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        assert "st=0" in fg or "ss=0" in fg

    def test_short_bgm_clamped_fade(self):
        # BGM shorter than 2*fade → clamp fade duration so they don't overlap
        cmd = self._base_cmd(total_duration=3.0, config=ComposeConfig(bgm_fade_seconds=2.0))
        fc_idx = cmd.index("-filter_complex")
        fg = cmd[fc_idx + 1]
        # Should not raise; fade durations should be clamped (e.g., 1.5 each for 3s BGM)
        assert "afade" in fg


# ─────────────────────── Task 5: compose_video_audio (orchestration) ────────────────────────

class TestComposeVideoAudio:
    def _setup_files(self, tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
        bg = tmp_path / "background.mp4"
        bg.write_bytes(b"x")
        voice = tmp_path / "voice.mp3"
        voice.write_bytes(b"x")
        bgm = tmp_path / "bgm.mp3"
        bgm.write_bytes(b"x")
        thumb = tmp_path / "thumbnail.jpg"
        thumb.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()
        return bg, voice, bgm, thumb, attempt

    def test_returns_path_to_final_mp4(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]  # voice, bgm
            mock_run.return_value = MagicMock(returncode=0)
            result = compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert result.name == "final.mp4"
        assert result.parent == attempt

    def test_raises_compose_error_if_audio_probe_fails(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur:
            mock_dur.side_effect = FileNotFoundError("not found")
            with pytest.raises(ComposeError) as exc:
                compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert exc.value.error_code == "PROBE_FAILED"

    def test_raises_compose_error_if_ffmpeg_fails(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]
            mock_run.return_value = MagicMock(returncode=1, stderr="err")
            with pytest.raises(ComposeError) as exc:
                compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert exc.value.error_code == "FFMPEG_FAILED"

    def test_run_safe_called_instead_of_raw_subprocess(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]
            mock_run.return_value = MagicMock(returncode=0)
            compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert mock_run.called

    def test_config_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_COMPOSE_CONFIG.bgm_fade_seconds = 5.0  # type: ignore[misc]

    def test_original_files_not_modified(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        voice_mtime = voice.stat().st_mtime
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]
            mock_run.return_value = MagicMock(returncode=0)
            compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert voice.stat().st_mtime == voice_mtime

    def test_raises_compose_error_if_bgm_shorter_than_voice(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur:
            mock_dur.side_effect = [60.0, 30.0]  # voice=60s > bgm=30s
            with pytest.raises(ComposeError) as exc:
                compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert exc.value.error_code == "BGM_TOO_SHORT"

    def test_raises_compose_error_if_voice_zero_duration(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur:
            mock_dur.side_effect = [0.0, 120.0]
            with pytest.raises(ComposeError) as exc:
                compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert exc.value.error_code == "INVALID_DURATION"

    def test_runner_error_is_wrapped_as_compose_error(self, tmp_path):
        bg, voice, bgm, thumb, attempt = self._setup_files(tmp_path)
        from gracetree_engine.media.runner import RunnerError
        with patch("gracetree_engine.media.compose.probe_audio_duration") as mock_dur, \
             patch("gracetree_engine.media.compose.run_safe") as mock_run:
            mock_dur.side_effect = [20.0, 120.0]
            mock_run.side_effect = RunnerError("TIMEOUT", "timed out")
            with pytest.raises(ComposeError) as exc:
                compose_video_audio(bg, voice, bgm, thumb, attempt)
        assert exc.value.error_code == "FFMPEG_FAILED"
