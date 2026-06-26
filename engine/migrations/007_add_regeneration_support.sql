-- Story 3.3: 재생성 지원을 위한 필드 추가
-- job_attempts.is_regeneration: 재생성 attempt 여부 (0=신규, 1=재생성)
-- jobs.pending_artifact_path: 파일 이동 중 crash 복구용 마커
ALTER TABLE job_attempts ADD COLUMN is_regeneration INTEGER NOT NULL DEFAULT 0;

ALTER TABLE jobs ADD COLUMN pending_artifact_path TEXT;
