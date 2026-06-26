"""Orchestrator unit tests and FFmpeg integration tests.

Unit tests mock subprocess.run and test all orchestrator logic.
Integration tests (marked 'integration') are skipped when FFmpeg is absent.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest.mock as mock
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from gracetree_engine.jobs.orchestrator import (
    _verify_mp4,
    start_job,
)
from gracetree_engine.jobs.attempt_repository import AttemptRepository
from gracetree_engine.storage.migrations import apply_migrations, connect_database

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _setup_db(tmp_path: Path) -> tuple[Path, str]:
    """migrations를 적용하고 테스트용 job을 만들어 (db_path, job_id)를 반환한다."""
    db_path = tmp_path / "studio.db"
    apply_migrations(db_path)
    job_id = str(uuid4())
    today = "2026-06-25"
    work_path = str(tmp_path / "work")
    with connect_database(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, status, publish_date, work_path, result_path, created_at, updated_at)
            VALUES (?, 'draft', ?, ?, ?, '2026-06-25T00:00:00.000Z', '2026-06-25T00:00:00.000Z')
            """,
            (job_id, today, work_path, work_path + "/output"),
        )
    return db_path, job_id


def _make_command(job_id: str, managed_root: Path, work_path: Path) -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "type": "start_job",
        "jobId": job_id,
        "timestamp": "2026-06-25T00:00:00.000Z",
        "payload": {
            "managedRoot": str(managed_root),
            "workPath": str(work_path),
        },
    }


def _fake_ffmpeg_success(artifact_path: Path):
    """subprocess.run의 성공 mock — artifact 파일을 실제로 생성한다."""
    def _run(args, **kwargs):
        # artifact 경로는 마지막 인자
        out = Path(args[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00" * 128)
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")
    return _run


def _fake_ffprobe_valid(artifact_path: Path):
    """ffprobe가 video 스트림과 양수 duration을 반환하는 mock."""
    def _run(args, **kwargs):
        info = {
            "streams": [{"codec_type": "video"}],
            "format": {"duration": "2.0"},
        }
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(info).encode(), stderr=b"")
    return _run


# ──────────────────────────── unit tests ────────────────────────────────────

class TestVerifyMp4:
    def test_returns_false_when_file_missing(self, tmp_path):
        assert _verify_mp4(tmp_path / "missing.mp4") is False

    def test_returns_false_when_file_is_empty(self, tmp_path):
        p = tmp_path / "empty.mp4"
        p.write_bytes(b"")
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout=b"{}", stderr=b"")
            assert _verify_mp4(p) is False

    def test_returns_false_on_ffprobe_nonzero_exit(self, tmp_path):
        p = tmp_path / "bad.mp4"
        p.write_bytes(b"\x00" * 64)
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"error")
            assert _verify_mp4(p) is False

    def test_returns_false_on_invalid_json(self, tmp_path):
        p = tmp_path / "corrupt.mp4"
        p.write_bytes(b"\x00" * 64)
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout=b"not-json", stderr=b"")
            assert _verify_mp4(p) is False

    def test_returns_false_when_no_video_stream(self, tmp_path):
        p = tmp_path / "audio.mp4"
        p.write_bytes(b"\x00" * 64)
        info = {"streams": [{"codec_type": "audio"}], "format": {"duration": "2.0"}}
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout=json.dumps(info).encode(), stderr=b"")
            assert _verify_mp4(p) is False

    def test_returns_false_when_zero_duration(self, tmp_path):
        p = tmp_path / "zero.mp4"
        p.write_bytes(b"\x00" * 64)
        info = {"streams": [{"codec_type": "video"}], "format": {"duration": "0.0"}}
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout=json.dumps(info).encode(), stderr=b"")
            assert _verify_mp4(p) is False

    def test_returns_true_for_valid_mp4_shape(self, tmp_path):
        p = tmp_path / "ok.mp4"
        p.write_bytes(b"\x00" * 64)
        info = {"streams": [{"codec_type": "video"}], "format": {"duration": "2.0"}}
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout=json.dumps(info).encode(), stderr=b"")
            assert _verify_mp4(p) is True


