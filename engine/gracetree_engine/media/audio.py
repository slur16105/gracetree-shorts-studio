"""Story 2.7: Audio probe and FFmpeg compose command builder.

Builds the final-composition FFmpeg command that:
  - Overlays thumbnail image on the first frame of background video
  - Mixes voice audio + BGM (with fade in/out) into a single audio track
"""
from __future__ import annotations

import json
from pathlib import Path

from .runner import ALLOWED_EXECUTABLES, RunnerError, run_safe


def probe_audio_duration(path: Path, timeout: int = 60) -> float:
    """Return duration of an audio file in seconds using ffprobe (via run_safe).

    Raises FileNotFoundError if path does not exist.
    Raises RuntimeError if ffprobe fails or returns unparseable output.
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
    try:
        result = run_safe(cmd, timeout=timeout)
    except RunnerError as exc:
        raise RuntimeError(str(exc)) from exc

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 실패: {result.stderr[:200]}")

    data = json.loads(result.stdout)

    # Try stream duration first, then format duration
    for stream in data.get("streams", []):
        dur_str = stream.get("duration")
        if dur_str and dur_str != "N/A":
            try:
                dur = float(dur_str)
                if dur > 0:
                    return dur
            except (ValueError, TypeError):
                pass

    dur_str = data.get("format", {}).get("duration", "0")
    try:
        dur = float(dur_str) if dur_str and dur_str != "N/A" else 0.0
    except (ValueError, TypeError):
        dur = 0.0

    if dur <= 0:
        raise RuntimeError(f"유효한 재생 시간을 찾을 수 없습니다: {path}")
    return dur


def _escape_filter_path(path: str) -> str:
    """Escape a path for use as an ffmpeg filtergraph option value.

    Within a filtergraph, an option value is terminated by ``:`` and the graph
    parser also treats ``\\`` and ``'`` specially. Escape these so paths with a
    Windows drive (``C:\\``) or quotes survive intact. Spaces are literal.
    """
    out = path.replace("\\", "\\\\")
    out = out.replace(":", "\\:")
    out = out.replace("'", "\\'")
    return out


def build_compose_cmd(
    background_path: Path,
    voice_path: Path,
    bgm_path: Path,
    thumbnail_path: Path,
    output_path: Path,
    total_duration: float,
    config: object,  # ComposeConfig — imported lazily to avoid circular
    subtitle_path: Path | None = None,
    fontsdir: Path | None = None,
) -> list[str]:
    """Build FFmpeg command list for final composition.

    Inputs:
      0: background.mp4 (video only)
      1: voice audio
      2: BGM audio
      3: thumbnail image (-loop 1)

    Filter graph:
      - Thumbnail overlay on first frame
      - Subtitle (.ass) burn-in via libass when subtitle_path is given,
        with fontsdir so the Korean font is found (else glyphs fall back/break)
      - BGM afade in+out (clamped if BGM too short)
      - amix voice+BGM
    """
    fade: float = config.bgm_fade_seconds  # type: ignore[attr-defined]

    # Clamp fade so in+out don't overlap when total_duration < 2*fade
    max_fade = total_duration / 2.0
    actual_fade = min(fade, max_fade)
    # Use consistent float format for both fade-in and fade-out
    fade_str = f"{actual_fade:.3f}"

    # 1/30s = one frame at 30fps; thumbnail shown for the first frame
    frame_dur = 1.0 / 30.0

    # BGM fade out start (in BGM stream time)
    fade_out_start = total_duration - actual_fade

    parts: list[str] = []

    # Thumbnail overlay for first frame. When subtitles are burned in, the
    # overlay output feeds the ass filter; otherwise it is the final video.
    overlay_out = "[vov]" if subtitle_path is not None else "[vout]"
    parts.append(
        f"[0:v][3:v]overlay=x=0:y=0:enable='lte(t,{frame_dur:.6f})'{overlay_out}"
    )

    # Subtitle burn-in (libass). fontsdir ensures the Korean font is resolved.
    if subtitle_path is not None:
        ass_opts = f"ass=filename={_escape_filter_path(str(subtitle_path))}"
        if fontsdir is not None:
            ass_opts += f":fontsdir={_escape_filter_path(str(fontsdir))}"
        parts.append(f"[vov]{ass_opts}[vout]")

    # BGM fade in + fade out (consistent precision)
    parts.append(
        f"[2:a]afade=t=in:st=0:d={fade_str},"
        f"afade=t=out:st={fade_out_start:.3f}:d={fade_str}[bgm_faded]"
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
