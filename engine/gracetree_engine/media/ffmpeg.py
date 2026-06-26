"""Story 2.6: FFmpeg command builder for background video composition.

Builds argument lists (never shell strings) for compositing:
  - Speed-adjusted intro (setpts)
  - N prayer-loop copies chained with xfade
  - 3s tail + trim to exact desired duration
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from .probe import VideoInfo


class _BackgroundConfigProto(Protocol):
    crossfade_seconds: float
    tail_seconds: float


def loop_count_needed(
    intro_target: float,
    prayer_end: float,
    loop_duration: float,
    crossfade: float,
    tail: float,
) -> int:
    """Return the minimum number of prayer-loop repeats to cover target duration.

    With N copies of the loop clip (each D seconds) chained via xfade (c seconds):
        total = intro_target + N * (D - c)

    We need: total >= prayer_end + tail
        N >= (prayer_end + tail - intro_target) / (D - c)
    """
    prayer_target = prayer_end + tail - intro_target
    effective = loop_duration - crossfade
    if effective <= 0:
        return max(1, math.ceil(prayer_target))
    return max(1, math.ceil(prayer_target / effective))


def build_background_cmd(
    intro_path: Path,
    intro_info: VideoInfo,
    loop_path: Path,
    loop_info: VideoInfo,
    output_path: Path,
    intro_target: float,
    prayer_end: float,
    config: _BackgroundConfigProto,
) -> list[str]:
    """Build an FFmpeg command list for background video composition.

    Layout:
      - [0:v] intro, speed-adjusted to intro_target seconds
      - [1:v]..[N:v] prayer loop copies, chained with xfade

    Returns a list of strings safe to pass to subprocess.run without shell=True.
    """
    crossfade: float = config.crossfade_seconds
    tail: float = config.tail_seconds

    n_loops = loop_count_needed(intro_target, prayer_end, loop_info.duration, crossfade, tail)
    total_duration = prayer_end + tail

    # PTS multiplier: scales presentation timestamps so intro fits intro_target
    if intro_info.duration > 0 and intro_target > 0:
        pts_ratio = intro_target / intro_info.duration
    else:
        pts_ratio = 1.0

    # Inputs: intro + N loop copies
    cmd: list[str] = ["ffmpeg", "-y"]
    cmd += ["-i", str(intro_path)]
    for _ in range(n_loops):
        cmd += ["-i", str(loop_path)]

    # Build filter_complex
    parts: list[str] = []

    # Speed-adjust intro using guarded pts_ratio
    parts.append(f"[0:v]setpts=PTS*{pts_ratio:.6f}[iv]")

    # Chain xfade: intro→l0, l0→l1, ...
    # Offset at step k: intro_target + k*(D - c) - c; clamped >= 0
    D = loop_info.duration
    c = crossfade

    prev_label = "iv"
    for k in range(n_loops):
        input_label = f"{k + 1}:v"
        out_label = f"x{k}"
        offset = max(0.0, intro_target + k * (D - c) - c)
        parts.append(
            f"[{prev_label}][{input_label}]"
            f"xfade=transition=fade:duration={c}:offset={offset:.3f}"
            f"[{out_label}]"
        )
        prev_label = out_label

    # Trim to exact total duration
    parts.append(
        f"[{prev_label}]trim=end={total_duration:.3f},setpts=PTS-STARTPTS[vout]"
    )

    filter_graph = ";".join(parts)
    cmd += ["-filter_complex", filter_graph]
    cmd += ["-map", "[vout]", "-an"]
    cmd.append(str(output_path))
    return cmd
