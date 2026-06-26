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
) -> Path:
    """Compose final.mp4 from background video, voice, BGM, and thumbnail.

    Raises ComposeError on probe or ffmpeg failure.
    Does not modify any source file.
    """
    try:
        voice_duration = probe_audio_duration(voice_path)
        _bgm_duration = probe_audio_duration(bgm_path)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ComposeError("PROBE_FAILED", str(exc)) from exc

    # Total output duration is driven by voice length
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
