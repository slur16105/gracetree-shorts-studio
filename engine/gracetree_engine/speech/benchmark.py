"""Story 2.4: Speech model benchmark harness.

Records timing accuracy (LCS ratio vs ground truth), wall time, and peak memory
for model/compute_type/cpu_threads combinations on a fixed Korean corpus.

Usage (dev-only script — not run in CI):
    cd engine
    python3 -m gracetree_engine.speech.benchmark \\
        --manifest tests/fixtures/media/benchmark-manifest.json \\
        --output benchmark-result.json
"""
from __future__ import annotations

import dataclasses
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .config import SpeechConfig
from .aligner import Segment, _normalize, _lcs_ratio


# ─────────────────────── corpus ────────────────────────


@dataclass
class BenchmarkSample:
    id: str
    file: str
    reference_text: str
    duration_seconds: float
    language: str


# ─────────────────────── memory measurement ────────────────────────


def _peak_memory_mb() -> float:
    """Return peak RSS memory in MB (process-lifetime high-water mark on macOS/Linux).

    Note: ru_maxrss cannot be reset between runs; values for later runs in a
    multi-config session are >= the previous peak, not per-run figures.
    """
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if platform.system() == "Darwin":
            return round(usage.ru_maxrss / (1024 * 1024), 1)
        return round(usage.ru_maxrss / 1024, 1)
    except Exception:
        return 0.0


# ─────────────────────── harness ────────────────────────


def run_benchmark(
    manifest_path: Path,
    configs: list[SpeechConfig],
    transcribe_fn: Callable[[Path, SpeechConfig], list[Segment]] | None = None,
) -> dict[str, Any]:
    """Run all configs over all corpus samples and return a structured report.

    Parameters
    ----------
    manifest_path:
        Path to benchmark-manifest.json.
    configs:
        List of SpeechConfig combinations to evaluate.
    transcribe_fn:
        Optional injectable transcription function (used for testing).
        Defaults to the real _default_transcribe from aligner.

    Returns
    -------
    JSON-serializable dict with platform metadata and per-run results.
    """
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    media_dir = manifest_path.parent
    valid_fields = {f.name for f in dataclasses.fields(BenchmarkSample)}
    samples = [
        BenchmarkSample(**{k: v for k, v in s.items() if k in valid_fields})
        for s in manifest_data["samples"]
    ]

    if transcribe_fn is None:
        from .aligner import _default_transcribe
        transcribe_fn = _default_transcribe

    runs: list[dict[str, Any]] = []
    for config in configs:
        for sample in samples:
            audio_path = media_dir / sample.file
            if not audio_path.exists():
                print(f"[benchmark] WARNING: audio file not found, skipping: {audio_path}")
                continue

            ref_normalized = _normalize(sample.reference_text)
            if not ref_normalized:
                print(f"[benchmark] WARNING: empty reference_text after normalization, skipping: {sample.id}")
                continue

            t0 = time.perf_counter()
            try:
                segments = transcribe_fn(audio_path, config)
            except Exception as exc:
                print(f"[benchmark] ERROR: transcription failed for {sample.id} / {config.model_size}/{config.compute_type}: {exc}")
                continue
            wall_time = round(time.perf_counter() - t0, 3)
            peak_mem = _peak_memory_mb()

            combined = " ".join(s.text for s in segments)
            lcs = round(_lcs_ratio(
                _normalize(combined),
                ref_normalized,
            ), 4)

            runs.append({
                "config": asdict(config),
                "sample_id": sample.id,
                "lcs_ratio": lcs,
                "wall_time_seconds": wall_time,
                "peak_memory_mb": peak_mem,
            })

    return {
        "version": 1,
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        },
        "runs": runs,
    }


# ─────────────────────── CLI entry point ────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Story 2.4 benchmark harness")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    BENCHMARK_CONFIGS = [
        SpeechConfig(model_size="base", compute_type="int8", cpu_threads=4),
        SpeechConfig(model_size="base", compute_type="float32", cpu_threads=4),
        SpeechConfig(model_size="base", compute_type="int8", cpu_threads=2),
        SpeechConfig(model_size="small", compute_type="int8", cpu_threads=4),
    ]

    result = run_benchmark(args.manifest, BENCHMARK_CONFIGS)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Benchmark complete → {args.output}")
    for run in result["runs"]:
        print(f"  [{run['config']['model_size']}/{run['config']['compute_type']}/t{run['config']['cpu_threads']}] "
              f"lcs={run['lcs_ratio']:.3f} wall={run['wall_time_seconds']:.2f}s "
              f"mem={run['peak_memory_mb']:.0f}MB")
