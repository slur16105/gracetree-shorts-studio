"""Story 2.9: Atomic artifact commit service.

Sequence:
  1. Stage artifacts to a temporary pending directory (same filesystem as output)
  2. Atomic os.replace per file: pending/ → output/
  3. DB: complete_attempt (AttemptRepository)
  4. Copy diagnostic log to logs/<attempt_id>-render_log.txt
  5. Cleanup attempt_dir (best-effort)

Compensation:
  - Staging failure: pending dir removed, output unchanged, CommitError raised
  - Rename failure: pending dir removed, CommitError raised
    (output may have partial files from a prior incomplete commit)
  - DB failure after rename: files exist in output but DB is in running state.
    Caller must handle startup reconciliation — the attempt_dir has already been
    cleaned up and files are safe in output.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

# Names of artifacts transferred from attempt_dir to output_dir
ARTIFACT_NAMES: tuple[str, ...] = ("final.mp4", "subtitles.ass", "timing.json")
_LOG_NAME = "pipeline-diagnostics.json"


class CommitError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _cleanup_dir(path: Path) -> None:
    """Remove directory tree silently; ignore errors (best-effort)."""
    try:
        if path.exists():
            shutil.rmtree(path)
    except Exception:
        pass


def commit_artifacts(
    attempt_dir: Path,
    output_dir: Path,
    log_dir: Path,
    attempt_id: str,
    attempt_repo: Any,
) -> None:
    """Commit validated artifacts from attempt_dir to output_dir atomically.

    Steps:
      1. Copy ARTIFACT_NAMES to a staging pending dir (same parent as output_dir)
      2. os.replace each file from pending/ to output_dir/
      3. Cleanup pending dir
      4. DB: attempt_repo.complete_attempt(attempt_id, artifact_path)
      5. Copy diagnostic log to log_dir/<attempt_id>-render_log.txt
      6. Remove attempt_dir (best-effort)

    Raises CommitError("STAGING_FAILED") if file copy fails.
    Raises CommitError("RENAME_FAILED") if os.replace fails.
    DB failures after rename propagate directly (caller reconciles on startup).
    """
    pending_dir = output_dir.parent / f"output.pending.{attempt_id}"

    # ── Step 1: Stage to pending dir ───────────────────────────
    try:
        pending_dir.mkdir(parents=True, exist_ok=False)
        for name in ARTIFACT_NAMES:
            shutil.copy2(attempt_dir / name, pending_dir / name)
    except Exception as exc:
        _cleanup_dir(pending_dir)
        raise CommitError("STAGING_FAILED", f"staging 실패: {exc}") from exc

    # ── Step 2: Atomic replace per file ────────────────────────
    try:
        for name in ARTIFACT_NAMES:
            os.replace(pending_dir / name, output_dir / name)
    except Exception as exc:
        _cleanup_dir(pending_dir)
        raise CommitError("RENAME_FAILED", f"rename 실패: {exc}") from exc

    # pending_dir should now be empty; remove it
    _cleanup_dir(pending_dir)

    # ── Step 3: DB transaction ──────────────────────────────────
    attempt_repo.complete_attempt(
        attempt_id=attempt_id,
        artifact_path=str(output_dir / "final.mp4"),
    )

    # ── Step 4: Copy diagnostic log ────────────────────────────
    log_src = attempt_dir / _LOG_NAME
    if log_src.is_file():
        log_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(log_src, log_dir / f"{attempt_id}-render_log.txt")

    # ── Step 5: Cleanup attempt dir (best-effort) ───────────────
    _cleanup_dir(attempt_dir)
