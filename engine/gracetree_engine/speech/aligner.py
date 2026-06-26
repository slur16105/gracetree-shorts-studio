"""Story 2.3: Local speech alignment and timing generation.

Aligns a voice recording against the script AST produced by Story 2.2 and
writes a schema-valid timing.json to the attempt temp directory.

All audio mutations happen in attempt_dir; the original voice file is never
modified (hash-invariant).  No network calls are made: faster-whisper uses
only a pre-installed local model.
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Callable, NamedTuple

from .config import SpeechConfig, TARGET_VOICE_START_SECONDS


class Segment(NamedTuple):
    start: float
    end: float
    text: str


class AlignmentError(Exception):
    """Raised when prayer boundary is 0 or N (ambiguous)."""

    def __init__(self, error_code: str, message: str, *, recoverable: bool = False) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.recoverable = recoverable


# ─────────────────────── text matching ────────────────────────

def _normalize(text: str) -> str:
    """NFC normalization; strip whitespace and common punctuation."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"[\s\.,!?;:·…—\-『』「」《》\n]", "", text)


def _lcs_ratio(source: str, target: str) -> float:
    """Fraction of `target` that appears as a subsequence in `source`."""
    if not target:
        return 1.0
    i = 0
    for ch in source:
        if i < len(target) and ch == target[i]:
            i += 1
    return i / len(target)


# ─────────────────────── prayer boundary ────────────────────────

def find_prayer_boundary(
    segments: list[Segment],
    first_block: dict[str, Any],
) -> list[int]:
    """Return indices of candidate segments for the prayer start.

    A segment is a candidate when:
    - Its text alone has LCS ratio ≥ 0.7 against the normalized first line, OR
    - Its text provides ≥ 25% prefix coverage of the first line AND the
      concatenation with the next segment reaches ≥ 0.7 (handles the common
      case where Whisper splits a single prayer line mid-sentence).

    The 25% first-segment guard prevents false positives where a distant pair
    happens to cover the target as a subsequence.

    Returns a list: len 0 → not found, len 1 → unique, len N → ambiguous.
    """
    first_line = first_block["lines"][0] if first_block.get("lines") else first_block.get("text", "")
    target = _normalize(first_line)
    if not target:
        return []

    candidates = []
    n = len(segments)
    for idx in range(n):
        seg_norm = _normalize(segments[idx].text)
        if _lcs_ratio(seg_norm, target) >= 0.7:
            candidates.append(idx)
        elif idx + 1 < n and _lcs_ratio(seg_norm, target) >= 0.25:
            # Pair check: only when the first segment meaningfully starts the line.
            combined = _normalize(segments[idx].text + segments[idx + 1].text)
            if _lcs_ratio(combined, target) >= 0.7:
                candidates.append(idx)
    return candidates


# ─────────────────────── transcription ────────────────────────

def _default_transcribe(voice_path: Path, config: SpeechConfig) -> list[Segment]:
    """Run faster-whisper against a local model (no network allowed)."""
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    model_kwargs: dict[str, Any] = dict(
        device=config.device,
        compute_type=config.compute_type,
        cpu_threads=config.cpu_threads,
        num_workers=config.num_workers,
    )
    if config.model_dir is not None:
        model_kwargs["download_root"] = config.model_dir

    model = WhisperModel(config.model_size, local_files_only=True, **model_kwargs)
    raw_segments, _ = model.transcribe(
        str(voice_path),
        language=config.language,
        beam_size=config.beam_size,
        vad_filter=False,
    )
    return [Segment(s.start, s.end, s.text) for s in raw_segments]


# ─────────────────────── block→segment mapping ────────────────────────

