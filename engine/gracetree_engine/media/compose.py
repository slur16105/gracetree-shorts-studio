"""Story 2.7: Final video+audio+thumbnail composition orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audio import build_compose_cmd, probe_audio_duration
from .runner import RunnerError, run_safe


@dataclass(frozen=True)
class ComposeConfig:
    bgm_fade_seconds: float = 2.0


DEFAULT_COMPOSE_CONFIG = ComposeConfig()


class ComposeError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def compose_video_audio(
    background_path: Path,
    voice_path: Path,
    bgm_path: Path,
    thumbnail_path: Path,
    attempt_dir: Path,
    config: ComposeConfig = DEFAULT_COMPOSE_CONFIG,
    subtitle_path: Path | None = None,
    fontsdir: Path | None = None,
) -> Path:
    """Compose final.mp4 from background video, voice, BGM, and thumbnail.

    When subtitle_path is given, the .ass subtitle is burned into the video via
    libass; fontsdir lets libass resolve the Korean font.

    Raises ComposeError on probe or ffmpeg failure.
    Does not modify any source file.
    """
    try:
        voice_duration = probe_audio_duration(voice_path)
        bgm_duration = probe_audio_duration(bgm_path)
    except Exception as exc:
        raise ComposeError("PROBE_FAILED", str(exc)) from exc

    if voice_duration <= 0:
        raise ComposeError("INVALID_DURATION", "음성 파일의 재생 시간이 유효하지 않습니다.")

    if bgm_duration < voice_duration:
        raise ComposeError(
            "BGM_TOO_SHORT",
            f"BGM 재생 시간({bgm_duration:.2f}s)이 음성({voice_duration:.2f}s)보다 짧습니다. "
            "BGM이 부족하면 오디오 테일이 무음 처리됩니다.",
        )

    total_duration = voice_duration
    output_path = attempt_dir / "final.mp4"

    cmd = build_compose_cmd(
        background_path=background_path,
        voice_path=voice_path,
        bgm_path=bgm_path,
        thumbnail_path=thumbnail_path,
        output_path=output_path,
        total_duration=total_duration,
        config=config,
        subtitle_path=subtitle_path,
        fontsdir=fontsdir,
    )

    try:
        result = run_safe(cmd)
    except RunnerError as exc:
        raise ComposeError("FFMPEG_FAILED", str(exc)) from exc

    if result.returncode != 0:
        raise ComposeError(
            "FFMPEG_FAILED",
            f"FFmpeg 실패: {result.stderr[:500]}",
        )

    return output_path
