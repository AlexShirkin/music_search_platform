CREATE TABLE IF NOT EXISTS tracks (
    track_id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    artist TEXT,
    album TEXT,
    genre TEXT,
    file_path TEXT,
    duration_sec DOUBLE PRECISION,
    ingest_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracks_ingest_status ON tracks (ingest_status);
CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks (file_path) WHERE file_path IS NOT NULL;
