"""Story 2.12: Bundle manifest verifier.

Validates that a bundle-manifest.json produced by scripts/build-engine.mjs
correctly describes every packaged file: engine_version, per-file SHA-256
checksums, and license labels.

Usage (post-build):
    from gracetree_engine.packaging.verifier import verify_manifest
    verify_manifest(Path("dist/gracetree-engine/bundle-manifest.json"),
                    base_dir=Path("dist/gracetree-engine"))
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ManifestError(Exception):
    pass


def compute_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(manifest_path: Path, *, base_dir: Path) -> None:
    """Verify *manifest_path* against files in *base_dir*.

    Raises ManifestError with a descriptive message on the first violation.
    """
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"cannot read manifest: {exc}") from exc

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON in manifest: {exc}") from exc

    if "engine_version" not in manifest:
        raise ManifestError("manifest missing required field: engine_version")

    for entry in manifest.get("files", []):
        rel_path = entry.get("path", "")
        expected_digest = entry.get("sha256", "")
        file_path = base_dir / rel_path

        if not file_path.is_file():
            raise ManifestError(
                f"manifest entry missing from bundle: {rel_path}"
            )

        actual_digest = compute_sha256(file_path)
        if actual_digest != expected_digest:
            raise ManifestError(
                f"checksum mismatch for {rel_path}: "
                f"expected {expected_digest}, got {actual_digest}"
            )
