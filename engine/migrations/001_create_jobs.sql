CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    publish_date TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',
    title TEXT,
    work_path TEXT NOT NULL,
    result_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (length(publish_date) = 10),
    CHECK (status IN ('draft', 'running', 'completed', 'failed', 'cancelled', 'interrupted'))
);

CREATE UNIQUE INDEX idx_jobs_publish_date ON jobs (publish_date);
