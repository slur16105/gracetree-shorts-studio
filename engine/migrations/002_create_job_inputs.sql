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
    CHECK (status IN ('registered', 'conflict'))
);

CREATE INDEX idx_job_inputs_job_id ON job_inputs (job_id);
