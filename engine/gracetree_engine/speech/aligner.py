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


class Word(NamedTuple):
    start: float
    end: float
    text: str


class Segment(NamedTuple):
    start: float
    end: float
    text: str
    # Per-word timestamps (empty when unavailable, e.g. in tests). When present,
    # block timing is derived from words for accurate per-phrase sync instead of
    # a coarse 1-block-per-segment mapping.
    words: tuple[Word, ...] = ()


class AlignmentError(Exception):
    """Raised when prayer boundary is 0 or N (ambiguous)."""

    def __init__(self, error_code: str, message: str, *, recoverable: bool = False) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.recoverable = recoverable


# ─────────────────────── text matching ────────────────────────

def normalize(text: str) -> str:
    """NFC normalization; strip whitespace and common punctuation."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"[\s\.,!?;:·…—\-『』「」《》\n]", "", text)


def lcs_ratio(source: str, target: str) -> float:
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

    Matching is two-pass: the full block text is tried first because it is the
    most distinctive anchor. A very short first line (e.g. a single word like
    "하나님") is a weak anchor — its few characters can appear as an incidental
    subsequence elsewhere in the audio (e.g. "하나(됨)…주(님)"), yielding spurious
    candidates. Only when the full block matches nothing (e.g. Whisper produced a
    segment covering just the first line) do we relax to the first line alone.
    """
    full_target = normalize(first_block.get("text", ""))
    candidates = _match_target(segments, full_target)
    if candidates:
        return candidates

    first_line = first_block["lines"][0] if first_block.get("lines") else first_block.get("text", "")
    return _match_target(segments, normalize(first_line))


def _match_target(segments: list[Segment], target: str) -> list[int]:
    """Return indices of segments matching `target` (see find_prayer_boundary)."""
    if not target:
        return []

    candidates: list[int] = []
    seen: set[int] = set()
    n = len(segments)
    for idx in range(n):
        seg_norm = normalize(segments[idx].text)
        if lcs_ratio(seg_norm, target) >= 0.7:
            if idx not in seen:
                candidates.append(idx)
                seen.add(idx)
        elif idx + 1 < n and lcs_ratio(seg_norm, target) >= 0.25:
            # Pair check: only when the first segment meaningfully starts the line.
            combined = normalize(segments[idx].text + segments[idx + 1].text)
            if lcs_ratio(combined, target) >= 0.7:
                # Boundary is at idx+1 (end of pair); deduplicate with seen.
                if idx + 1 not in seen:
                    candidates.append(idx + 1)
                    seen.add(idx + 1)
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

    model = WhisperModel(config.model_size, local_files_only=config.local_files_only, **model_kwargs)
    raw_segments, _ = model.transcribe(
        str(voice_path),
        language=config.language,
        beam_size=config.beam_size,
        vad_filter=config.vad_filter,
        word_timestamps=True,
    )
    return [
        Segment(
            s.start, s.end, s.text,
            tuple(Word(w.start, w.end, w.word) for w in (s.words or [])),
        )
        for s in raw_segments
    ]


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


def _assign_blocks_by_words(
    words: list[Word],
    subtitle_blocks: list[dict[str, Any]],
    start_word_idx: int,
) -> list[dict[str, Any]] | None:
    """Assign each block a contiguous run of spoken words and time it from them.

    The prayer is spoken contiguously from start_word_idx to the last word.
    Whisper's transcription rarely matches the script word-for-word (e.g. 아픈
    vs 아픔), so fragile per-word *text* matching mis-aligns. Instead we decide
    how many words each block consumes from its character-length share, but take
    each block's startTime/endTime from the REAL word timestamps of the words it
    consumes. A block therefore stays on screen for exactly as long as its words
    are actually spoken — fixing the case where a coarse proportional split cut a
    subtitle off before the speaker finished saying it.

    To avoid blank flashes during the natural pauses between phrases, each block
    is held until the next block's first word begins (the last block ends at its
    own last spoken word).

    Times are the real spoken times — the voice plays from t=0 in the final
    video, so subtitles match those times directly (no offset).

    Returns None if alignment cannot proceed (caller falls back to segments).
    """
    n = len(words)
    if start_word_idx >= n or not subtitle_blocks:
        return None
    prayer_words = words[start_word_idx:]
    total_words = len(prayer_words)
    if total_words == 0:
        return None

    lengths = [max(1, len(normalize(b["text"]))) for b in subtitle_blocks]
    total_len = sum(lengths)
    num_blocks = len(subtitle_blocks)

    # Partition the word sequence into one contiguous run per block. Boundaries
    # come from cumulative character share, but every block must get ≥1 word and
    # the runs must stay within [cursor, total_words].
    result: list[dict[str, Any]] = []
    cursor = 0
    cum_len = 0
    for bi, (block, length) in enumerate(zip(subtitle_blocks, lengths)):
        cum_len += length
        if bi == num_blocks - 1:
            end_word = total_words
        else:
            target = round(total_words * cum_len / total_len)
            # Leave at least one word for each remaining block.
            max_end = total_words - (num_blocks - 1 - bi)
            end_word = max(cursor + 1, min(target, max_end))
        block_words = prayer_words[cursor:end_word] or [prayer_words[min(cursor, total_words - 1)]]
        start = round(block_words[0].start, 6)
        end = round(max(block_words[-1].end, start + 0.001), 6)
        result.append({
            "index": block["index"],
            "text": block["text"],
            "lines": block["lines"],
            "startTime": start,
            "endTime": end,
        })
        cursor = end_word

    # Hold each subtitle until the next one begins so pauses between phrases do
    # not leave the screen blank (the final block keeps its own spoken end).
    for i in range(len(result) - 1):
        next_start = result[i + 1]["startTime"]
        if next_start > result[i]["endTime"]:
            result[i]["endTime"] = next_start
    return result


