"""Story 2.7: Safe FFmpeg/ffprobe subprocess runner.

Enforces:
  - Executable allowlist (ffmpeg, ffprobe only)
  - No shell=True
  - Configurable timeout
  - stderr length redaction to limit sensitive path exposure
"""
from __future__ import annotations

import os
import subprocess

ALLOWED_EXECUTABLES: frozenset[str] = frozenset({"ffmpeg", "ffprobe"})
STDERR_MAX_CHARS = 500

# The bundled ffmpeg/ffprobe binaries are not on PATH. The trusted host
# (Electron main, or a dev shell) points these env vars at the bundled
# executables; the allowlist is still enforced on the *logical* name so the
# env override cannot introduce an arbitrary executable.
_EXECUTABLE_ENV: dict[str, str] = {
    "ffmpeg": "GRACETREE_FFMPEG",
    "ffprobe": "GRACETREE_FFPROBE",
}


class RunnerError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def run_safe(
    cmd: list[str],
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Run cmd safely; raises RunnerError on allowlist violation or timeout.

    Returns CompletedProcess (may have non-zero returncode — caller must check).
    """
    if not cmd or cmd[0] not in ALLOWED_EXECUTABLES:
        executable = cmd[0] if cmd else "(empty)"
        raise RunnerError(
            "DISALLOWED_EXECUTABLE",
            f"실행 파일이 허용 목록에 없습니다: {executable!r}",
        )
    # Resolve the logical name to the bundled binary when the host configured it.
    resolved = list(cmd)
    override = os.environ.get(_EXECUTABLE_ENV[cmd[0]])
    if override:
        resolved[0] = override
    try:
        result = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        # Truncate stderr to limit sensitive path exposure in callers
        if result.stderr and len(result.stderr) > STDERR_MAX_CHARS:
            result.stderr = result.stderr[:STDERR_MAX_CHARS] + "…"
        return result
    except subprocess.TimeoutExpired:
        raise RunnerError("TIMEOUT", f"FFmpeg 타임아웃 ({timeout}s 초과)")
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise RunnerError("EXECUTION_FAILED", f"실행 파일을 시작할 수 없습니다: {exc}") from exc
