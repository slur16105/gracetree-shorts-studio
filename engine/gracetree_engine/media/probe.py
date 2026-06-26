"""Story 2.6: ffprobe-based video stream validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from .runner import RunnerError, run_safe


class VideoInfo(NamedTuple):
    duration: float
    width: int
    height: int
    fps: float


class ProbeError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def probe_video(path: Path) -> VideoInfo:
    """Run ffprobe on path and return VideoInfo. Raises ProbeError on failure."""
    if not path.exists():
        raise ProbeError("FILE_NOT_FOUND", f"파일을 찾을 수 없습니다: {path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        result = run_safe(cmd)
    except RunnerError as exc:
        raise ProbeError("PROBE_FAILED", str(exc)) from exc

    if result.returncode != 0:
        raise ProbeError("PROBE_FAILED", f"ffprobe 실패: {result.stderr[:200]}")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise ProbeError("NO_VIDEO_STREAM", f"비디오 스트림이 없습니다: {path.name}")

    vs = video_streams[0]
    duration_str = vs.get("duration") or data.get("format", {}).get("duration", "0")
    duration = float(duration_str)
    if duration <= 0:
        raise ProbeError("INVALID_DURATION", f"유효하지 않은 재생 시간: {duration}")

    width = int(vs["width"])
    height = int(vs["height"])

    fps_str = vs.get("r_frame_rate", "30/1")
    num, _, den = fps_str.partition("/")
    fps = float(num) / float(den) if den else float(num)

    return VideoInfo(duration=duration, width=width, height=height, fps=fps)
