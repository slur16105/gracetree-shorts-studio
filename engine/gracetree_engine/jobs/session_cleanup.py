from __future__ import annotations

import shutil
from pathlib import Path

from ..storage.migrations import connect_database


def sweep_session_workspaces(approved_root: Path) -> None:
    """이전 세션의 모든 작업 데이터를 정리한다.

    앱을 새로 켤 때 호출한다. ``jobs/`` 하위의 모든 작업 디렉터리와 jobs/job_inputs/
    job_attempts 행을 삭제해 완료 목록을 세션 한정으로 유지한다.

    안전 조건(절대 위반 금지):
    - 정리 범위는 ``approved_root/jobs/`` 하위로만 엄격히 한정한다.
    - 공용 리소스(``resources/``)와 데이터베이스 파일(``studio.db``)은 삭제하지 않는다.
      studio.db는 파일을 유지하고 행만 비운다.
    - 완성 영상은 생성 시 다운로드 폴더로 복사되므로 사용자 사본은 영향받지 않는다.
    """
    root = approved_root.resolve()
    jobs_dir = root / "jobs"
    database_path = root / "studio.db"

    # 1) jobs/ 하위 작업 디렉터리 삭제. jobs/ 컨테이너 자체는 유지한다.
    if jobs_dir.is_dir():
        for child in jobs_dir.iterdir():
            # 안전: 심볼릭 링크 등으로 jobs/ 밖을 가리키는 항목은 건드리지 않는다.
            if not child.resolve().is_relative_to(jobs_dir):
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    # 2) job 관련 행 삭제. 자식 테이블을 먼저 지워 FK 설정과 무관하게 안전하게 비운다.
    if database_path.is_file():
        with connect_database(database_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM job_attempts")
            conn.execute("DELETE FROM job_inputs")
            conn.execute("DELETE FROM jobs")
