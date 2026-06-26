-- Migration 006: job_attempts에 interrupted 상태와 error_stage_id, log_path 컬럼 추가.
-- SQLite는 CHECK 제약 변경이 불가하므로 테이블을 재생성한다.
--
-- DROP TABLE job_attempts 시 jobs.running_attempt_id → job_attempts FK 위반이 발생한다.
-- defer_foreign_keys는 COMMIT 시점에 제약을 재검사하나, DROP 후 RENAME으로 복원해도
-- SQLite가 내부 OID 기반으로 위반을 추적하여 COMMIT에서 실패한다.
-- 해결책: 마이그레이션 중 running_attempt_id를 임시로 NULL로 설정한 뒤 복원한다.
-- (startup reconciliation이 어차피 running 상태를 정리하므로 링크 손실 무방)
CREATE TEMP TABLE _running_links AS
    SELECT id AS job_id, running_attempt_id
    FROM jobs
    WHERE running_attempt_id IS NOT NULL;

UPDATE jobs SET running_attempt_id = NULL WHERE running_attempt_id IS NOT NULL;

CREATE TABLE job_attempts_new (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    artifact_path TEXT,
    error_code TEXT,
    error_stage_id TEXT,
    log_path TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CHECK (status IN ('running', 'completed', 'failed', 'cancelled', 'interrupted')),
    CHECK (json_valid(snapshot_json))
);

INSERT INTO job_attempts_new
    (id, job_id, snapshot_json, status, started_at, ended_at, artifact_path, error_code, error_stage_id, log_path)
SELECT
    id, job_id, snapshot_json, status, started_at, ended_at, artifact_path, error_code, NULL, NULL
FROM job_attempts;

DROP TABLE job_attempts;

ALTER TABLE job_attempts_new RENAME TO job_attempts;

UPDATE jobs
    SET running_attempt_id = (
        SELECT running_attempt_id FROM _running_links WHERE job_id = jobs.id
    )
    WHERE id IN (SELECT job_id FROM _running_links);

DROP TABLE _running_links;

CREATE INDEX idx_job_attempts_job_id ON job_attempts (job_id);
CREATE INDEX idx_job_attempts_status ON job_attempts (status);
