"""Story 2.12: Tests for bundle manifest verifier (version/checksum/license)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gracetree_engine.packaging.verifier import (
    ManifestError,
    verify_manifest,
    compute_sha256,
)


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello gracetree")
    return f


@pytest.fixture()
def valid_manifest(tmp_path: Path, sample_file: Path) -> tuple[Path, dict]:
    digest = hashlib.sha256(sample_file.read_bytes()).hexdigest()
    manifest = {
        "engine_version": "0.1.0",
        "platform": "darwin",
        "files": [
            {
                "path": sample_file.name,
                "sha256": digest,
                "license": "MIT",
            }
        ],
    }
    manifest_path = tmp_path / "bundle-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, manifest


def test_compute_sha256(sample_file: Path):
    digest = compute_sha256(sample_file)
    expected = hashlib.sha256(b"hello gracetree").hexdigest()
    assert digest == expected


def test_verify_manifest_passes_valid(valid_manifest, tmp_path):
    manifest_path, _ = valid_manifest
    verify_manifest(manifest_path, base_dir=tmp_path)  # should not raise


def test_verify_manifest_fails_missing_file(tmp_path: Path):
    manifest = {
        "engine_version": "0.1.0",
        "platform": "darwin",
        "files": [
            {
                "path": "nonexistent.txt",
                "sha256": "abc123",
                "license": "MIT",
            }
        ],
    }
    mp = tmp_path / "bundle-manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError, match="missing"):
        verify_manifest(mp, base_dir=tmp_path)


def test_verify_manifest_fails_wrong_checksum(tmp_path: Path, sample_file: Path):
    manifest = {
        "engine_version": "0.1.0",
        "platform": "darwin",
        "files": [
            {
                "path": sample_file.name,
                "sha256": "0" * 64,  # wrong digest
                "license": "MIT",
            }
        ],
    }
    mp = tmp_path / "bundle-manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError, match="checksum"):
        verify_manifest(mp, base_dir=tmp_path)


def test_verify_manifest_fails_missing_version(tmp_path: Path):
    manifest = {"platform": "darwin", "files": []}
    mp = tmp_path / "bundle-manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError, match="engine_version"):
        verify_manifest(mp, base_dir=tmp_path)


def test_verify_manifest_fails_invalid_json(tmp_path: Path):
    mp = tmp_path / "bundle-manifest.json"
    mp.write_bytes(b"not json")
    with pytest.raises(ManifestError, match="JSON"):
        verify_manifest(mp, base_dir=tmp_path)
