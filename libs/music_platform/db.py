"""PostgreSQL helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from music_platform.config import Settings, get_settings

TRACK_UPSERT_SQL = """
INSERT INTO tracks (
    track_id, title, artist, album, genre, file_path, duration_sec, ingest_status
) VALUES (
    %(track_id)s, %(title)s, %(artist)s, %(album)s, %(genre)s,
    %(file_path)s, %(duration_sec)s, %(ingest_status)s
)
ON CONFLICT (track_id) DO UPDATE SET
    title = EXCLUDED.title,
    artist = EXCLUDED.artist,
    album = EXCLUDED.album,
    genre = EXCLUDED.genre,
    file_path = EXCLUDED.file_path,
    duration_sec = EXCLUDED.duration_sec,
    ingest_status = EXCLUDED.ingest_status
"""


def connect(settings: Settings | None = None) -> psycopg.Connection:
    cfg = settings or get_settings()
    return psycopg.connect(cfg.database_url)


@contextmanager
def db_connection(settings: Settings | None = None) -> Iterator[psycopg.Connection]:
    conn = connect(settings)
    try:
        yield conn
    finally:
        conn.close()


def upsert_tracks(conn: psycopg.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(TRACK_UPSERT_SQL, row)
    conn.commit()
    return len(rows)


def count_tracks(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tracks")
        result = cur.fetchone()
    return int(result[0]) if result else 0