def _find_prayer_start_word(words: list[Word], first_block: dict[str, Any], hint_time: float) -> int | None:
    """Find the word index where the first prayer block begins.

    Scans candidate start positions and returns the one whose forward-consumed
    words best cover the first block's text, preferring matches near hint_time
    (the boundary segment's start) to avoid earlier identical phrases.
    """
    target = normalize(first_block.get("text", "") if not first_block.get("lines")
                        else "".join(first_block["lines"]))
    if not target or not words:
        return None
    best: tuple[float, int] | None = None  # (score, idx)
    n = len(words)
    for i in range(n):
        acc = ""
        j = i
        while j < n and len(acc) < len(target) * 2:
            acc += normalize(words[j].text)
            if lcs_ratio(acc, target) >= 0.75 and len(acc) >= len(target):
                break
            j += 1
        score = lcs_ratio(acc, target)
        if score >= 0.75:
            # Prefer candidates near the hint time (closer = better).
            proximity = -abs(words[i].start - hint_time)
            key = (score, proximity)
            if best is None or key > best[0]:  # type: ignore[index]
                best = (key, i)  # type: ignore[assignment]
    return best[1] if best is not None else None


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
    # Validate before expensive copy/transcribe operations.
    subtitle_blocks = script_ast.get("subtitleBlocks", [])
    if not subtitle_blocks:
        raise AlignmentError(
            "PRAYER_BOUNDARY_AMBIGUOUS",
            "스크립트 AST에 자막 블록이 없습니다.",
            recoverable=True,
        )

    # Copy voice to attempt dir; original is never touched.
    voice_copy = attempt_dir / f"voice_copy{voice_path.suffix}"
    shutil.copy2(str(voice_path), str(voice_copy))

    # Transcribe (real or injected mock).
    transcribe = _transcribe if _transcribe is not None else _default_transcribe
    segments = transcribe(voice_copy, config)

    if not segments:
        raise AlignmentError(
            "NO_SPEECH_DETECTED",
            "음성 파일에서 발화가 감지되지 않았습니다.",
            recoverable=True,
        )

    # Leading silence: injected (tests) or first segment start time.
    # Use the raw value (which may be negative for unusual Whisper output) to
    # compute voice_offset correctly, then clamp only for JSON storage.
    if _leading_silence is not None:
        raw_leading_silence = _leading_silence
    else:
        raw_leading_silence = segments[0].start
    leading_silence = max(0.0, raw_leading_silence)

    voice_offset = max(0.0, TARGET_VOICE_START_SECONDS - raw_leading_silence)

    # Locate prayer start.
    candidates = find_prayer_boundary(segments, subtitle_blocks[0])
    if len(candidates) != 1:
        raise AlignmentError(
            "PRAYER_BOUNDARY_AMBIGUOUS",
            f"기도 시작 후보 수가 {len(candidates)}개입니다 (정확히 1개여야 합니다).",
            recoverable=True,
        )

    boundary_idx = candidates[0]

    # Prefer word-level timing when the transcription provides per-word
    # timestamps: it tracks each spoken phrase instead of cramming overflow
    # blocks onto one coarse segment. Fall back to segment mapping otherwise.
    all_words: list[Word] = [w for seg in segments for w in seg.words]
    timed_blocks: list[dict[str, Any]] | None = None
    if all_words:
        start_word = _find_prayer_start_word(
            all_words, subtitle_blocks[0], segments[boundary_idx].start
        )
        if start_word is not None:
            timed_blocks = _assign_blocks_by_words(all_words, subtitle_blocks, start_word)
    if timed_blocks is None:
        # Map blocks to segments (no word timing available).
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
