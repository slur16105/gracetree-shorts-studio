"""Story 2.7: Audio probe and FFmpeg compose command builder.

Builds the final-composition FFmpeg command that:
  - Overlays thumbnail image on the first frame of background video
  - Mixes voice audio + BGM (with fade in/out) into a single audio track
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


def probe_audio_duration(path: Path) -> float:
    """Return duration of an audio file in seconds using ffprobe.

    Raises FileNotFoundError if path does not exist.
    Raises RuntimeError if ffprobe fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 실패: {result.stderr[:200]}")

    data = json.loads(result.stdout)
    # Prefer stream duration; fall back to format duration
    for stream in data.get("streams", []):
        dur_str = stream.get("duration")
        if dur_str:
            return float(dur_str)
    dur_str = data.get("format", {}).get("duration", "0")
    return float(dur_str)


def build_compose_cmd(
    background_path: Path,
    voice_path: Path,
    bgm_path: Path,
    thumbnail_path: Path,
    output_path: Path,
    total_duration: float,
    config: object,  # ComposeConfig — imported lazily to avoid circular
) -> list[str]:
    """Build FFmpeg command list for final composition.

    Inputs:
      0: background.mp4 (video only)
      1: voice audio
      2: BGM audio
      3: thumbnail image (-loop 1)

    Filter graph:
      - Thumbnail overlay on first frame
      - BGM afade in+out (clamped if BGM too short)
      - amix voice+BGM
    """
    fade: float = config.bgm_fade_seconds  # type: ignore[attr-defined]

    # Clamp fade so in+out don't overlap when total_duration < 2*fade
    max_fade = total_duration / 2.0
    actual_fade = min(fade, max_fade)

    # 1/30s = one frame at 30fps; thumbnail shown for the first frame
    frame_dur = 1.0 / 30.0

    # BGM fade out start (in BGM stream time; assume BGM >= total_duration)
    fade_out_start = total_duration - actual_fade

    parts: list[str] = []

    # Thumbnail overlay for first frame
    parts.append(
        f"[0:v][3:v]overlay=x=0:y=0:enable='lte(t,{frame_dur:.6f})'[vout]"
    )

    # BGM fade in + fade out
    parts.append(
        f"[2:a]afade=t=in:st=0:d={actual_fade},"
        f"afade=t=out:st={fade_out_start:.1f}:d={actual_fade}[bgm_faded]"
    )

    # Mix voice + BGM; duration follows voice (first input)
    parts.append("[1:a][bgm_faded]amix=inputs=2:duration=first:dropout_transition=0[aout]")

    filter_graph = ";".join(parts)

    cmd: list[str] = [
        "ffmpeg", "-y",
        "-i", str(background_path),
        "-i", str(voice_path),
        "-i", str(bgm_path),
        "-loop", "1", "-i", str(thumbnail_path),
        "-filter_complex", filter_graph,
        "-map", "[vout]",
        "-map", "[aout]",
        "-t", str(total_duration),
        str(output_path),
    ]
    return cmd
