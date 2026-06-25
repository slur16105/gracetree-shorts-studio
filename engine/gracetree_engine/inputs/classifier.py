from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

INPUT_ROLES = ("thumbnail", "voice", "bgm", "script", "unclassified")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}


def classify_input(file_name: str) -> str:
    """Return a role only when the filename convention is unambiguous."""
    normalized = Path(file_name).name.lower()
    suffix = Path(normalized).suffix
    if suffix in IMAGE_EXTENSIONS:
        return "thumbnail"
    if suffix == ".txt":
        return "script"
    if suffix in AUDIO_EXTENSIONS:
        if normalized.startswith("voice."):
            return "voice"
        if normalized.startswith("bgm."):
            return "bgm"
    return "unclassified"


def resolve_input_states(inputs: Iterable[Mapping[str, str]]) -> dict[str, str]:
    items = list(inputs)
    role_counts = Counter(
        item["role"] for item in items if item["role"] != "unclassified"
    )
    return {
        item["id"]: (
            "unclassified"
            if item["role"] == "unclassified"
            else "conflict"
            if role_counts[item["role"]] > 1
            else "ready"
        )
        for item in items
    }
