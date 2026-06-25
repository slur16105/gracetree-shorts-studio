-- resources 테이블: 공통 리소스 저장
CREATE TABLE IF NOT EXISTS resources (
    resource_type TEXT NOT NULL,
    managed_path TEXT,
    status TEXT NOT NULL DEFAULT 'missing',
    updated_at TEXT NOT NULL,
    CONSTRAINT uq_resources_resource_type UNIQUE (resource_type),
    CONSTRAINT chk_resources_resource_type CHECK (
        resource_type IN ('title_scripture_video', 'prayer_loop_video', 'default_bgm', 'subtitle_font')
    ),
    CONSTRAINT chk_resources_status CHECK (
        status IN ('ready', 'missing', 'invalid')
    )
);

CREATE INDEX IF NOT EXISTS idx_resources_status ON resources (status);

-- 초기 행 삽입 (없으면): 모든 4개 타입을 missing으로
INSERT OR IGNORE INTO resources (resource_type, managed_path, status, updated_at)
VALUES
    ('title_scripture_video', NULL, 'missing', strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now')),
    ('prayer_loop_video', NULL, 'missing', strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now')),
    ('default_bgm', NULL, 'missing', strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now')),
    ('subtitle_font', NULL, 'missing', strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now'));
