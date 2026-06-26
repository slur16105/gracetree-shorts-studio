"""Story 2.8: Post-generation ffprobe stream and quality verification."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..media.runner import RunnerError, run_safe
from .logger import redact_paths


class VerificationError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def probe_file(path: Path) -> dict[str, Any]:
    """Run ffprobe on path and return parsed JSON.

    Raises VerificationError(FILE_NOT_FOUND) if path is absent.
    Raises VerificationError(PROBE_FAILED) if ffprobe fails.
    """
    if not path.exists():
        raise VerificationError("FILE_NOT_FOUND", f"파일을 찾을 수 없습니다: {path.name}")

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(path),
    ]
    try:
        result = run_safe(cmd)
    except RunnerError as exc:
        raise VerificationError("PROBE_FAILED", redact_paths(str(exc))) from exc

    if result.returncode != 0:
        raise VerificationError(
            "PROBE_FAILED",
            f"ffprobe 실패: {redact_paths(result.stderr[:200])}",
        )
    return json.loads(result.stdout)


def verify_streams(
    info: dict[str, Any],
    require_video: bool = True,
    require_audio: bool = False,
) -> None:
    """Verify stream presence. Raises VerificationError on failure."""
    streams = info.get("streams", [])
    codec_types = {s.get("codec_type") for s in streams}
    if require_video and "video" not in codec_types:
        raise VerificationError("NO_VIDEO_STREAM", "비디오 스트림이 없습니다.")
    if require_audio and "audio" not in codec_types:
        raise VerificationError("NO_AUDIO_STREAM", "오디오 스트림이 없습니다.")


def verify_dimensions(
    width: int,
    height: int,
    expected_width: int,
    expected_height: int,
) -> None:
    """Verify video dimensions. Raises VerificationError on mismatch."""
    if width != expected_width or height != expected_height:
        raise VerificationError(
            "WRONG_DIMENSIONS",
            f"해상도 불일치: {width}×{height} (기대값: {expected_width}×{expected_height})",
        )


def verify_duration(actual: float, minimum: float) -> None:
    """Verify video duration meets minimum. Raises VerificationError if too short."""
    if actual < minimum:
        raise VerificationError(
            "DURATION_TOO_SHORT",
            f"재생 시간이 너무 짧습니다: {actual:.2f}s (최소: {minimum:.2f}s)",
        )


def run_blackdetect(path: Path, threshold: float = 0.98) -> list[dict[str, float]]:
    """Run ffmpeg blackdetect and return list of black intervals.

    Each interval: {"start": float, "end": float, "duration": float}
    Returns [] if ffmpeg is unavailable or the input has no black frames.
    Raises VerificationError on non-zero ffmpeg exit.
    """
    cmd = [
        "ffmpeg", "-i", str(path),
        "-vf", f"blackdetect=d=0.1:pix_th={threshold}",
        "-an", "-f", "null", "-",
    ]
    try:
        result = run_safe(cmd)
    except RunnerError:
        return []

    if result.returncode != 0:
        raise VerificationError(
            "BLACKDETECT_FAILED",
            f"blackdetect 실패: {redact_paths(result.stderr[:200])}",
        )

    intervals = []
    for line in result.stderr.splitlines():
        if "black_start" in line:
            parts: dict[str, float] = {}
            for token in line.split():
                if ":" in token:
                    k, _, v = token.partition(":")
                    try:
                        parts[k] = float(v)
                    except ValueError:
                        pass
            if "black_start" in parts:
                intervals.append({
                    "start": parts.get("black_start", 0.0),
                    "end": parts.get("black_end", 0.0),
                    "duration": parts.get("black_duration", 0.0),
                })
    return intervals


def run_freezedetect(path: Path, noise: float = -60.0, duration: float = 2.0) -> list[dict]:
    """Run ffmpeg freezedetect and return list of frozen intervals.

    Each interval: {"start": float, "end": float}
    Raises VerificationError on non-zero ffmpeg exit.
    """
    cmd = [
        "ffmpeg", "-i", str(path),
        "-vf", f"freezedetect=noise={noise}dB:duration={duration}",
        "-an", "-f", "null", "-",
    ]
    try:
        result = run_safe(cmd)
    except RunnerError:
        return []

    if result.returncode != 0:
        raise VerificationError(
            "FREEZEDETECT_FAILED",
            f"freezedetect 실패: {redact_paths(result.stderr[:200])}",
        )

    # ffmpeg emits tokens like "freeze_start: 1.23" (value is the NEXT whitespace-separated token)
    intervals = []
    freeze_start: float | None = None
    for line in result.stderr.splitlines():
        tokens = line.split()
        for i, token in enumerate(tokens):
            if token == "freeze_start:" and i + 1 < len(tokens):
                try:
                    freeze_start = float(tokens[i + 1])
                except ValueError:
                    pass
            elif token == "freeze_end:" and i + 1 < len(tokens) and freeze_start is not None:
                try:
                    freeze_end = float(tokens[i + 1])
                    intervals.append({"start": freeze_start, "end": freeze_end})
                    freeze_start = None
                except ValueError:
                    pass
    return intervals
