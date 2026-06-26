"""Story 2.9: Final artifact validator.

Validates attempt_dir contents before committing to the output directory.
All checks must pass before any file is moved.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..diagnostics.verifier import VerificationError, probe_file, verify_streams


REQUIRED_WIDTH = 1080
REQUIRED_HEIGHT = 1920
REQUIRED_FPS = 30.0
MIN_DURATION_SECONDS = 1.0


class ValidationError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _parse_fps(fps_str: str) -> float:
    num, _, den = fps_str.partition("/")
    try:
        return float(num) / float(den) if den else float(num)
    except (ValueError, ZeroDivisionError):
        return 0.0


def validate_final_artifacts(attempt_dir: Path) -> None:
    """Validate all required final artifacts in attempt_dir.

    Raises ValidationError if any artifact is missing, empty, malformed,
    or fails video stream/dimension/fps/duration checks.
    Does not modify any file.

    Required artifacts:
      - final.mp4: 1080×1920, 30fps, video+audio streams, duration >= 1s
      - subtitles.ass: exists and non-empty
      - timing.json: exists, non-empty, valid JSON
    """
    # ── final.mp4 ──────────────────────────────────────────────
    final = attempt_dir / "final.mp4"
    if not final.is_file() or final.stat().st_size == 0:
        raise ValidationError(
            "MISSING_ARTIFACT",
            f"final.mp4이 없거나 비어 있습니다: {attempt_dir.name}",
        )

    try:
        info = probe_file(final)
    except VerificationError as exc:
        raise ValidationError(exc.error_code, str(exc)) from exc

    # streams
    try:
        verify_streams(info, require_video=True, require_audio=True)
    except VerificationError as exc:
        raise ValidationError(exc.error_code, str(exc)) from exc

    # dimensions
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is not None:
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        if width != REQUIRED_WIDTH or height != REQUIRED_HEIGHT:
            raise ValidationError(
                "WRONG_DIMENSIONS",
                f"해상도 불일치: {width}×{height} (기대값: {REQUIRED_WIDTH}×{REQUIRED_HEIGHT})",
            )
        fps_str = video_stream.get("r_frame_rate", "0/1")
        fps = _parse_fps(fps_str)
        if abs(fps - REQUIRED_FPS) > 0.5:
            raise ValidationError(
                "WRONG_FPS",
                f"프레임레이트 불일치: {fps:.2f}fps (기대값: {REQUIRED_FPS}fps)",
            )

    # duration
    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except (ValueError, TypeError):
        duration = 0.0
    if duration < MIN_DURATION_SECONDS:
        raise ValidationError(
            "DURATION_TOO_SHORT",
            f"재생 시간이 너무 짧습니다: {duration:.2f}s (최소: {MIN_DURATION_SECONDS:.2f}s)",
        )

    # ── subtitles.ass ──────────────────────────────────────────
    subtitles = attempt_dir / "subtitles.ass"
    if not subtitles.is_file() or subtitles.stat().st_size == 0:
        raise ValidationError(
            "MISSING_ARTIFACT",
            f"subtitles.ass이 없거나 비어 있습니다: {attempt_dir.name}",
        )

    # ── timing.json ────────────────────────────────────────────
    timing = attempt_dir / "timing.json"
    if not timing.is_file() or timing.stat().st_size == 0:
        raise ValidationError(
            "MISSING_ARTIFACT",
            f"timing.json이 없거나 비어 있습니다: {attempt_dir.name}",
        )
    try:
        json.loads(timing.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError(
            "INVALID_ARTIFACT",
            f"timing.json이 유효한 JSON이 아닙니다: {exc}",
        ) from exc
