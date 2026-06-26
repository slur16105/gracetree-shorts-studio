#!/usr/bin/env python3
"""Story 2.11: Automated quality checker for release gate fixtures.

Runs probe/frame/subtitle/audio checks on each fixture listed in manifest.yaml
and outputs per-fixture results to quality-results.json.

Usage:
    python3 tests/quality/check_quality.py [--manifest tests/quality/manifest.yaml]
    python3 tests/quality/check_quality.py --fixture fixture-001 --output-dir /path/to/output

Exit code:
    0  All fixtures pass gate threshold AND no critical auto-check failures
    1  Below gate threshold OR any critical auto-check failure OR GATE-AUTO violation
    2  Manifest / configuration error
"""
# NOTE: probe_file is intentionally reimplemented here (not imported from
# engine/gracetree_engine/diagnostics/verifier.py) so this script runs as a
# standalone tool without requiring the engine package to be installed.
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# Thresholds — manifest meta values override these defaults at runtime.
REQUIRED_WIDTH = 1080
REQUIRED_HEIGHT = 1920
REQUIRED_FPS = 30.0
FPS_TOLERANCE = 0.5
MIN_DURATION = 55.0   # YouTube Shorts 최소 길이 (story: 55-65s)
LOUDNESS_MIN = -26.0
LOUDNESS_MAX = -20.0
BLACK_DETECT_DURATION = 2.0
BLACK_DETECT_THRESHOLD = 0.98
DEFAULT_GATE_THRESHOLD = 8
DEFAULT_REQUIRED_SAMPLE_COUNT = 10


@dataclass
class CheckResult:
    check_id: str
    passed: bool
    detail: str
    critical: bool = False


@dataclass
class FixtureResult:
    fixture_id: str
    output_dir: str
    checks: list[CheckResult] = field(default_factory=list)
    publishable: bool = False
    fail_categories: list[str] = field(default_factory=list)

    def evaluate(self) -> None:
        critical_failures = [c for c in self.checks if not c.passed and c.critical]
        if critical_failures:
            self.publishable = False
            self.fail_categories = [c.check_id for c in critical_failures]
            return
        auto_failures = [c for c in self.checks if not c.passed]
        self.publishable = len(auto_failures) == 0
        self.fail_categories = [c.check_id for c in auto_failures]

    @property
    def has_critical_failure(self) -> bool:
        return any(not c.passed and c.critical for c in self.checks)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def probe_file(path: Path) -> dict | None:
    """Run ffprobe and return parsed JSON, or None on failure."""
    result = _run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(path),
    ])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def check_dimensions(info: dict) -> CheckResult:
    streams = info.get("streams", [])
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    if vs is None:
        return CheckResult("auto-dimensions", False, "비디오 스트림 없음", critical=True)
    w, h = int(vs.get("width", 0)), int(vs.get("height", 0))
    passed = (w == REQUIRED_WIDTH and h == REQUIRED_HEIGHT)
    detail = f"{w}×{h}" if not passed else f"{w}×{h} ✓"
    return CheckResult("auto-dimensions", passed, detail, critical=True)


def check_fps(info: dict) -> CheckResult:
    streams = info.get("streams", [])
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    if vs is None:
        return CheckResult("auto-fps", False, "비디오 스트림 없음", critical=True)
    fps_str = vs.get("r_frame_rate", "0/1")
    num, _, den = fps_str.partition("/")
    try:
        fps = float(num) / float(den) if (den and float(den) != 0) else float(num)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    passed = abs(fps - REQUIRED_FPS) <= FPS_TOLERANCE
    return CheckResult("auto-fps", passed, f"{fps:.2f}fps", critical=True)


def check_streams(info: dict) -> CheckResult:
    """Require exactly 1 video stream and at least 1 audio stream."""
    streams = info.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    has_one_video = len(video_streams) == 1
    has_audio = len(audio_streams) >= 1
    passed = has_one_video and has_audio
    detail = f"video={len(video_streams)} (expected 1), audio={len(audio_streams)}"
    return CheckResult("auto-streams", passed, detail, critical=True)


