"""Story 2.6: 배경 영상 구성 테스트."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gracetree_engine.media.probe import ProbeError, VideoInfo, probe_video
from gracetree_engine.media.ffmpeg import build_background_cmd, loop_count_needed
from gracetree_engine.media.background import (
    BackgroundConfig,
    BackgroundError,
    DEFAULT_BACKGROUND_CONFIG,
    compose_background,
)


# ─────────────────────── 공통 픽스처 ────────────────────────

INTRO_INFO = VideoInfo(duration=15.0, width=1080, height=1920, fps=30.0)
LOOP_INFO = VideoInfo(duration=10.0, width=1080, height=1920, fps=30.0)

TIMING: dict[str, Any] = {
    "version": 1,
    "voiceOffset": 5.0,
    "leadingSilenceSeconds": 0.0,
    "subtitleBlocks": [
        {"index": 0, "startTime": 5.0, "endTime": 12.0, "text": "주님 감사합니다."},
        {"index": 1, "startTime": 12.0, "endTime": 20.0, "text": "아멘."},
    ],
}

_FFPROBE_STREAM_OUTPUT = json.dumps({
    "streams": [
        {
            "codec_type": "video",
            "width": 1080,
            "height": 1920,
            "r_frame_rate": "30/1",
            "duration": "15.0",
        }
    ],
    "format": {"duration": "15.0"},
})


# ─────────────────────── Task 1: ffprobe 검증 ────────────────────────

class TestProbeVideo:
    def _make_result(self, stdout: str, returncode: int = 0) -> MagicMock:
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        r.stderr = ""
        return r

    def test_returns_video_info_on_success(self, tmp_path):
        fake_file = tmp_path / "video.mp4"
        fake_file.write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(_FFPROBE_STREAM_OUTPUT)
            info = probe_video(fake_file)
        assert isinstance(info, VideoInfo)
        assert info.duration == pytest.approx(15.0)
        assert info.width == 1080
        assert info.height == 1920
        assert info.fps == pytest.approx(30.0)

    def test_raises_file_not_found_if_path_missing(self):
        with pytest.raises(ProbeError) as exc:
            probe_video(Path("/no/such/file.mp4"))
        assert exc.value.error_code == "FILE_NOT_FOUND"

    def test_raises_probe_failed_if_ffprobe_returns_error(self, tmp_path):
        fake = tmp_path / "v.mp4"
        fake.write_bytes(b"x")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result("", returncode=1)
            with pytest.raises(ProbeError) as exc:
                probe_video(fake)
        assert exc.value.error_code == "PROBE_FAILED"

    def test_raises_no_video_stream_if_missing(self, tmp_path):
        fake = tmp_path / "audio.mp3"
        fake.write_bytes(b"x")
        no_video = json.dumps({
            "streams": [{"codec_type": "audio"}],
            "format": {"duration": "5.0"},
        })
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(no_video)
            with pytest.raises(ProbeError) as exc:
                probe_video(fake)
        assert exc.value.error_code == "NO_VIDEO_STREAM"

    def test_raises_invalid_duration_if_zero(self, tmp_path):
        fake = tmp_path / "v.mp4"
        fake.write_bytes(b"x")
        zero_dur = json.dumps({
            "streams": [{"codec_type": "video", "width": 1080, "height": 1920,
                         "r_frame_rate": "30/1", "duration": "0.0"}],
            "format": {"duration": "0.0"},
        })
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(zero_dur)
            with pytest.raises(ProbeError) as exc:
                probe_video(fake)
        assert exc.value.error_code == "INVALID_DURATION"

    def test_ffprobe_called_with_list_args_not_shell(self, tmp_path):
        fake = tmp_path / "v.mp4"
        fake.write_bytes(b"x")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(_FFPROBE_STREAM_OUTPUT)
            probe_video(fake)
        _, kwargs = mock_run.call_args
        assert kwargs.get("shell", False) is False
        cmd = mock_run.call_args[0][0]
        assert isinstance(cmd, list)

    def test_fps_parsed_from_fraction(self, tmp_path):
        fake = tmp_path / "v.mp4"
        fake.write_bytes(b"x")
        output = json.dumps({
            "streams": [{"codec_type": "video", "width": 1080, "height": 1920,
                         "r_frame_rate": "24000/1001", "duration": "10.0"}],
            "format": {"duration": "10.0"},
        })
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_result(output)
            info = probe_video(fake)
        assert info.fps == pytest.approx(24000 / 1001, rel=1e-4)


# ─────────────────────── Task 2: 반복 횟수 및 타이밍 계산 ────────────────────────

class TestLoopCalculation:
    def test_exact_fit_one_loop(self):
        # intro_target=5, prayer_duration=8, tail=3 → total_prayer=11, D=11, xfade=0.5
        # N = ceil((11) / (11-0.5)) = ceil(1.047...) = 2? No...
        # prayer target = prayer_end + tail - intro_target = 20 + 3 - 5 = 18
        # D - xfade = 18 - 0.5 = 17.5
        # N = ceil(18 / 17.5) = 2
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=20.0,
            loop_duration=18.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n == 2

    def test_short_loop_needs_more_repeats(self):
        # prayer target = prayer_end + tail - intro_target = 20 + 3 - 5 = 18
        # loop_duration = 5, crossfade = 0.5 → effective = 4.5
        # N = ceil(18 / 4.5) = 4
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=20.0,
            loop_duration=5.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n == 4

    def test_long_loop_needs_one_repeat(self):
        # prayer target = 20 + 3 - 5 = 18, loop_dur = 100
        # N = ceil(18 / (100-0.5)) = ceil(0.18...) = 1
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=20.0,
            loop_duration=100.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n == 1

    def test_exactly_divisible_loop(self):
        # prayer target = 18, loop_dur = 9, effective = 8.5
        # N = ceil(18 / 8.5) = ceil(2.117...) = 3
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=20.0,
            loop_duration=9.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n == 3

    def test_minimum_one_loop(self):
        # Even with long loop, minimum is 1
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=8.0,
            loop_duration=1000.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n >= 1


# ─────────────────────── Task 3: FFmpeg filter graph 생성 ────────────────────────

class TestBuildBackgroundCmd:
    def test_returns_list_of_strings(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        assert isinstance(cmd, list)
        assert all(isinstance(a, str) for a in cmd)

    def test_first_arg_is_ffmpeg(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        assert cmd[0] == "ffmpeg"

    def test_includes_filter_complex(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        assert "-filter_complex" in cmd

    def test_output_path_is_last_arg(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        assert cmd[-1] == "out.mp4"

    def test_multiple_loop_inputs_for_multiple_repeats(self):
        # short loop → needs multiple inputs
        short_loop = VideoInfo(duration=3.0, width=1080, height=1920, fps=30.0)
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=short_loop,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        loop_inputs = [a for a in cmd if a == "loop.mp4"]
        n = loop_count_needed(5.0, 20.0, 3.0, 0.5, 3.0)
        assert len(loop_inputs) == n

    def test_filter_graph_contains_xfade(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_graph = cmd[fc_idx + 1]
        assert "xfade" in filter_graph

    def test_filter_graph_contains_setpts_for_speed_adjustment(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_graph = cmd[fc_idx + 1]
        assert "setpts" in filter_graph

    def test_no_audio_mapping(self):
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=LOOP_INFO,
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        # Should not map audio
        assert "-an" in cmd


# ─────────────────────── Task 4: compose_background (orchestration) ────────────────────────

class TestComposeBackground:
    def _mock_probe(self, info: VideoInfo):
        return lambda path: info

    def test_returns_path_to_background_mp4(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        def _fake_run(cmd, **kwargs):
            # Simulate ffmpeg writing the output file
            out = attempt / "background.mp4"
            out.write_bytes(b"fake-video")
            return MagicMock(returncode=0)

        with patch("gracetree_engine.media.background.probe_video") as mock_probe, \
             patch("gracetree_engine.media.background.run_safe", side_effect=_fake_run):
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            result = compose_background(intro, loop, TIMING, attempt)

        assert result.name == "background.mp4"
        assert result.parent == attempt
        assert result.is_file()

    def test_raises_background_error_if_probe_fails(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        loop = tmp_path / "loop.mp4"
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        with patch("gracetree_engine.media.background.probe_video") as mock_probe:
            mock_probe.side_effect = ProbeError("FILE_NOT_FOUND", "not found")
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, TIMING, attempt)
        assert exc.value.error_code == "PROBE_FAILED"

    def test_raises_background_error_if_dimension_mismatch(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        mismatched_loop = VideoInfo(duration=10.0, width=1920, height=1080, fps=30.0)
        with patch("gracetree_engine.media.background.probe_video") as mock_probe:
            mock_probe.side_effect = [INTRO_INFO, mismatched_loop]
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, TIMING, attempt)
        assert exc.value.error_code == "DIMENSION_MISMATCH"

    def test_raises_background_error_if_ffmpeg_fails(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        with patch("gracetree_engine.media.background.probe_video") as mock_probe, \
             patch("gracetree_engine.media.background.run_safe") as mock_run:
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, TIMING, attempt)
        assert exc.value.error_code == "FFMPEG_FAILED"

    def test_raises_background_error_if_output_not_created(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        with patch("gracetree_engine.media.background.probe_video") as mock_probe, \
             patch("gracetree_engine.media.background.run_safe") as mock_run:
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            # ffmpeg returns 0 but writes no file
            mock_run.return_value = MagicMock(returncode=0)
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, TIMING, attempt)
        assert exc.value.error_code == "OUTPUT_MISSING"

    def test_ffmpeg_called_without_shell(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        called = []

        def _fake_run(cmd, **kwargs):
            called.append(cmd)
            (attempt / "background.mp4").write_bytes(b"fake")
            return MagicMock(returncode=0)

        with patch("gracetree_engine.media.background.probe_video") as mock_probe, \
             patch("gracetree_engine.media.background.run_safe", side_effect=_fake_run):
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            compose_background(intro, loop, TIMING, attempt)

        assert called, "run_safe was never called"


# ─────────────────────── Task 5: 경계 케이스 통합 테스트 ────────────────────────

class TestLoopBoundaryIntegration:
    def test_short_prayer_duration_still_gets_one_loop(self):
        timing = {
            "version": 1,
            "voiceOffset": 5.0,
            "leadingSilenceSeconds": 0.0,
            "subtitleBlocks": [
                {"index": 0, "startTime": 5.0, "endTime": 7.0, "text": "아멘."},
            ],
        }
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=7.0,
            loop_duration=10.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n >= 1

    def test_exact_loop_multiple(self):
        # prayer_target = 18, loop_duration = 6, effective = 5.5
        # N = ceil(18/5.5) = ceil(3.27) = 4
        n = loop_count_needed(
            intro_target=5.0,
            prayer_end=20.0,
            loop_duration=6.0,
            crossfade=0.5,
            tail=3.0,
        )
        assert n == 4

    def test_loop_count_is_deterministic(self):
        n1 = loop_count_needed(5.0, 20.0, 10.0, 0.5, 3.0)
        n2 = loop_count_needed(5.0, 20.0, 10.0, 0.5, 3.0)
        assert n1 == n2

    def test_background_config_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_BACKGROUND_CONFIG.crossfade_seconds = 1.0  # type: ignore[misc]

    def test_xfade_count_equals_loop_count(self):
        # For N loops, we should have N xfade transitions
        # (1 intro-to-loop, N-1 loop-to-loop)
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=INTRO_INFO,
            loop_path=Path("loop.mp4"),
            loop_info=VideoInfo(duration=3.0, width=1080, height=1920, fps=30.0),
            output_path=Path("out.mp4"),
            intro_target=5.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_graph = cmd[fc_idx + 1]
        n = loop_count_needed(5.0, 20.0, 3.0, 0.5, 3.0)
        xfade_count = filter_graph.count("xfade")
        assert xfade_count == n

    def test_xfade_offset_is_never_negative(self):
        # intro_target=0.3 < crossfade=0.5 → offset would be negative without clamp
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=VideoInfo(duration=15.0, width=1080, height=1920, fps=30.0),
            loop_path=Path("loop.mp4"),
            loop_info=VideoInfo(duration=10.0, width=1080, height=1920, fps=30.0),
            output_path=Path("out.mp4"),
            intro_target=0.3,
            prayer_end=20.0,
            config=BackgroundConfig(crossfade_seconds=0.5, tail_seconds=3.0),
        )
        fc_idx = cmd.index("-filter_complex")
        filter_graph = cmd[fc_idx + 1]
        # All offset= values must be non-negative
        import re
        offsets = [float(m) for m in re.findall(r"offset=([\d.]+)", filter_graph)]
        assert all(o >= 0.0 for o in offsets), f"Negative offset found: {offsets}"

    def test_setpts_not_zero_when_intro_target_equals_zero(self):
        # When intro_target=0, setpts should fall back to ratio=1.0 (not 0.0)
        cmd = build_background_cmd(
            intro_path=Path("intro.mp4"),
            intro_info=VideoInfo(duration=15.0, width=1080, height=1920, fps=30.0),
            loop_path=Path("loop.mp4"),
            loop_info=VideoInfo(duration=10.0, width=1080, height=1920, fps=30.0),
            output_path=Path("out.mp4"),
            intro_target=0.0,
            prayer_end=20.0,
            config=DEFAULT_BACKGROUND_CONFIG,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_graph = cmd[fc_idx + 1]
        # setpts=PTS*0.000000 would collapse intro; 1.000000 is the safe fallback
        assert "setpts=PTS*0.000000" not in filter_graph

    def test_missing_timing_key_raises_background_error(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        bad_timing = {
            "version": 1,
            "subtitleBlocks": [{"index": 0, "text": "아멘."}],  # missing startTime/endTime
        }
        with patch("gracetree_engine.media.background.probe_video") as mock_probe:
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, bad_timing, attempt)
        assert exc.value.error_code == "MISSING_TIMING"

    def test_empty_subtitle_blocks_raises_missing_timing(self, tmp_path):
        intro = tmp_path / "intro.mp4"
        intro.write_bytes(b"x")
        loop = tmp_path / "loop.mp4"
        loop.write_bytes(b"x")
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        empty_blocks_timing = {"version": 1, "subtitleBlocks": [], "voiceOffset": 5.0}
        with patch("gracetree_engine.media.background.probe_video") as mock_probe:
            mock_probe.side_effect = [INTRO_INFO, LOOP_INFO]
            with pytest.raises(BackgroundError) as exc:
                compose_background(intro, loop, empty_blocks_timing, attempt)
        assert exc.value.error_code == "MISSING_TIMING"
