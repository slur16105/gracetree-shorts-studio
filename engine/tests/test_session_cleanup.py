from __future__ import annotations

from pathlib import Path

from gracetree_engine.jobs.session_cleanup import sweep_session_workspaces
from gracetree_engine.storage.migrations import apply_migrations, connect_database

JOB_ID = "11111111-1111-4111-8111-111111111111"
ATTEMPT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
INPUT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
NOW = "2026-06-20T00:00:00.000Z"


def _make_root(tmp_path: Path) -> Path:
    """jobs/, resources/, studio.db(작업 1건)를 갖춘 managed root를 만든다."""
    root = tmp_path / "GraceTreeData"
    work = root / "jobs" / "2026-06-20"
    (work / "output").mkdir(parents=True)
    (work / "input").mkdir()
    (work / "temp").mkdir()
    (work / "logs").mkdir()
    (work / "output" / "final.mp4").write_bytes(b"video-bytes")
    (work / "input" / "voice.m4a").write_bytes(b"voice")

    resources = root / "resources"
    resources.mkdir()
    (resources / "default_bgm.mp3").write_bytes(b"bgm")
    (resources / "subtitle_font.woff").write_bytes(b"font")

    db = root / "studio.db"
    apply_migrations(db)
    with connect_database(db) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, publish_date, status, title, work_path, result_path, created_at, updated_at)
            VALUES (?, '2026-06-20', 'completed', '오늘의 은혜', ?, ?, ?, ?)
            """,
            (JOB_ID, str(work), str(work / "output"), NOW, NOW),
        )
        conn.execute(
            """
            INSERT INTO job_inputs (id, job_id, role, original_name, managed_path, status, created_at, updated_at)
            VALUES (?, ?, 'voice', 'voice.m4a', ?, 'ready', ?, ?)
            """,
            (INPUT_ID, JOB_ID, str(work / "input" / "voice.m4a"), NOW, NOW),
        )
        conn.execute(
            """
            INSERT INTO job_attempts (id, job_id, snapshot_json, status, started_at)
            VALUES (?, ?, '{}', 'completed', ?)
            """,
            (ATTEMPT_ID, JOB_ID, NOW),
        )
    return root


def test_sweep_deletes_job_workspace_directories(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    sweep_session_workspaces(root)

    # 작업 폴더는 삭제되지만 jobs/ 컨테이너 자체는 유지된다.
    assert not (root / "jobs" / "2026-06-20").exists()
    assert (root / "jobs").is_dir()


def test_sweep_deletes_job_rows(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    sweep_session_workspaces(root)

    with connect_database(root / "studio.db") as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM job_inputs").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM job_attempts").fetchone()["n"] == 0


def test_sweep_preserves_resources_directory(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    sweep_session_workspaces(root)

    # 공용 리소스는 절대 삭제하지 않는다(가장 중요한 안전 조건).
    assert (root / "resources" / "default_bgm.mp3").read_bytes() == b"bgm"
    assert (root / "resources" / "subtitle_font.woff").read_bytes() == b"font"


def test_sweep_preserves_database_file(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    sweep_session_workspaces(root)

    # studio.db 파일 자체는 유지하고 내용(행)만 비운다.
    assert (root / "studio.db").is_file()


def test_sweep_handles_missing_jobs_directory(tmp_path: Path) -> None:
    root = tmp_path / "GraceTreeData"
    root.mkdir()
    db = root / "studio.db"
    apply_migrations(db)

    # jobs/ 가 없어도 예외 없이 통과한다.
    sweep_session_workspaces(root)

    assert (root / "studio.db").is_file()


def test_sweep_handles_missing_database(tmp_path: Path) -> None:
    root = tmp_path / "GraceTreeData"
    (root / "jobs" / "2026-06-20").mkdir(parents=True)

    # DB가 없어도 디렉터리 정리는 수행하고 예외 없이 통과한다.
    sweep_session_workspaces(root)

    assert not (root / "jobs" / "2026-06-20").exists()
    assert (root / "jobs").is_dir()
