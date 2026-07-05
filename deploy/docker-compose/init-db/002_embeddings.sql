CREATE TABLE IF NOT EXISTS track_embeddings (
    track_id VARCHAR(32) PRIMARY KEY REFERENCES tracks(track_id) ON DELETE CASCADE,
    model VARCHAR(64) NOT NULL DEFAULT 'musicnn',
    embedding REAL[] NOT NULL,
    tempo DOUBLE PRECISION,
    energy DOUBLE PRECISION,
    musical_key VARCHAR(8),
    scale VARCHAR(16),
    moods JSONB,
    num_patches INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_track_embeddings_model ON track_embeddings (model);
