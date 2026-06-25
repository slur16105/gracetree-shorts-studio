from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import uuid4

from ..storage.migrations import apply_migrations, connect_database
from ..storage.job_repository import JobRepository
from ..utils import utc_now as _utc_now
from .attempt_repository import AttemptRepository

_CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "packages" / "contracts"


def _make_event(type_: str, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "type": type_,
        "jobId": job_id,
        "timestamp": _utc_now(),
        "payload": payload,
    }


def _resolve_ffmpeg() -> str:
    """FFmpeg 실행 파일 경로를 결정한다. 환경 변수 → 시스템 PATH 순서."""
    if "FFMPEG" in os.environ:
        return os.environ["FFMPEG"]
    return "ffmpeg"


def _resolve_ffprobe() -> str:
    if "FFPROBE" in os.environ:
        return os.environ["FFPROBE"]
    return "ffprobe"


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    """FFmpeg를 인자 배열로 실행한다. 셸 문자열 조합 금지."""
    ffmpeg = _resolve_ffmpeg()
    return subprocess.run(
        [ffmpeg, *args],
        capture_output=True,
        timeout=120,
    )


def _verify_mp4(artifact_path: Path) -> bool:
    """ffprobe로 mp4 영상 스트림과 양수 duration을 검증한다."""
    if not artifact_path.is_file() or artifact_path.stat().st_size == 0:
        return False
    ffprobe = _resolve_ffprobe()
    result = subprocess.run(
        [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(artifact_path),
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        return False
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    streams = info.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0.0
    return has_video and duration > 0


def _take_job_snapshot(job_id: str, approved_root: Path) -> dict[str, Any]:
    """현재 job의 입력 슬롯과 리소스 상태를 스냅샷으로 만든다."""
    db_path = approved_root / "studio.db"
    with connect_database(db_path) as conn:
        inputs = conn.execute(
            "SELECT id, role, managed_path, status FROM job_inputs WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        resources = conn.execute(
            "SELECT resource_type, managed_path, status FROM resources"
        ).fetchall()
    return {
        "inputs": [
            {
                "id": str(row["id"]),
                "role": str(row["role"]),
                "managedPath": str(row["managed_path"]),
                "status": str(row["status"]),
            }
            for row in inputs
        ],
        "resources": {
            str(row["resource_type"]): {
                "managedPath": row["managed_path"],
                "status": str(row["status"]),
            }
            for row in resources
        },
    }


Emit = Callable[[dict[str, Any]], None]


def start_job(
    *,
    command: dict[str, Any],
    approved_root: Path,
    emit: Emit,
) -> None:
    """start_job 커맨드를 처리해 수직 슬라이스 진단 MP4를 생성하고 이벤트를 순차 방출한다."""
    job_id = command["jobId"]
    work_path = Path(command["payload"]["workPath"]).resolve()

    if not work_path.is_relative_to(approved_root.resolve()):
        raise ValueError(f"workPath '{work_path}' is outside the approved managed root")

    db_path = approved_root / "studio.db"
    apply_migrations(db_path)

    attempt_id = str(uuid4())
    snapshot = _take_job_snapshot(job_id, approved_root)
    repo = AttemptRepository(db_path)

    try:
        repo.create_attempt(
            attempt_id=attempt_id,
            job_id=job_id,
            snapshot=snapshot,
        )
    except (ValueError, RuntimeError) as exc:
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": "PROCESS_FAILED",
            "stageId": None,
        }))
        return

    emit(_make_event("job_accepted", job_id, {"attemptId": attempt_id}))
    emit(_make_event("stage_started", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "stageName": "수직 슬라이스 진단",
    }))
    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 10,
    }))

    attempt_dir = work_path / "temp" / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = attempt_dir / "vertical-slice.mp4"

    ffmpeg_args = [
        "-y",
        "-f", "lavfi",
        "-i", "color=black:size=64x64:rate=30:duration=2",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(artifact_path),
    ]

    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 30,
    }))

    try:
        result = _run_ffmpeg(ffmpeg_args)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        repo.fail_attempt(attempt_id=attempt_id, error_code="PROCESS_FAILED")
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": "PROCESS_FAILED",
            "stageId": "vertical_slice",
        }))
        return

    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 70,
    }))

    if result.returncode != 0:
        repo.fail_attempt(attempt_id=attempt_id, error_code="PROCESS_FAILED")
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": "PROCESS_FAILED",
            "stageId": "vertical_slice",
        }))
        return

    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 90,
    }))

    if not _verify_mp4(artifact_path):
        repo.fail_attempt(attempt_id=attempt_id, error_code="PROCESS_FAILED")
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": "PROCESS_FAILED",
            "stageId": "vertical_slice",
        }))
        return

    artifact_name = artifact_path.name
    repo.complete_attempt(attempt_id=attempt_id, artifact_path=str(artifact_path))

    emit(_make_event("artifact_created", job_id, {
        "attemptId": attempt_id,
        "artifactPath": str(artifact_path),
        "artifactName": artifact_name,
    }))

    emit(_make_event("job_completed", job_id, {
        "attemptId": attempt_id,
        "artifactPath": str(artifact_path),
        "artifactName": artifact_name,
    }))
