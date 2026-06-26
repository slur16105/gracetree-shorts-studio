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

# Matches multi-segment Unix paths (/a/b/c) AND root-level paths (/file.ext)
_UNIX_PATH_RE = re.compile(r"/(?:[^\s,\"'\\]+/)*([^\s,\"'\\]+)")
_WIN_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\s,\"'\\]+\\)+([^\s,\"'\\]+)")


def redact_paths(text: str) -> str:
    """Replace absolute paths with just the basename to limit sensitive exposure."""
    text = _UNIX_PATH_RE.sub(lambda m: m.group(1), text)
    text = _WIN_PATH_RE.sub(lambda m: m.group(1), text)
    return text


# ─────────────────────── stage result ────────────────────────

@dataclass
class StageResult:
    name: str
    wall_time: float
    redacted_cmd: str | None = None


# ─────────────────────── diagnostics ────────────────────────

@dataclass
class PipelineDiagnostics:
    attempt_dir: Path
    stages: list[StageResult] = field(default_factory=list)

    def record_stage(
        self,
        name: str,
        wall_time: float,
        cmd: list[str] | None = None,
    ) -> None:
        redacted_cmd = redact_paths(" ".join(cmd)) if cmd is not None else None
        self.stages.append(StageResult(name=name, wall_time=wall_time, redacted_cmd=redacted_cmd))

    @contextlib.contextmanager
    def stage(self, name: str, cmd: list[str] | None = None) -> Generator[None, None, None]:
        """Context manager that records wall time for a named stage, even on exception."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            wall_time = time.perf_counter() - t0
            self.record_stage(name, wall_time, cmd)

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
