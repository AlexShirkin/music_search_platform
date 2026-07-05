#!/usr/bin/env python3
"""Ingest FMA metadata into PostgreSQL and optionally upload audio to MinIO."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from music_platform.config import get_settings  # noqa: E402
from music_platform.db import count_tracks, db_connection, upsert_tracks  # noqa: E402
from music_platform.fma import load_fma_tracks, s3_audio_key  # noqa: E402
from music_platform.s3 import ensure_bucket, get_s3_client, object_exists, upload_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest FMA small into PostgreSQL / MinIO")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "data" / "fma",
        help="Root dir with fma_metadata/ and fma_small/ subfolders",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=None,
        help="Override metadata dir (default: <data-dir>/fma_metadata)",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="Override audio dir (default: <data-dir>/fma_small)",
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload MP3 files to MinIO (skip if object already exists)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max tracks to ingest (for testing)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="DB upsert batch size",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    metadata_dir = args.metadata_dir or (args.data_dir / "fma_metadata")
    audio_dir = args.audio_dir or (args.data_dir / "fma_small")

    if not metadata_dir.is_dir():
        print(f"Metadata dir not found: {metadata_dir}")
        print("Run: make download-fma")
        return 1
    if not audio_dir.is_dir():
        print(f"Audio dir not found: {audio_dir}")
        print("Run: make download-fma  (fma_small.zip is ~7 GB)")
        return 1

    tracks = load_fma_tracks(metadata_dir, audio_dir, subset="small", limit=args.limit)
    if not tracks:
        print("No tracks with local audio files found.")
        return 1

    print(f"Found {len(tracks)} tracks with audio on disk")

    s3_client = get_s3_client(settings) if args.upload_s3 else None
    if s3_client is not None:
        ensure_bucket(s3_client, settings.s3_bucket)

    rows: list[dict] = []
    uploaded = 0
    skipped_upload = 0

    for track in tracks:
        file_path = track.local_audio_path.as_posix() if track.local_audio_path else None
        ingest_status = "indexed_local"

        if s3_client is not None and track.local_audio_path is not None:
            key = s3_audio_key(int(track.track_id))
            if object_exists(s3_client, settings.s3_bucket, key):
                skipped_upload += 1
            else:
                upload_file(s3_client, settings.s3_bucket, key, track.local_audio_path)
                uploaded += 1
            file_path = f"s3://{settings.s3_bucket}/{key}"
            ingest_status = "uploaded"

        rows.append(
            {
                "track_id": track.track_id,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "genre": track.genre,
                "file_path": file_path,
                "duration_sec": track.duration_sec,
                "ingest_status": ingest_status,
            }
        )

        if len(rows) >= args.batch_size:
            with db_connection(settings) as conn:
                upsert_tracks(conn, rows)
            rows.clear()

    if rows:
        with db_connection(settings) as conn:
            upsert_tracks(conn, rows)

    with db_connection(settings) as conn:
        total = count_tracks(conn)

    print(f"PostgreSQL tracks total: {total}")
    if args.upload_s3:
        print(f"MinIO uploaded: {uploaded}, skipped (exists): {skipped_upload}")

    if total < 1000:
        print("Warning: gate этапа 1 expects > 1000 tracks with valid file_path")
        return 1

    print("Ingest complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
