"""Story 2.9: Atomic artifact commit service.

Sequence:
  1. Stage artifacts to a temporary pending directory (same filesystem as output)
  2. Atomic os.replace per file: pending/ → output/
     On mid-loop failure, files already placed in output/ are rolled back to
     pending/ before pending/ is cleaned up.
  3. DB: complete_attempt (AttemptRepository)
  4. Copy diagnostic log to logs/<attempt_id>-render_log.txt (best-effort)
  5. Cleanup attempt_dir (best-effort)

Compensation:
  - Staging failure: pending dir removed, output unchanged, CommitError raised
  - Rename failure: placed files rolled back to pending/ then pending/ removed,
    CommitError raised. attempt_dir is intentionally left on disk so the caller
    can retry the commit with the same attempt_dir.
  - DB failure after rename: files exist in output but DB is in running state.
    Log copy and attempt_dir cleanup still run via finally (best-effort).
    Caller must handle startup reconciliation.
  - Log copy failure: silently ignored; attempt_dir cleanup still runs.
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
      3. DB: attempt_repo.complete_attempt(attempt_id, artifact_path)
      4. Copy diagnostic log to log_dir/<attempt_id>-render_log.txt
      5. Remove attempt_dir (best-effort)

    Raises CommitError("STAGING_FAILED") if file copy fails.
    Raises CommitError("RENAME_FAILED") if os.replace fails; attempt_dir is left
      on disk to allow the caller to retry.
    DB failures after rename propagate directly; steps 4-5 still run via finally.
    """
    pending_dir = output_dir.parent / f"output.pending.{attempt_id}"

    # ── Step 1: Stage to pending dir ───────────────────────────
    _cleanup_dir(pending_dir)  # remove any leftover from a crashed prior run
    try:
        pending_dir.mkdir(parents=True)
        for name in ARTIFACT_NAMES:
            shutil.copy2(attempt_dir / name, pending_dir / name)
    except Exception as exc:
        _cleanup_dir(pending_dir)
        raise CommitError("STAGING_FAILED", f"staging 실패: {exc}") from exc

    # ── Step 2: Atomic replace per file ────────────────────────
    placed: list[str] = []
    try:
        for name in ARTIFACT_NAMES:
            os.replace(pending_dir / name, output_dir / name)
            placed.append(name)
    except Exception as exc:
        # Roll back files already placed in output_dir
        for placed_name in placed:
            try:
                os.replace(output_dir / placed_name, pending_dir / placed_name)
            except Exception:
                pass
        _cleanup_dir(pending_dir)
        # attempt_dir is left on disk so the caller can retry the commit
        raise CommitError("RENAME_FAILED", f"rename 실패: {exc}") from exc

    _cleanup_dir(pending_dir)  # now empty after all os.replace calls

    # ── Step 3: DB transaction ──────────────────────────────────
    # Steps 4 and 5 run even if DB raises so diagnostics and disk are cleaned up.
    try:
        attempt_repo.complete_attempt(
            attempt_id=attempt_id,
            artifact_path=str(output_dir / "final.mp4"),
        )
    finally:
        # ── Step 4: Copy diagnostic log (best-effort) ──────────────
        log_src = attempt_dir / _LOG_NAME
        if log_src.is_file():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(log_src, log_dir / f"{attempt_id}-render_log.txt")
            except Exception:
                pass  # log copy is best-effort; do not obscure the DB exception

        # ── Step 5: Cleanup attempt dir (best-effort) ──────────────
        _cleanup_dir(attempt_dir)
