from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ..storage.migrations import apply_migrations, connect_database
from ..storage.job_repository import JobRepository
from ..utils import utc_now as _utc_now
from ..scripts.parser import parse_script as _parse_script
from ..speech.aligner import AlignmentError, align_speech as _align_speech
from ..speech.config import DEFAULT_SPEECH_CONFIG
from .attempt_repository import AttemptRepository
from ..resource_resolver import contracts_dir as _contracts_dir

_CONTRACTS_DIR = _contracts_dir()


class JobCancelledError(Exception):
    """취소 이벤트로 인해 generation이 중단됨."""


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise JobCancelledError()


def _run_ffmpeg_cancellable(
    args: list[str],
    cancel_event: threading.Event | None,
    timeout: float = 120.0,
) -> subprocess.CompletedProcess:
    """FFmpeg를 인자 배열로 실행한다. cancel_event가 set되거나 timeout 초 경과 시 프로세스를 kill한다."""
    if cancel_event is None:
        return _run_ffmpeg(args)
    ffmpeg = _resolve_ffmpeg()
    proc = subprocess.Popen(
        [ffmpeg, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + timeout
    try:
        while True:
            if time.monotonic() >= deadline:
                proc.kill()
                proc.wait()
                raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)
            if cancel_event.is_set():
                proc.kill()
                proc.wait()
                raise JobCancelledError()
            try:
                stdout, stderr = proc.communicate(timeout=0.1)
                return subprocess.CompletedProcess(
                    args=[ffmpeg, *args],
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )
            except subprocess.TimeoutExpired:
                continue
    except (JobCancelledError, subprocess.TimeoutExpired):
        raise
    except Exception:
        proc.kill()
        proc.wait()
        raise


def _write_attempt_log(
    work_path: Path,
    attempt_id: str,
    job_id: str,
    stage_id: str | None,
    error_code: str,
    cause: str,
) -> Path:
    """logs/<attemptId>-render_log.txt에 진단 정보를 기록하고 경로를 반환한다."""
    logs_dir = work_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{attempt_id}-render_log.txt"
    stage_label = stage_id if stage_id else "N/A"
    log_path.write_text(
        f"[{_utc_now()}] Attempt {attempt_id} FAILED\n"
        f"Job: {job_id}\n"
        f"Stage: {stage_label}\n"
        f"Error: {error_code}\n"
        f"Cause: {cause}\n",
        encoding="utf-8",
    )
    return log_path


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


def _read_script_ast(managed_path: str, approved_root: Path) -> dict[str, Any] | None:
    """스크립트 파일을 읽어 AST를 반환한다. 읽기 실패 시 None."""
    script_path = Path(managed_path).resolve()
    if not script_path.is_relative_to(approved_root.resolve()):
        return None
    try:
        raw = script_path.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        # 파일이 없거나 인코딩 오류 시 AST 없이 계속 진행. scriptAst는 None으로 저장.
        return None
    parsed = _parse_script(text)
    return parsed["ast"] if parsed["status"] == "valid" else None


def _take_job_snapshot(job_id: str, approved_root: Path) -> dict[str, Any]:
    """현재 job의 입력 슬롯, 리소스 상태, 스크립트 AST를 스냅샷으로 만든다."""
    db_path = approved_root / "studio.db"
    with connect_database(db_path) as conn:
        inputs = conn.execute(
            # ORDER BY id ensures deterministic selection when multiple rows exist.
            "SELECT id, role, managed_path, status FROM job_inputs WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
        resources = conn.execute(
            "SELECT resource_type, managed_path, status FROM resources"
        ).fetchall()

    script_ast = None
    for row in inputs:
        if str(row["role"]) == "script" and str(row["status"]) == "ready":
            if row["managed_path"]:
                script_ast = _read_script_ast(str(row["managed_path"]), approved_root)
            break

    return {
        "inputs": [
            {
                "id": str(row["id"]),
                "role": str(row["role"]),
                # Preserve None; str(None) → 'None' which is truthy and invalid as a path.
                "managedPath": str(row["managed_path"]) if row["managed_path"] is not None else None,
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
        "scriptAst": script_ast,
    }


def _find_voice_path(snapshot: dict[str, Any]) -> str | None:
    """스냅샷 inputs에서 role=voice, status=ready인 첫 번째 managed_path를 반환한다."""
    for inp in snapshot.get("inputs", []):
        if inp.get("role") == "voice" and inp.get("status") == "ready":
            return inp.get("managedPath")
    return None


Emit = Callable[[dict[str, Any]], None]


def start_job(
    *,
    command: dict[str, Any],
    approved_root: Path,
    emit: Emit,
    cancel_event: threading.Event | None = None,
    _align: Callable | None = None,
) -> None:
    """start_job 커맨드를 처리해 수직 슬라이스 진단 MP4를 생성하고 이벤트를 순차 방출한다."""
    job_id = command["jobId"]
    work_path = Path(command["payload"]["workPath"]).resolve()
    is_regeneration: bool = bool(command["payload"].get("regenerate", False))

    if not work_path.is_relative_to(approved_root.resolve()):
        raise ValueError(f"workPath '{work_path}' is outside the approved managed root")

    db_path = approved_root / "studio.db"
    apply_migrations(db_path)

    attempt_id = str(uuid4())
    snapshot = _take_job_snapshot(job_id, approved_root)
    repo = AttemptRepository(db_path)

    emit(_make_event("job_accepted", job_id, {"attemptId": attempt_id}))

    try:
        repo.create_attempt(
            attempt_id=attempt_id,
            job_id=job_id,
            snapshot=snapshot,
            is_regeneration=is_regeneration,
        )
    except (ValueError, RuntimeError) as exc:
        try:
            _write_attempt_log(work_path, attempt_id, job_id, None, "PROCESS_FAILED", str(exc))
        except OSError:
            pass
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": "PROCESS_FAILED",
            "stageId": None,
            "recoverable": False,
            "details": None,
        }))
        return

    attempt_dir = work_path / "temp" / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    try:
        _run_start_job_stages(
            job_id=job_id,
            attempt_id=attempt_id,
            attempt_dir=attempt_dir,
            work_path=work_path,
            approved_root=approved_root,
            snapshot=snapshot,
            repo=repo,
            emit=emit,
            cancel_event=cancel_event,
            _align=_align,
        )
    except JobCancelledError:
        repo.cancel_attempt(attempt_id=attempt_id)
        shutil.rmtree(attempt_dir, ignore_errors=True)
        emit(_make_event("job_cancelled", job_id, {"attemptId": attempt_id}))


def _run_start_job_stages(
    *,
    job_id: str,
    attempt_id: str,
    attempt_dir: Path,
    work_path: Path,
    approved_root: Path,
    snapshot: dict[str, Any],
    repo: AttemptRepository,
    emit: Emit,
    cancel_event: threading.Event | None,
    _align: Callable | None,
) -> None:
    """각 단계를 순서대로 실행한다. 취소 시 JobCancelledError를 발생시킨다."""

    def _fail(
        error_code: str,
        stage_id: str | None,
        recoverable: bool,
        details: str | None,
        cause: str,
    ) -> None:
        """실패 공통 처리: 로그 기록 → DB 업데이트 → 이벤트 방출 → 임시 폴더 삭제."""
        try:
            log_path_str: str | None = str(
                _write_attempt_log(work_path, attempt_id, job_id, stage_id, error_code, cause)
            )
        except OSError:
            log_path_str = None
        repo.fail_attempt(
            attempt_id=attempt_id,
            error_code=error_code,
            error_stage_id=stage_id,
            log_path=log_path_str,
        )
        emit(_make_event("job_failed", job_id, {
            "attemptId": attempt_id,
            "errorCode": error_code,
            "stageId": stage_id,
            "recoverable": recoverable,
            "details": details,
        }))
        shutil.rmtree(attempt_dir, ignore_errors=True)

    voice_path_str = _find_voice_path(snapshot)
    script_ast = snapshot.get("scriptAst")

    if voice_path_str and script_ast:
        _check_cancel(cancel_event)
        voice_path = Path(voice_path_str).resolve()
        if not voice_path.is_relative_to(approved_root.resolve()):
            _fail("PROCESS_FAILED", "speech_alignment", False, None, "음성 파일 경로가 허가된 범위 밖입니다.")
            return
        align_fn = _align if _align is not None else _align_speech
        emit(_make_event("stage_started", job_id, {
            "attemptId": attempt_id,
            "stageId": "speech_alignment",
            "stageName": "음성 정렬",
        }))
        emit(_make_event("progress", job_id, {
            "attemptId": attempt_id,
            "stageId": "speech_alignment",
            "percent": 5,
        }))
        try:
            align_fn(
                voice_path=voice_path,
                script_ast=script_ast,
                attempt_dir=attempt_dir,
                config=DEFAULT_SPEECH_CONFIG,
            )
        except AlignmentError as exc:
            recoverable = exc.recoverable
            if recoverable:
                details = (
                    f"{exc} — "
                    "스크립트의 첫 번째 기도 문장과 음성 녹음의 첫 기도 문장이 일치하는지 확인하세요."
                )
            else:
                details = None
            _fail(exc.error_code, "speech_alignment", recoverable, details, str(exc))
            return
        except Exception as exc:
            _fail("PROCESS_FAILED", "speech_alignment", False, None, str(exc))
            return
        _check_cancel(cancel_event)
        emit(_make_event("progress", job_id, {
            "attemptId": attempt_id,
            "stageId": "speech_alignment",
            "percent": 25,
        }))

    _check_cancel(cancel_event)
    emit(_make_event("stage_started", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "stageName": "수직 슬라이스 진단",
    }))
    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 30,
    }))
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
        "percent": 50,
    }))

    try:
        result = _run_ffmpeg_cancellable(ffmpeg_args, cancel_event)
    except JobCancelledError:
        raise
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _fail("PROCESS_FAILED", "vertical_slice", False, None, "FFmpeg 실행 실패 또는 시간 초과.")
        return

    _check_cancel(cancel_event)

    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 70,
    }))

    if result.returncode != 0:
        _fail("PROCESS_FAILED", "vertical_slice", False, None, "FFmpeg 비정상 종료.")
        return

    emit(_make_event("progress", job_id, {
        "attemptId": attempt_id,
        "stageId": "vertical_slice",
        "percent": 90,
    }))

    if not _verify_mp4(artifact_path):
        _fail("PROCESS_FAILED", "vertical_slice", False, None, "생성된 MP4 파일 검증 실패.")
        return

    # AC 4: output 디렉터리로 원자적 이동 (pending 마커 → os.replace → DB 완료)
    output_dir = work_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / artifact_path.name
    try:
        repo.mark_artifact_commit_pending(job_id=job_id, artifact_path=str(artifact_path))
        os.replace(str(artifact_path), str(output_path))
        repo.complete_attempt(attempt_id=attempt_id, artifact_path=str(output_path))
    except Exception as exc:
        _fail("PROCESS_FAILED", "vertical_slice", False, None, f"산출물 저장 실패: {exc}")
        return

    shutil.rmtree(attempt_dir, ignore_errors=True)

    artifact_name = output_path.name
    emit(_make_event("artifact_created", job_id, {
        "attemptId": attempt_id,
        "artifactPath": str(output_path),
        "artifactName": artifact_name,
    }))

    emit(_make_event("job_completed", job_id, {
        "attemptId": attempt_id,
        "artifactPath": str(output_path),
        "artifactName": artifact_name,
    }))
