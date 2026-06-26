"""Shared test helpers for engine tests."""
from __future__ import annotations

import struct
from pathlib import Path


def make_silent_wav(path: Path, duration: float = 1.0) -> Path:
    """Minimal 16kHz mono 16-bit PCM WAV (silence)."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration)
    data_size = num_samples * 2
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
    return path
