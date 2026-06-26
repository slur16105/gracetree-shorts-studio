"""Story 2.6: Background video composition orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .probe import ProbeError, VideoInfo, probe_video
from .ffmpeg import build_background_cmd
from .runner import RunnerError, run_safe


@dataclass(frozen=True)
class BackgroundConfig:
    crossfade_seconds: float = 0.5
    tail_seconds: float = 3.0


DEFAULT_BACKGROUND_CONFIG = BackgroundConfig()


class BackgroundError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _extract_timing(timing: dict[str, Any]) -> tuple[float, float]:
    """Return (intro_target, prayer_end) from timing.json dict."""
    blocks = timing.get("subtitleBlocks", [])
    if not blocks:
        raise BackgroundError(
            "MISSING_TIMING",
            "subtitleBlocks가 비어 있거나 없습니다. 음성 정렬이 완료된 후 배경을 합성하세요.",
        )
    start = blocks[0].get("startTime")
    end = blocks[-1].get("endTime")
    if start is None or end is None:
        raise BackgroundError(
            "MISSING_TIMING",
            "subtitleBlocks 항목에 startTime 또는 endTime이 없습니다.",
        )
    return float(start), float(end)


def compose_background(
    intro_path: Path,
    loop_path: Path,
    timing: dict[str, Any],
    attempt_dir: Path,
    config: BackgroundConfig = DEFAULT_BACKGROUND_CONFIG,
) -> Path:
    """Compose background video and write to attempt_dir/background.mp4.

    Raises BackgroundError on probe or ffmpeg failure.
    """
    try:
        intro_info = probe_video(intro_path)
        loop_info = probe_video(loop_path)
    except ProbeError as exc:
        raise BackgroundError("PROBE_FAILED", str(exc)) from exc

    if intro_info.width != loop_info.width or intro_info.height != loop_info.height:
        raise BackgroundError(
            "DIMENSION_MISMATCH",
            f"intro ({intro_info.width}×{intro_info.height}) vs "
            f"loop ({loop_info.width}×{loop_info.height}) 해상도가 다릅니다.",
        )

    intro_target, prayer_end = _extract_timing(timing)
    output_path = attempt_dir / "background.mp4"

    cmd = build_background_cmd(
        intro_path=intro_path,
        intro_info=intro_info,
        loop_path=loop_path,
        loop_info=loop_info,
        output_path=output_path,
        intro_target=intro_target,
        prayer_end=prayer_end,
        config=config,
    )

    try:
        result = run_safe(cmd)
    except RunnerError as exc:
        raise BackgroundError("FFMPEG_FAILED", str(exc)) from exc

    if result.returncode != 0:
        raise BackgroundError(
            "FFMPEG_FAILED",
            f"FFmpeg 실패: {result.stderr[:500]}",
        )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise BackgroundError(
            "OUTPUT_MISSING",
            "FFmpeg가 성공했지만 background.mp4가 생성되지 않았습니다.",
        )

    return output_path