def _assign_blocks(
    segments: list[Segment],
    boundary_idx: int,
    subtitle_blocks: list[dict[str, Any]],
    voice_offset: float,
) -> list[dict[str, Any]]:
    """Sequentially map subtitle blocks to segments from boundary_idx.

    Each block is assigned to the segment at `boundary_idx + i`.  If there
    are more blocks than remaining segments the last available segment is
    reused, with a 1ms offset per overflow step to keep startTime strictly
    increasing and guarantee endTime > startTime.
    """
    last_available = len(segments) - 1
    result = []
    for i, block in enumerate(subtitle_blocks):
        seg_i = min(boundary_idx + i, last_available)
        seg = segments[seg_i]
        overflow_delta = max(0, (boundary_idx + i) - last_available) * 0.001
        start = round(seg.start + voice_offset + overflow_delta, 6)
        end = round(max(seg.end + voice_offset + overflow_delta, start + 0.001), 6)
        result.append({
            "index": block["index"],
            "text": block["text"],
            "lines": block["lines"],
            "startTime": start,
            "endTime": end,
        })
    return result


# ─────────────────────── main entry point ────────────────────────

def align_speech(
    voice_path: Path,
    script_ast: dict[str, Any],
    attempt_dir: Path,
    config: SpeechConfig,
    _transcribe: Callable[[Path, SpeechConfig], list[Segment]] | None = None,
    _leading_silence: float | None = None,
) -> Path:
    """Align voice file against script AST; write timing.json to attempt_dir.

    Parameters
    ----------
    voice_path:
        Path to the original voice file (will NOT be modified).
    script_ast:
        ScriptAstDto dict from Story 2.2 parser.
    attempt_dir:
        Directory for all temp outputs (timing.json + voice copy).
    config:
        SpeechConfig with model settings.
    _transcribe:
        Injectable transcription callable for tests.
    _leading_silence:
        Override leading silence (seconds) for tests; None → derived from
        the first segment's start time.

    Returns
    -------
    Path to the written timing.json.

    Raises
    ------
    AlignmentError(PRAYER_BOUNDARY_AMBIGUOUS)
        When 0 or ≥2 prayer boundary candidates are found.
    """
    # Copy voice to attempt dir; original is never touched.
    voice_copy = attempt_dir / f"voice_copy{voice_path.suffix}"
    shutil.copy2(str(voice_path), str(voice_copy))

    # Transcribe (real or injected mock).
    transcribe = _transcribe if _transcribe is not None else _default_transcribe
    segments = transcribe(voice_copy, config)

    # Leading silence: injected (tests) or first segment start time.
    # Use the raw value (which may be negative for unusual Whisper output) to
    # compute voice_offset correctly, then clamp only for JSON storage.
    if _leading_silence is not None:
        raw_leading_silence = _leading_silence
    else:
        raw_leading_silence = segments[0].start if segments else 0.0
    leading_silence = max(0.0, raw_leading_silence)

    voice_offset = max(0.0, TARGET_VOICE_START_SECONDS - raw_leading_silence)

    # Locate prayer start.
    subtitle_blocks = script_ast.get("subtitleBlocks", [])
    if not subtitle_blocks:
        raise AlignmentError(
            "PRAYER_BOUNDARY_AMBIGUOUS",
            "스크립트 AST에 자막 블록이 없습니다.",
            recoverable=True,
        )

    candidates = find_prayer_boundary(segments, subtitle_blocks[0])
    if len(candidates) != 1:
        raise AlignmentError(
            "PRAYER_BOUNDARY_AMBIGUOUS",
            f"기도 시작 후보 수가 {len(candidates)}개입니다 (정확히 1개여야 합니다).",
            recoverable=True,
        )

    boundary_idx = candidates[0]

    # Map blocks to segments.
    timed_blocks = _assign_blocks(segments, boundary_idx, subtitle_blocks, voice_offset)

    timing = {
        "version": 1,
        "voiceOffset": round(voice_offset, 6),
        "leadingSilenceSeconds": round(leading_silence, 6),
        "subtitleBlocks": timed_blocks,
    }

    timing_path = attempt_dir / "timing.json"
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    return timing_path