def check_duration(info: dict) -> CheckResult:
    streams = info.get("streams", [])
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    dur_str = (vs or {}).get("duration") if vs else None
    if not dur_str:
        dur_str = info.get("format", {}).get("duration", "0")
    try:
        duration = float(dur_str)
    except (ValueError, TypeError):
        duration = 0.0
    passed = duration >= MIN_DURATION
    return CheckResult("auto-duration", passed, f"{duration:.2f}s", critical=True)


def check_subtitles(output_dir: Path) -> CheckResult:
    ass = output_dir / "subtitles.ass"
    if not ass.is_file() or ass.stat().st_size == 0:
        return CheckResult("auto-subtitles-exist", False, "subtitles.ass 없거나 빔", critical=True)
    return CheckResult("auto-subtitles-exist", True, f"{ass.stat().st_size}B", critical=True)


def check_timing(output_dir: Path) -> CheckResult:
    timing = output_dir / "timing.json"
    if not timing.is_file() or timing.stat().st_size == 0:
        return CheckResult("auto-timing-valid", False, "timing.json 없거나 빔", critical=True)
    try:
        json.loads(timing.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return CheckResult("auto-timing-valid", False, str(e), critical=True)
    return CheckResult("auto-timing-valid", True, "valid JSON", critical=True)


def check_black_frames(video_path: Path) -> CheckResult:
    """ffmpeg blackdetect: fail if any black segment >= BLACK_DETECT_DURATION."""
    result = _run([
        "ffmpeg", "-i", str(video_path),
        "-vf", f"blackdetect=d={BLACK_DETECT_DURATION}:pix_th={BLACK_DETECT_THRESHOLD}",
        "-an", "-f", "null", "-",
    ])
    if result.returncode != 0:
        return CheckResult(
            "auto-black-frames", False,
            f"ffmpeg 실패 (exit {result.returncode})",
            critical=False,
        )
    found = "black_start" in result.stderr
    detail = "검은 프레임 구간 발견" if found else "이상 없음"
    return CheckResult("auto-black-frames", not found, detail, critical=False)


def check_audio_loudness(video_path: Path) -> CheckResult:
    """ffmpeg EBU R128 integrated loudness check."""
    result = _run([
        "ffmpeg", "-i", str(video_path),
        "-af", "ebur128=peak=true",
        "-f", "null", "-",
    ])
    if result.returncode != 0:
        return CheckResult(
            "auto-audio-loudness", False,
            f"ffmpeg 실패 (exit {result.returncode})",
            critical=False,
        )
    loudness = None
    for line in result.stderr.splitlines():
        if "I:" in line and "LUFS" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "I:" and i + 1 < len(parts):
                    try:
                        loudness = float(parts[i + 1])
                        break
                    except ValueError:
                        pass
    if loudness is None:
        return CheckResult("auto-audio-loudness", False, "측정 실패", critical=False)
    passed = LOUDNESS_MIN <= loudness <= LOUDNESS_MAX
    return CheckResult("auto-audio-loudness", passed, f"{loudness:.1f} LUFS", critical=False)


def check_fixture(fixture_id: str, output_dir_str: str) -> FixtureResult:
    result = FixtureResult(fixture_id=fixture_id, output_dir=output_dir_str)
    output_dir = Path(output_dir_str)
    video = output_dir / "final.mp4"

    if not video.is_file():
        result.checks.append(
            CheckResult("auto-file-missing", False, f"final.mp4 없음: {output_dir}", critical=True)
        )
        result.evaluate()
        return result

    info = probe_file(video)
    if info is None:
        result.checks.append(
            CheckResult("auto-streams", False, "ffprobe 실패", critical=True)
        )
        result.evaluate()
        return result

    result.checks.extend([
        check_dimensions(info),
        check_fps(info),
        check_streams(info),
        check_duration(info),
        check_subtitles(output_dir),
        check_timing(output_dir),
        check_black_frames(video),
        check_audio_loudness(video),
    ])
    result.evaluate()
    return result


def load_manifest(manifest_path: Path) -> tuple[list[dict], dict]:
    """Returns (fixtures, meta) from manifest.yaml."""
    if not _YAML_AVAILABLE:
        print("PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(2)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return data.get("fixtures", []), data.get("meta", {})


def run_all(manifest_path: Path, output_json: Path) -> int:
    fixtures, meta = load_manifest(manifest_path)
    threshold = int(meta.get("gate_threshold", DEFAULT_GATE_THRESHOLD))
    required_count = int(meta.get("required_sample_count", DEFAULT_REQUIRED_SAMPLE_COUNT))

    results: list[FixtureResult] = []
    skipped = 0
    for f in fixtures:
        fid = f.get("id", "unknown")
        out_dir = f.get("output_dir", "")
        if out_dir == "TBD" or not out_dir:
            print(f"  [SKIP] {fid}: output_dir not configured")
            skipped += 1
            continue
        print(f"  [CHECK] {fid} …", end=" ", flush=True)
        r = check_fixture(fid, out_dir)
        results.append(r)
        status = "PASS" if r.publishable else f"FAIL ({', '.join(r.fail_categories)})"
        print(status)

    pass_count = sum(1 for r in results if r.publishable)
    evaluated = len(results)
    total_in_manifest = evaluated + skipped

    # GATE-AUTO: any critical failure blocks release regardless of pass_count
    any_critical = any(r.has_critical_failure for r in results)

    # GATE-QUALITY: need pass_count >= threshold out of required_count total
    # Unevaluated (skipped) fixtures count as failures against the denominator.
    gate_pass = (
        not any_critical
        and pass_count >= threshold
        and total_in_manifest >= required_count
    )

    gate_auto_fail = any_critical
    gate_quality_fail = not gate_pass and not gate_auto_fail

    summary = {
        "total_in_manifest": total_in_manifest,
        "total_evaluated": evaluated,
        "skipped": skipped,
        "pass_count": pass_count,
        "fail_count": evaluated - pass_count,
        "gate_threshold": threshold,
        "required_sample_count": required_count,
        "gate_auto_fail": gate_auto_fail,
        "gate_quality_fail": gate_quality_fail,
        "gate_result": "PASS" if gate_pass else "FAIL",
        "fixtures": [asdict(r) for r in results],
    }
    output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    gate_label = "✅ PASS" if gate_pass else "❌ FAIL"
    print(f"\n결과: {pass_count}/{total_in_manifest} 통과 ({skipped}개 미평가) — gate {gate_label}")
    if gate_auto_fail:
        print("⛔ GATE-AUTO: critical 자동 검사 실패 → 릴리스 전면 차단")
    elif gate_quality_fail:
        print(f"⛔ GATE-QUALITY: {pass_count}/{required_count} < {threshold} → 프로덕션 릴리스 차단")
    print(f"상세 결과: {output_json}")
    return 0 if gate_pass else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="GraceTree quality gate checker")
    parser.add_argument(
        "--manifest",
        default="tests/quality/manifest.yaml",
        help="Fixture manifest path",
    )
    parser.add_argument(
        "--output",
        default="tests/quality/quality-results.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--fixture",
        help="Run single fixture by ID",
    )
    parser.add_argument(
        "--output-dir",
        help="output/ directory for single fixture run (required with --fixture)",
    )
    args = parser.parse_args()

    if args.fixture and not args.output_dir:
        print("오류: --fixture 사용 시 --output-dir 도 지정해야 합니다.", file=sys.stderr)
        sys.exit(2)

    if args.fixture and args.output_dir:
        r = check_fixture(args.fixture, args.output_dir)
        result_data = asdict(r)
        output_json = Path(args.output)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(result_data, indent=2, ensure_ascii=False))
        sys.exit(0 if r.publishable else 1)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(2)

    sys.exit(run_all(manifest_path, Path(args.output)))


if __name__ == "__main__":
    main()
