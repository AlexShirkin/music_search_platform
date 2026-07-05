#!/usr/bin/env python3
"""Batch MusiCNN embedding: PostgreSQL tracks → parquet (+ optional MinIO, DB upsert)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from music_platform.audio.load import load_audio  # noqa: E402
from music_platform.config import get_settings  # noqa: E402
from music_platform.db import connect  # noqa: E402
from music_platform.inference.musicnn import MusiCNNEmbedder, top_moods  # noqa: E402
from music_platform.s3 import get_s3_client, upload_file  # noqa: E402

EMBED_UPSERT_SQL = """
INSERT INTO track_embeddings (
    track_id, model, embedding, tempo, energy, musical_key, scale, moods, num_patches
) VALUES (
    %(track_id)s, %(model)s, %(embedding)s, %(tempo)s, %(energy)s,
    %(musical_key)s, %(scale)s, %(moods)s, %(num_patches)s
)
ON CONFLICT (track_id) DO UPDATE SET
    model = EXCLUDED.model,
    embedding = EXCLUDED.embedding,
    tempo = EXCLUDED.tempo,
    energy = EXCLUDED.energy,
    musical_key = EXCLUDED.musical_key,
    scale = EXCLUDED.scale,
    moods = EXCLUDED.moods,
    num_patches = EXCLUDED.num_patches,
    updated_at = NOW()
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch embed tracks with MusiCNN")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--upload-s3", action="store_true")
    parser.add_argument("--write-db", action="store_true", default=True)
    parser.add_argument("--no-write-db", action="store_false", dest="write_db")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Local parquet path (default: data/embeddings/dt=.../embeddings.parquet)",
    )
    return parser.parse_args()


def fetch_tracks(limit: int, offset: int) -> list[tuple[str, str]]:
    settings = get_settings()
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.track_id, t.file_path
                FROM tracks t
                LEFT JOIN track_embeddings e ON e.track_id = t.track_id
                WHERE t.file_path IS NOT NULL AND e.track_id IS NULL
                ORDER BY t.track_id
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def main() -> int:
    args = parse_args()
    settings = get_settings()
    tracks = fetch_tracks(args.limit, args.offset)
    if not tracks:
        print("No pending tracks to embed.")
        return 0

    embedder = MusiCNNEmbedder(
        embedding_model_path=settings.musicnn_embedding_path,
        prediction_model_path=settings.musicnn_prediction_path,
    )

    records: list[dict] = []
    errors = 0

    for track_id, file_path in tracks:
        try:
            audio, sr = load_audio(file_path, settings=settings)
            result = embedder.embed_audio(audio, sr)
            moods = result.moods or {}
            records.append(
                {
                    "track_id": track_id,
                    "model": "musicnn",
                    "embedding": result.embedding.tolist(),
                    "tempo": result.tempo,
                    "energy": result.energy,
                    "musical_key": result.key,
                    "scale": result.scale,
                    "moods": json.dumps(moods),
                    "top_moods": json.dumps(top_moods(moods, n=5)),
                    "num_patches": result.num_patches,
                }
            )
            print(f"embedded track_id={track_id} patches={result.num_patches}")
        except Exception as exc:
            errors += 1
            print(f"ERROR track_id={track_id}: {exc}")

    if not records:
        print("No embeddings produced.")
        return 1

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    output = args.output or (ROOT / "data" / "embeddings" / f"dt={dt}" / "embeddings.parquet")
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records)
    pq.write_table(table, output)
    print(f"Wrote parquet: {output} ({len(records)} rows)")

    if args.write_db:
        with connect(settings) as conn:
            with conn.cursor() as cur:
                for row in records:
                    cur.execute(
                        EMBED_UPSERT_SQL,
                        {
                            "track_id": row["track_id"],
                            "model": row["model"],
                            "embedding": row["embedding"],
                            "tempo": row["tempo"],
                            "energy": row["energy"],
                            "musical_key": row["musical_key"],
                            "scale": row["scale"],
                            "moods": Jsonb(json.loads(row["moods"])),
                            "num_patches": row["num_patches"],
                        },
                    )
            conn.commit()
        print(f"Upserted {len(records)} rows into track_embeddings")

    if args.upload_s3:
        client = get_s3_client(settings)
        key = f"embeddings/dt={dt}/embeddings.parquet"
        upload_file(client, settings.s3_bucket, key, output)
        print(f"Uploaded s3://{settings.s3_bucket}/{key}")

    print(f"Done. success={len(records)} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
