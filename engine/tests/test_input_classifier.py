from __future__ import annotations

import pytest

from gracetree_engine.inputs.classifier import classify_input, resolve_input_states


@pytest.mark.parametrize(
    ("name", "expected_role"),
    [
        ("thumbnail.PNG", "thumbnail"),
        ("cover.final.JpEg", "thumbnail"),
        ("script.TXT", "script"),
        ("voice.mp3", "voice"),
        ("VOICE.final.WAV", "voice"),
        ("bgm.m4a", "bgm"),
        ("bgm.mix.final.AAC", "bgm"),
        ("recording.mp3", "unclassified"),
        ("voice.txt", "script"),
        ("voice.mp3.exe", "unclassified"),
        ("background.mp4", "unclassified"),
    ],
)
def test_classification_is_case_insensitive_and_deterministic(
    name: str, expected_role: str
) -> None:
    assert classify_input(name) == expected_role
    assert classify_input(name) == expected_role


def test_duplicate_role_candidates_are_all_conflicts() -> None:
    resolved = resolve_input_states(
        [
            {"id": "a", "role": "voice"},
            {"id": "b", "role": "voice"},
            {"id": "c", "role": "script"},
            {"id": "d", "role": "unclassified"},
        ]
    )

    assert resolved == {
        "a": "conflict",
        "b": "conflict",
        "c": "ready",
        "d": "unclassified",
    }
