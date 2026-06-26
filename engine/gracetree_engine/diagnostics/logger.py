"""Story 2.8: Pipeline stage diagnostics — wall time logging and path redaction."""
from __future__ import annotations

import contextlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Generator


# ─────────────────────── path redaction ────────────────────────

# Matches Unix absolute paths preceded by whitespace, quote, =, :, (, comma, or start-of-string.
# Consuming group 1 captures the delimiter so it can be restored in the substitution.
# Basename requires ≥2 chars to avoid matching single-char tokens like /0 or /1.
_UNIX_PATH_RE = re.compile(r"(^|[\s'\"=:(,])/(?:[^\s,\"'\\]+/)*([^\s,\"'\\]{2,})")
_WIN_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\s,\"'\\]+\\)+([^\s,\"'\\]+)")


def redact_paths(text: str) -> str:
    """Replace absolute paths with just the basename to limit sensitive exposure."""
    text = _UNIX_PATH_RE.sub(lambda m: m.group(1) + m.group(2), text)
    text = _WIN_PATH_RE.sub(lambda m: m.group(1), text)
    return text


# ─────────────────────── stage result ────────────────────────

@dataclass
class StageResult:
    name: str
    wall_time: float
    redacted_cmd: str | None = None
    status: str = "ok"  # "ok" | "error"


# ─────────────────────── diagnostics ────────────────────────

@dataclass
class PipelineDiagnostics:
    attempt_dir: Path
    stages: list[StageResult] = field(default_factory=list)

    def _record_stage(
        self,
        name: str,
        wall_time: float,
        cmd: list[str] | None = None,
        status: str = "ok",
    ) -> None:
        redacted_cmd = redact_paths(" ".join(cmd)) if cmd is not None else None
        self.stages.append(StageResult(name=name, wall_time=wall_time, redacted_cmd=redacted_cmd, status=status))

    @contextlib.contextmanager
    def stage(self, name: str, cmd: list[str] | None = None) -> Generator[None, None, None]:
        """Context manager that records wall time for a named stage, even on exception."""
        t0 = time.perf_counter()
        _failed = False
        try:
            yield
        except Exception:
            _failed = True
            raise
        finally:
            wall_time = time.perf_counter() - t0
            self._record_stage(name, wall_time, cmd, status="error" if _failed else "ok")

    @property
    def total_wall_time(self) -> float:
        return sum(s.wall_time for s in self.stages)

    def write_log(self) -> Path:
        """Write diagnostics JSON atomically to attempt_dir/pipeline-diagnostics.json."""
        out = self.attempt_dir / "pipeline-diagnostics.json"
        tmp = self.attempt_dir / "pipeline-diagnostics.json.tmp"
        data = {
            "total_wall_time": self.total_wall_time,
            "stages": [asdict(s) for s in self.stages],
        }
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(out)
        return out
