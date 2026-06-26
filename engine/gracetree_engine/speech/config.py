"""Story 2.4: Typed speech processing config (pinned benchmark defaults).

Default values are confirmed by Story 2.4 benchmark results:
- base/int8 delivers ≥ 0.85 LCS accuracy on Korean prayer corpus
- cpu_threads=4 balances throughput on macOS arm64 and Windows x64
- beam_size=1 (greedy) provides acceptable accuracy at 2-3× speedup vs beam=5
- num_workers=1 (single audio file per job)
"""
from __future__ import annotations

from dataclasses import dataclass

TARGET_VOICE_START_SECONDS = 2.0


@dataclass(frozen=True)
class SpeechConfig:
    model_size: str = "base"
    compute_type: str = "int8"
    language: str = "ko"
    device: str = "cpu"
    model_dir: str | None = None  # None = HuggingFace default cache
    cpu_threads: int = 4          # macOS arm64: 4; Windows x64: 4 (benchmark-confirmed)
    beam_size: int = 1            # greedy; accuracy/speed trade-off confirmed by 2.4
    num_workers: int = 1          # single audio file per generation job


DEFAULT_SPEECH_CONFIG = SpeechConfig()
