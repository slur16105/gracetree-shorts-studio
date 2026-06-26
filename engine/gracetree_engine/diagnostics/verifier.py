"""Story 2.8: Post-generation ffprobe stream and quality verification."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..media.runner import STDERR_MAX_CHARS, RunnerError, run_safe
from .logger import redact_paths


class VerificationError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def probe_file(path: Path) -> dict[str, Any]:
    """Run ffprobe on path and return parsed JSON.

    Raises VerificationError(FILE_NOT_FOUND) if path is absent.
    Raises VerificationError(PROBE_FAILED) if ffprobe fails or returns invalid JSON.
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
            f"ffprobe 실패: {redact_paths(result.stderr[:STDERR_MAX_CHARS])}",
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(
            "PROBE_FAILED",
            f"ffprobe JSON 파싱 실패: {redact_paths(str(exc))}",
        ) from exc


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


def _run_ffmpeg_detection(cmd: list[str], error_code: str):
    """Run an ffmpeg detection filter; raise VerificationError on RunnerError or non-zero exit."""
    try:
        result = run_safe(cmd)
    except RunnerError as exc:
        raise VerificationError(error_code, redact_paths(str(exc))) from exc
    if result.returncode != 0:
        raise VerificationError(
            error_code,
            f"ffmpeg 실패: {redact_paths(result.stderr[:STDERR_MAX_CHARS])}",
        )
    return result


def run_blackdetect(path: Path, threshold: float = 0.98) -> list[dict[str, float]]:
    """Run ffmpeg blackdetect and return list of black intervals.

    Each interval: {"start": float, "end": float, "duration": float}
    Raises VerificationError on RunnerError or non-zero ffmpeg exit.
    Intervals with missing black_end or black_duration emit a warning and are skipped.
    """
    cmd = [
        "ffmpeg", "-i", str(path),
        "-vf", f"blackdetect=d=0.1:pix_th={threshold}",
        "-an", "-f", "null", "-",
    ]
    result = _run_ffmpeg_detection(cmd, "BLACKDETECT_FAILED")

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
                if "black_end" not in parts or "black_duration" not in parts:
                    print(
                        f"[blackdetect] WARNING: 불완전한 인터벌 무시: {redact_paths(line)!r}",
                        file=sys.stderr,
                    )
                    continue
                intervals.append({
                    "start": parts["black_start"],
                    "end": parts["black_end"],
                    "duration": parts["black_duration"],
                })
    return intervals


def run_freezedetect(path: Path, noise: float = -60.0, duration: float = 2.0) -> list[dict]:
    """Run ffmpeg freezedetect and return list of frozen intervals.

    Each interval: {"start": float, "end": float | None}
    end is None when the freeze extends to EOF (ffmpeg emits no freeze_end).
    Raises VerificationError on RunnerError or non-zero ffmpeg exit.
    """
    cmd = [
        "ffmpeg", "-i", str(path),
        "-vf", f"freezedetect=noise={noise}dB:duration={duration}",
        "-an", "-f", "null", "-",
    ]
    result = _run_ffmpeg_detection(cmd, "FREEZEDETECT_FAILED")

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
                    freeze_start = None  # Reset stale value on parse failure
            elif token == "freeze_end:" and i + 1 < len(tokens) and freeze_start is not None:
                try:
                    freeze_end = float(tokens[i + 1])
                    intervals.append({"start": freeze_start, "end": freeze_end})
                    freeze_start = None
                except ValueError:
                    pass
    if freeze_start is not None:
        # Freeze extends to EOF — ffmpeg did not emit freeze_end.
        intervals.append({"start": freeze_start, "end": None})
    return intervals
