ALTER TABLE job_inputs RENAME TO job_inputs_story_1_4;

CREATE TABLE job_inputs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    role TEXT NOT NULL,
    original_name TEXT NOT NULL,
    managed_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CONSTRAINT uq_job_inputs_job_id_managed_path UNIQUE (job_id, managed_path),
    CHECK (role IN ('thumbnail', 'voice', 'bgm', 'script', 'unclassified')),
    CHECK (status IN ('ready', 'conflict', 'unclassified', 'invalid'))
);

INSERT INTO job_inputs (
    id, job_id, role, original_name, managed_path, status, created_at, updated_at
)
SELECT
    id,
    job_id,
    role,
    original_name,
    managed_path,
    CASE WHEN status = 'conflict' THEN 'conflict' ELSE 'unclassified' END,
    created_at,
    updated_at
FROM job_inputs_story_1_4;

DROP TABLE job_inputs_story_1_4;

CREATE INDEX idx_job_inputs_job_id ON job_inputs (job_id);
