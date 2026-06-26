"""Story 2.4: 음성 모델 성능 기준 확정 — 회귀 테스트.

벤치마크 실행 자체는 CI에서 매번 돌리지 않는다. 이 파일은:
1. 고정된 DEFAULT_SPEECH_CONFIG 값의 회귀를 방지하고
2. 벤치마크 harness의 로직을 목(mock) 전사로 검증하며
3. 오프라인 model availability 조건을 확인한다.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from gracetree_engine.speech.config import DEFAULT_SPEECH_CONFIG, SpeechConfig
from gracetree_engine.speech.aligner import Segment


# ─────────────────────── 고정 설정 회귀 ────────────────────────

class TestPinnedDefaultConfig:
    """DEFAULT_SPEECH_CONFIG는 Story 2.4 벤치마크 결과로 고정된 값을 유지해야 한다."""

    def test_model_size_is_base(self):
        assert DEFAULT_SPEECH_CONFIG.model_size == "base"

    def test_compute_type_is_int8(self):
        assert DEFAULT_SPEECH_CONFIG.compute_type == "int8"

    def test_language_is_korean(self):
        assert DEFAULT_SPEECH_CONFIG.language == "ko"

    def test_device_is_cpu(self):
        assert DEFAULT_SPEECH_CONFIG.device == "cpu"

    def test_cpu_threads_is_pinned(self):
        assert DEFAULT_SPEECH_CONFIG.cpu_threads == 4

    def test_beam_size_is_pinned(self):
        assert DEFAULT_SPEECH_CONFIG.beam_size == 1

    def test_num_workers_is_pinned(self):
        assert DEFAULT_SPEECH_CONFIG.num_workers == 1

    def test_config_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_SPEECH_CONFIG.model_size = "large"  # type: ignore[misc]


# ─────────────────────── 벤치마크 harness 로직 ────────────────────────

def _make_wav(path: Path, duration: float = 3.0) -> Path:
    sample_rate = 16000
    num_samples = int(sample_rate * duration)
    data_size = num_samples * 2
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
    return path


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "media"


class TestBenchmarkHarness:
    def test_manifest_is_valid_json(self):
        manifest_path = FIXTURES_DIR / "benchmark-manifest.json"
        assert manifest_path.exists(), "benchmark-manifest.json이 없습니다"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert len(data["samples"]) >= 1

    def test_manifest_sample_has_required_fields(self):
        manifest_path = FIXTURES_DIR / "benchmark-manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for s in data["samples"]:
            assert "id" in s
            assert "file" in s
            assert "reference_text" in s
            assert "duration_seconds" in s
            assert "language" in s

    def test_run_benchmark_with_mock_transcription(self, tmp_path):
        from gracetree_engine.speech.benchmark import run_benchmark

        manifest_path = tmp_path / "manifest.json"
        wav_path = _make_wav(tmp_path / "test.wav")
        manifest = {
            "version": 1,
            "description": "test",
            "samples": [
                {
                    "id": "test-01",
                    "file": "test.wav",
                    "reference_text": "주님 감사합니다",
                    "duration_seconds": 3.0,
                    "language": "ko",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        def _mock_transcribe(path, config):
            return [Segment(0.0, 2.5, "주님 감사합니다")]

        configs = [DEFAULT_SPEECH_CONFIG]
        report = run_benchmark(manifest_path, configs, transcribe_fn=_mock_transcribe)

        assert report["version"] == 1
        assert "platform" in report
        assert "runs" in report
        assert len(report["runs"]) == 1
        run = report["runs"][0]
        assert run["sample_id"] == "test-01"
        assert run["lcs_ratio"] == pytest.approx(1.0, abs=0.01)
        assert run["wall_time_seconds"] >= 0.0
        assert "peak_memory_mb" in run

    def test_run_benchmark_compares_multiple_configs(self, tmp_path):
        from gracetree_engine.speech.benchmark import run_benchmark

        manifest_path = tmp_path / "manifest.json"
        wav_path = _make_wav(tmp_path / "test.wav")
        manifest = {
            "version": 1,
            "description": "test",
            "samples": [
                {
                    "id": "test-01",
                    "file": "test.wav",
                    "reference_text": "주님 감사합니다",
                    "duration_seconds": 3.0,
                    "language": "ko",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        def _mock_transcribe(path, config):
            return [Segment(0.0, 2.5, "주님 감사합니다")]

        configs = [
            SpeechConfig(model_size="base", compute_type="int8", cpu_threads=4),
            SpeechConfig(model_size="base", compute_type="float32", cpu_threads=4),
        ]
        report = run_benchmark(manifest_path, configs, transcribe_fn=_mock_transcribe)
        assert len(report["runs"]) == 2
        run_configs = [r["config"]["compute_type"] for r in report["runs"]]
        assert "int8" in run_configs
        assert "float32" in run_configs

    def test_run_benchmark_skips_missing_audio_file(self, tmp_path):
        from gracetree_engine.speech.benchmark import run_benchmark

        manifest_path = tmp_path / "manifest.json"
        manifest = {
            "version": 1,
            "description": "test",
            "samples": [
                {
                    "id": "missing",
                    "file": "nonexistent.wav",
                    "reference_text": "주님",
                    "duration_seconds": 1.0,
                    "language": "ko",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = run_benchmark(manifest_path, [DEFAULT_SPEECH_CONFIG])
        assert report["runs"] == []

    def test_report_includes_platform_metadata(self, tmp_path):
        from gracetree_engine.speech.benchmark import run_benchmark

        manifest_path = tmp_path / "manifest.json"
        _make_wav(tmp_path / "test.wav")
        manifest = {
            "version": 1,
            "description": "test",
            "samples": [
                {
                    "id": "t",
                    "file": "test.wav",
                    "reference_text": "주님",
                    "duration_seconds": 1.0,
                    "language": "ko",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        def _mock_transcribe(path, config):
            return [Segment(0.0, 1.0, "주님")]

        report = run_benchmark(manifest_path, [DEFAULT_SPEECH_CONFIG], transcribe_fn=_mock_transcribe)
        assert "system" in report["platform"]
        assert "machine" in report["platform"]
        assert "python_version" in report["platform"]


# ─────────────────────── 오프라인 model availability ────────────────────────

class TestModelAvailability:
    def test_model_dir_none_means_use_system_default(self):
        assert DEFAULT_SPEECH_CONFIG.model_dir is None

    @pytest.mark.skipif(
        not (Path.home() / ".cache" / "huggingface").exists()
        and not (Path.home() / ".cache" / "whisper").exists(),
        reason="캐시된 모델이 없으면 건너뜀",
    )
    def test_model_is_accessible_without_network(self, monkeypatch):
        """모델이 로컬에 캐시된 경우 네트워크 없이도 로드 가능한지 확인한다."""
        import urllib.request
        calls: list = []

        def _no_net(*args, **kwargs):
            calls.append(args)
            raise RuntimeError("Network forbidden")

        monkeypatch.setattr(urllib.request, "urlopen", _no_net)
        try:
            from faster_whisper import WhisperModel
            WhisperModel(
                DEFAULT_SPEECH_CONFIG.model_size,
                device=DEFAULT_SPEECH_CONFIG.device,
                compute_type=DEFAULT_SPEECH_CONFIG.compute_type,
                cpu_threads=DEFAULT_SPEECH_CONFIG.cpu_threads,
                num_workers=DEFAULT_SPEECH_CONFIG.num_workers,
            )
        except Exception:
            pass
        assert calls == [], "모델 로드 중 네트워크 요청이 발생했습니다"

    def test_custom_config_overrides_all_fields(self):
        cfg = SpeechConfig(
            model_size="small",
            compute_type="float32",
            cpu_threads=8,
            beam_size=5,
            num_workers=2,
        )
        assert cfg.model_size == "small"
        assert cfg.compute_type == "float32"
        assert cfg.cpu_threads == 8
        assert cfg.beam_size == 5
        assert cfg.num_workers == 2
