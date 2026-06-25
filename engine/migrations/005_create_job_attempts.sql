-- job_attempts 테이블: 생성 시도별 실행 기록과 입력 스냅샷
CREATE TABLE job_attempts (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    artifact_path TEXT,
    error_code TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    CHECK (json_valid(snapshot_json))
);

CREATE INDEX idx_job_attempts_job_id ON job_attempts (job_id);
CREATE INDEX idx_job_attempts_status ON job_attempts (status);

-- jobs 테이블에 단일 활성 attempt 추적 컬럼 추가
ALTER TABLE jobs ADD COLUMN running_attempt_id TEXT REFERENCES job_attempts(id);
