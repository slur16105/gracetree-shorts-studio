-- Story 3.3 코드 리뷰 수정: jobs.completed_at 컬럼 추가
-- updated_at이 재생성 실패 복원 시 갱신되어 완료 시각이 오염되는 문제 해결
ALTER TABLE jobs ADD COLUMN completed_at TEXT;

-- 기존 completed 상태 행의 completed_at을 updated_at으로 초기화
UPDATE jobs SET completed_at = updated_at WHERE status = 'completed';
