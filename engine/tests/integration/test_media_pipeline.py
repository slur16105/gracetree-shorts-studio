"""Story 2.8: FFmpeg 파이프라인 통합 테스트.

이 테스트는 ffmpeg/ffprobe가 설치된 환경에서만 실행됩니다.
CI에서는 SKIP됩니다.
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import time
import zlib
from pathlib import Path

import pytest

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None
REQUIRES_FFMPEG = pytest.mark.skipif(
    not (FFMPEG_AVAILABLE and FFPROBE_AVAILABLE),
    reason="ffmpeg/ffprobe not installed",
)


# ─────────────────────── 픽스처 생성 헬퍼 ────────────────────────

def _make_wav(path: Path, duration: float = 3.0, sample_rate: int = 16000,
              channels: int = 1) -> Path:
    num_samples = int(sample_rate * duration)
    data_size = num_samples * 2 * channels
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                            sample_rate * 2 * channels, 2 * channels, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
    return path


def _make_png(path: Path, width: int = 1080, height: int = 1920) -> Path:
    """Create a minimal black PNG using raw Python (no Pillow needed)."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_data = b"".join(b"\x00" + b"\x00" * (width * 3) for _ in range(height))
    idat_data = zlib.compress(raw_data)

    png = (
        b"\x89PNG\r\n\x1a\n" +
        chunk(b"IHDR", ihdr) +
        chunk(b"IDAT", idat_data) +
        chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    return path


def _make_mp4(path: Path, duration: float = 5.0, width: int = 1080, height: int = 1920) -> Path:
    """Create a black video MP4 using ffmpeg lavfi."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:size={width}x{height}:rate=30:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "51",
        "-pix_fmt", "yuv420p",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"MP4 생성 실패: {result.stderr.decode()[:200]}")
    return path


def _make_script(path: Path) -> Path:
    path.write_text(
        "제목: 오늘의 기도\n"
        "말씀: 주를 사랑하고 이웃을 사랑하라.\n"
        "기도:\n"
        "주님 감사합니다.\n"
        "아멘.\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="module")
def fixtures_dir(tmp_path_factory):
    """Module-scoped fixture directory with all synthetic media."""
    d = tmp_path_factory.mktemp("integration_fixtures")
    _make_wav(d / "voice.wav", duration=8.0)
    _make_wav(d / "bgm.wav", duration=20.0, sample_rate=44100, channels=2)
    _make_png(d / "thumbnail.png")
    _make_script(d / "script.txt")
    return d


# ─────────────────────── Task 2: 통합 파이프라인 하네스 ────────────────────────

class TestPipelineHarness:
    @REQUIRES_FFMPEG
    def test_background_compose_produces_video(self, fixtures_dir, tmp_path):
        """Story 2.6: compose_background로 background.mp4가 생성된다."""
        from gracetree_engine.media.background import compose_background, DEFAULT_BACKGROUND_CONFIG

        intro = tmp_path / "intro.mp4"
        loop = tmp_path / "loop.mp4"
        _make_mp4(intro, duration=5.0)
        _make_mp4(loop, duration=8.0)

        timing = {
            "version": 1,
            "voiceOffset": 5.0,
            "subtitleBlocks": [
                {"index": 0, "startTime": 5.0, "endTime": 12.0, "text": "주님 감사합니다."},
                {"index": 1, "startTime": 12.0, "endTime": 15.0, "text": "아멘."},
            ],
        }
        result = compose_background(intro, loop, timing, tmp_path, DEFAULT_BACKGROUND_CONFIG)
        assert result.exists()
        assert result.name == "background.mp4"

    @REQUIRES_FFMPEG
    def test_subtitle_generation_produces_ass(self, fixtures_dir, tmp_path):
        """Story 2.5: generate_subtitles로 subtitles.ass가 생성된다."""
        from gracetree_engine.subtitles.generator import generate_subtitles
        from gracetree_engine.subtitles.config import DEFAULT_SUBTITLE_CONFIG

        script_ast = {
            "title": "오늘의 기도",
            "scripture": "주를 사랑하고 이웃을 사랑하라.",
            "subtitleBlocks": [
                {"index": 0, "text": "주님 감사합니다.", "lines": ["주님 감사합니다."]},
                {"index": 1, "text": "아멘.", "lines": ["아멘."]},
            ],
        }
        timing = {
            "version": 1,
            "voiceOffset": 5.0,
            "subtitleBlocks": [
                {"index": 0, "startTime": 5.0, "endTime": 12.0, "text": "주님 감사합니다.", "lines": ["주님 감사합니다."]},
                {"index": 1, "startTime": 12.0, "endTime": 15.0, "text": "아멘.", "lines": ["아멘."]},
            ],
        }
        result = generate_subtitles(script_ast, timing, tmp_path, DEFAULT_SUBTITLE_CONFIG)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "[Events]" in content

    @REQUIRES_FFMPEG
    def test_full_audio_compose_produces_final(self, fixtures_dir, tmp_path):
        """Story 2.7: compose_video_audio로 final.mp4가 생성된다."""
        from gracetree_engine.media.compose import compose_video_audio, DEFAULT_COMPOSE_CONFIG

        bg = tmp_path / "background.mp4"
        _make_mp4(bg, duration=10.0)
        attempt = tmp_path / "attempt"
        attempt.mkdir()

        result = compose_video_audio(
            background_path=bg,
            voice_path=fixtures_dir / "voice.wav",
            bgm_path=fixtures_dir / "bgm.wav",
            thumbnail_path=fixtures_dir / "thumbnail.png",
            attempt_dir=attempt,
            config=DEFAULT_COMPOSE_CONFIG,
        )
        assert result.exists()
        assert result.name == "final.mp4"


# ─────────────────────── Task 3: ffprobe 스트림 검증 ────────────────────────

class TestFFprobeVerification:
    @REQUIRES_FFMPEG
    def test_background_mp4_has_video_stream(self, tmp_path):
        from gracetree_engine.diagnostics.verifier import probe_file, verify_streams

        mp4 = tmp_path / "bg.mp4"
        _make_mp4(mp4, duration=5.0)
        info = probe_file(mp4)
        verify_streams(info, require_video=True, require_audio=False)

    @REQUIRES_FFMPEG
    def test_final_mp4_has_video_and_audio(self, fixtures_dir, tmp_path):
        from gracetree_engine.media.compose import compose_video_audio, DEFAULT_COMPOSE_CONFIG
        from gracetree_engine.diagnostics.verifier import probe_file, verify_streams

        bg = tmp_path / "background.mp4"
        _make_mp4(bg, duration=10.0)
        attempt = tmp_path / "attempt"; attempt.mkdir()

        result = compose_video_audio(
            background_path=bg,
            voice_path=fixtures_dir / "voice.wav",
            bgm_path=fixtures_dir / "bgm.wav",
            thumbnail_path=fixtures_dir / "thumbnail.png",
            attempt_dir=attempt,
        )
        info = probe_file(result)
        verify_streams(info, require_video=True, require_audio=True)

    @REQUIRES_FFMPEG
    def test_background_mp4_dimensions_correct(self, tmp_path):
        from gracetree_engine.diagnostics.verifier import probe_file, verify_dimensions, verify_streams

        mp4 = tmp_path / "bg.mp4"
        _make_mp4(mp4, duration=5.0, width=1080, height=1920)
        info = probe_file(mp4)
        vs = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
        assert vs is not None, "ffprobe가 비디오 스트림을 보고하지 않았습니다"
        verify_dimensions(vs["width"], vs["height"], 1080, 1920)


# ─────────────────────── Task 4: 진단 로거 통합 ────────────────────────

class TestDiagnosticsIntegration:
    @REQUIRES_FFMPEG
    def test_diagnostics_log_written_after_pipeline(self, fixtures_dir, tmp_path):
        """실제 파이프라인 실행 후 진단 로그가 기록된다."""
        from gracetree_engine.diagnostics.logger import PipelineDiagnostics
        from gracetree_engine.media.compose import compose_video_audio

        bg = tmp_path / "bg.mp4"
        _make_mp4(bg, duration=10.0)
        attempt = tmp_path / "attempt"; attempt.mkdir()
        diag = PipelineDiagnostics(attempt_dir=attempt)

        with diag.stage("compose_audio"):
            compose_video_audio(bg, fixtures_dir / "voice.wav",
                                fixtures_dir / "bgm.wav", fixtures_dir / "thumbnail.png",
                                attempt)

        diag.write_log()
        log = attempt / "pipeline-diagnostics.json"
        assert log.exists()
        data = json.loads(log.read_text())
        assert data["stages"][0]["name"] == "compose_audio"
        assert data["stages"][0]["wall_time"] > 0
