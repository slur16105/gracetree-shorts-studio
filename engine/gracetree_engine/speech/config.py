"""Story 2.3: Typed speech processing config (provisional values for Story 2.3).

Story 2.4 confirms final model/compute_type. Until then these defaults are used.
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


DEFAULT_SPEECH_CONFIG = SpeechConfig()