class TestStartJobUnit:
    """FFmpeg와 DB를 mock하여 orchestrator의 이벤트 방출 순서를 검증한다."""

    def _run(self, tmp_path) -> tuple[list[dict], Path]:
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        db_path, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        # attempt_dir is: work_path/temp/attempts/<attempt_id>/vertical-slice.mp4
        # We don't know attempt_id yet, so we patch subprocess.run globally
        def fake_run(args, **kwargs):
            # For ffmpeg: create the artifact
            if args and "ffmpeg" in str(args[0]):
                out = Path(args[-1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"\x00" * 128)
                return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")
            # For ffprobe: return valid video info
            if args and "ffprobe" in str(args[0]):
                info = {"streams": [{"codec_type": "video"}], "format": {"duration": "2.0"}}
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(info).encode(), stderr=b"")
            return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")

        with mock.patch("subprocess.run", side_effect=fake_run):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        return emitted, db_path

    def test_emits_events_in_expected_order(self, tmp_path):
        emitted, _ = self._run(tmp_path)
        types = [e["type"] for e in emitted]
        # job_accepted must come first
        assert types[0] == "job_accepted"
        # stage_started after accepted
        assert types[1] == "stage_started"
        # at least one progress event before terminal
        progress_types = [t for t in types if t == "progress"]
        assert len(progress_types) >= 1
        # terminal event must be last
        assert types[-1] == "job_completed"

    def test_all_events_share_same_job_id_and_attempt_id(self, tmp_path):
        emitted, _ = self._run(tmp_path)
        job_ids = {e["jobId"] for e in emitted}
        assert len(job_ids) == 1
        attempt_ids = {e["payload"].get("attemptId") for e in emitted if "attemptId" in e.get("payload", {})}
        assert len(attempt_ids) == 1

    def test_progress_is_monotonically_increasing(self, tmp_path):
        emitted, _ = self._run(tmp_path)
        percents = [e["payload"]["percent"] for e in emitted if e["type"] == "progress"]
        assert percents == sorted(percents)

    def test_progress_never_reaches_100_before_completed(self, tmp_path):
        emitted, _ = self._run(tmp_path)
        progress_percents = [e["payload"]["percent"] for e in emitted if e["type"] == "progress"]
        assert all(p < 100 for p in progress_percents)

    def test_artifact_path_written_to_db(self, tmp_path):
        emitted, db_path = self._run(tmp_path)
        completed = next(e for e in emitted if e["type"] == "job_completed")
        attempt_id = completed["payload"]["attemptId"]
        with connect_database(db_path) as conn:
            row = conn.execute(
                "SELECT artifact_path, status FROM job_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        assert row is not None
        assert row["status"] == "completed"
        assert row["artifact_path"] is not None
        assert "vertical-slice.mp4" in row["artifact_path"]

    def test_emits_job_failed_when_ffmpeg_not_found(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        with mock.patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        types = [e["type"] for e in emitted]
        assert types[-1] == "job_failed"
        assert emitted[-1]["payload"]["errorCode"] == "PROCESS_FAILED"

    def test_emits_job_failed_when_ffmpeg_returns_nonzero(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        def fail_ffmpeg(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, stdout=b"", stderr=b"error")

        with mock.patch("subprocess.run", side_effect=fail_ffmpeg):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        assert emitted[-1]["type"] == "job_failed"

    def test_ffmpeg_called_with_argument_array_not_shell_string(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []
        captured_calls: list[Any] = []

        def capture_run(args, **kwargs):
            captured_calls.append(args)
            if "ffmpeg" in str(args[0]):
                out = Path(args[-1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"\x00" * 128)
                return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")
            info = {"streams": [{"codec_type": "video"}], "format": {"duration": "2.0"}}
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(info).encode(), stderr=b"")

        with mock.patch("subprocess.run", side_effect=capture_run):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        ffmpeg_calls = [c for c in captured_calls if "ffmpeg" in str(c[0])]
        assert len(ffmpeg_calls) >= 1
        # Must be a list/tuple, not a string
        assert isinstance(ffmpeg_calls[0], list)

    def test_artifact_placed_under_temp_attempts_dir(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        def fake_run(args, **kwargs):
            if "ffmpeg" in str(args[0]):
                out = Path(args[-1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"\x00" * 128)
                return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")
            info = {"streams": [{"codec_type": "video"}], "format": {"duration": "2.0"}}
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(info).encode(), stderr=b"")

        with mock.patch("subprocess.run", side_effect=fake_run):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        completed = next((e for e in emitted if e["type"] == "job_completed"), None)
        assert completed is not None
        artifact = completed["payload"]["artifactPath"]
        assert "temp/attempts" in artifact.replace("\\", "/")
        assert artifact.endswith("vertical-slice.mp4")


# ──────────────────────────── integration tests ─────────────────────────────

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg not installed — integration test skipped")
class TestStartJobIntegration:
    """실제 FFmpeg를 사용해 진단 MP4 전 주기를 검증한다."""

    def test_creates_valid_mp4_and_emits_completed(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        start_job(command=command, approved_root=managed_root, emit=emitted.append)

        types = [e["type"] for e in emitted]
        assert "job_completed" in types
        assert "job_failed" not in types

        completed = next(e for e in emitted if e["type"] == "job_completed")
        artifact = Path(completed["payload"]["artifactPath"])
        assert artifact.is_file()
        assert artifact.stat().st_size > 0
        assert artifact.name == "vertical-slice.mp4"
        assert "temp/attempts" in str(artifact).replace("\\", "/")

    def test_artifact_passes_ffprobe_verification(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        _, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        start_job(command=command, approved_root=managed_root, emit=emitted.append)

        completed = next((e for e in emitted if e["type"] == "job_completed"), None)
        assert completed is not None
        artifact = Path(completed["payload"]["artifactPath"])
        assert _verify_mp4(artifact), "ffprobe should confirm valid video stream and positive duration"


# ──────────────────────────── speech alignment integration ──────────────────

import struct

from gracetree_engine.speech.aligner import AlignmentError, Segment


def _make_wav(path: Path) -> Path:
    sample_rate, num_samples = 16000, 16000
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


def _setup_db_with_voice(tmp_path: Path, managed_root: Path) -> tuple[str, Path]:
    """job + voice input 행을 DB에 삽입하고 (job_id, voice_path)를 반환한다."""
    voice_path = managed_root / "voice.wav"
    _make_wav(voice_path)
    db_path, job_id = _setup_db(managed_root)
    with connect_database(db_path) as conn:
        conn.execute(
            """
            INSERT INTO job_inputs (id, job_id, role, original_name, managed_path, status, created_at, updated_at)
            VALUES (?, ?, 'voice', 'voice.wav', ?, 'ready', '2026-06-25T00:00:00.000Z', '2026-06-25T00:00:00.000Z')
            """,
            (str(uuid4()), job_id, str(voice_path)),
        )
    return job_id, voice_path


_AST_ONE_BLOCK = {
    "title": "오늘의 기도",
    "scripture": "주를 사랑하고 이웃을 사랑하라.",
    "subtitleBlocks": [
        {
            "index": 0,
            "text": "주님 감사합니다.\n오늘도 지켜주세요.",
            "lines": ["주님 감사합니다.", "오늘도 지켜주세요."],
        }
    ],
}


def _fake_run_ffmpeg(args, **kwargs):
    if args and "ffmpeg" in str(args[0]):
        out = Path(args[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00" * 128)
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")
    if args and "ffprobe" in str(args[0]):
        info = {"streams": [{"codec_type": "video"}], "format": {"duration": "2.0"}}
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(info).encode(), stderr=b"")
    return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")


class TestSpeechAlignmentIntegration:
    """음성 정렬 stage가 orchestrator 파이프라인에 올바르게 통합되는지 검증한다."""

    def test_skips_speech_alignment_when_no_voice_input(self, tmp_path):
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        db_path, job_id = _setup_db(managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        with mock.patch("subprocess.run", side_effect=_fake_run_ffmpeg):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        stage_ids = [
            e["payload"].get("stageId")
            for e in emitted
            if e["type"] == "stage_started"
        ]
        assert "speech_alignment" not in stage_ids
        assert "vertical_slice" in stage_ids

    def _run_with_snapshot_override(self, tmp_path, snapshot_override, align_fn):
        """_take_job_snapshot을 모킹해서 scriptAst를 포함한 스냅샷을 반환하는 헬퍼."""
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        job_id, voice_path = _setup_db_with_voice(tmp_path, managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        base_snapshot = {
            "inputs": [{"id": "x", "role": "voice", "managedPath": str(voice_path), "status": "ready"}],
            "resources": {},
            "scriptAst": _AST_ONE_BLOCK,
        }
        base_snapshot.update(snapshot_override)

        with mock.patch("subprocess.run", side_effect=_fake_run_ffmpeg), \
             mock.patch(
                 "gracetree_engine.jobs.orchestrator._take_job_snapshot",
                 return_value=base_snapshot,
             ):
            start_job(
                command=command,
                approved_root=managed_root,
                emit=emitted.append,
                _align=align_fn,
            )
        return emitted

    def test_emits_speech_alignment_stage_when_voice_and_ast_present(self, tmp_path):
        def _mock_align(voice_path, script_ast, attempt_dir, config):
            timing = {
                "version": 1,
                "voiceOffset": 2.0,
                "leadingSilenceSeconds": 0.0,
                "subtitleBlocks": [{"index": 0, "text": "주님", "lines": ["주님"], "startTime": 2.0, "endTime": 3.0}],
            }
            (attempt_dir / "timing.json").write_text(json.dumps(timing), encoding="utf-8")

        emitted = self._run_with_snapshot_override(tmp_path, {}, _mock_align)

        stage_ids = [
            e["payload"].get("stageId")
            for e in emitted
            if e["type"] in ("stage_started", "progress")
        ]
        assert "speech_alignment" in stage_ids
        assert "vertical_slice" in stage_ids
        assert emitted[-1]["type"] == "job_completed"

    def test_emits_job_failed_on_alignment_error(self, tmp_path):
        def _failing_align(voice_path, script_ast, attempt_dir, config):
            raise AlignmentError("PRAYER_BOUNDARY_AMBIGUOUS", "후보 없음")

        emitted = self._run_with_snapshot_override(tmp_path, {}, _failing_align)

        assert emitted[-1]["type"] == "job_failed"
        assert emitted[-1]["payload"]["errorCode"] == "PRAYER_BOUNDARY_AMBIGUOUS"
        assert emitted[-1]["payload"]["stageId"] == "speech_alignment"

    def test_speech_alignment_before_vertical_slice(self, tmp_path):
        def _mock_align(voice_path, script_ast, attempt_dir, config):
            timing = {
                "version": 1,
                "voiceOffset": 2.0,
                "leadingSilenceSeconds": 0.0,
                "subtitleBlocks": [{"index": 0, "text": "주님", "lines": ["주님"], "startTime": 2.0, "endTime": 3.0}],
            }
            (attempt_dir / "timing.json").write_text(json.dumps(timing), encoding="utf-8")

        emitted = self._run_with_snapshot_override(tmp_path, {}, _mock_align)

        stage_starts = [e for e in emitted if e["type"] == "stage_started"]
        stage_ids = [e["payload"]["stageId"] for e in stage_starts]
        speech_idx = stage_ids.index("speech_alignment")
        vertical_idx = stage_ids.index("vertical_slice")
        assert speech_idx < vertical_idx

    def test_progress_is_monotone_across_both_stages(self, tmp_path):
        def _mock_align(voice_path, script_ast, attempt_dir, config):
            timing = {
                "version": 1,
                "voiceOffset": 2.0,
                "leadingSilenceSeconds": 0.0,
                "subtitleBlocks": [{"index": 0, "text": "주님", "lines": ["주님"], "startTime": 2.0, "endTime": 3.0}],
            }
            (attempt_dir / "timing.json").write_text(json.dumps(timing), encoding="utf-8")

        emitted = self._run_with_snapshot_override(tmp_path, {}, _mock_align)

        percents = [e["payload"]["percent"] for e in emitted if e["type"] == "progress"]
        assert percents == sorted(percents), f"Progress must be monotone, got {percents}"

    def test_emits_job_failed_on_unexpected_exception_during_alignment(self, tmp_path):
        def _raise_oserror(voice_path, script_ast, attempt_dir, config):
            raise OSError("voice file missing from disk")

        emitted = self._run_with_snapshot_override(tmp_path, {}, _raise_oserror)

        assert emitted[-1]["type"] == "job_failed"
        assert emitted[-1]["payload"]["errorCode"] == "PROCESS_FAILED"
        assert emitted[-1]["payload"]["stageId"] == "speech_alignment"

    def test_skips_speech_alignment_when_no_script_ast(self, tmp_path):
        """음성이 있어도 scriptAst가 None이면 speech_alignment 스테이지를 건너뛰어야 한다."""
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        job_id, voice_path = _setup_db_with_voice(tmp_path, managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        snapshot_no_ast = {
            "inputs": [{"id": "x", "role": "voice", "managedPath": str(voice_path), "status": "ready"}],
            "resources": {},
            "scriptAst": None,
        }

        with mock.patch("subprocess.run", side_effect=_fake_run_ffmpeg), \
             mock.patch(
                 "gracetree_engine.jobs.orchestrator._take_job_snapshot",
                 return_value=snapshot_no_ast,
             ):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        stage_ids = [e["payload"].get("stageId") for e in emitted if e["type"] == "stage_started"]
        assert "speech_alignment" not in stage_ids
        assert "vertical_slice" in stage_ids

    def test_rejects_voice_path_outside_managed_root(self, tmp_path):
        """voice path가 approved_root 밖이면 job_failed를 방출해야 한다."""
        managed_root = tmp_path / "managed"
        managed_root.mkdir()
        work_path = managed_root / "jobs" / "2026-06-25"
        work_path.mkdir(parents=True)
        job_id, _ = _setup_db_with_voice(tmp_path, managed_root)
        command = _make_command(job_id, managed_root, work_path)
        emitted: list[dict] = []

        snapshot_outside = {
            "inputs": [{"id": "x", "role": "voice", "managedPath": "/etc/passwd", "status": "ready"}],
            "resources": {},
            "scriptAst": _AST_ONE_BLOCK,
        }

        with mock.patch("subprocess.run", side_effect=_fake_run_ffmpeg), \
             mock.patch(
                 "gracetree_engine.jobs.orchestrator._take_job_snapshot",
                 return_value=snapshot_outside,
             ):
            start_job(command=command, approved_root=managed_root, emit=emitted.append)

        assert emitted[-1]["type"] == "job_failed"
        assert emitted[-1]["payload"]["stageId"] == "speech_alignment"
