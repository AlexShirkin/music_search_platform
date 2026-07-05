"""FMA dataset path helpers and metadata parsing."""

from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FmaTrack:
    track_id: str
    title: str
    artist: str | None
    album: str | None
    genre: str | None
    duration_sec: float | None
    local_audio_path: Path | None
    file_path: str | None = None


def fma_audio_relpath(track_id: int) -> Path:
    """Relative path inside ``fma_small/`` for a track id."""
    return Path(f"{track_id // 1000:03d}") / f"{track_id:06d}.mp3"


def fma_audio_path(fma_small_dir: Path, track_id: int) -> Path:
    return fma_small_dir / fma_audio_relpath(track_id)


def s3_audio_key(track_id: int) -> str:
    rel = fma_audio_relpath(track_id)
    return f"raw/audio/{rel.as_posix()}"


def parse_duration_sec(raw: str | None) -> float | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return None
    return None


def _parse_tags(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw or raw == "[]":
        return None
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw[:200]
    if isinstance(parsed, list) and parsed:
        return ", ".join(str(x) for x in parsed[:3])
    return None


def _load_metadata_index(metadata_dir: Path) -> dict[int, dict[str, str]]:
    tracks_file = metadata_dir / "raw_tracks.csv"
    if not tracks_file.is_file():
        raise FileNotFoundError(f"raw_tracks.csv not found in {metadata_dir}")

    index: dict[int, dict[str, str]] = {}
    with tracks_file.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            track_id_raw = row.get("track_id")
            if not track_id_raw:
                continue
            index[int(track_id_raw)] = row
    return index


def iter_fma_audio_files(fma_small_dir: Path) -> list[tuple[int, Path]]:
    """Return sorted ``(track_id, path)`` for every MP3 under ``fma_small/``."""
    found: list[tuple[int, Path]] = []
    for path in sorted(fma_small_dir.rglob("*.mp3")):
        if not path.stem.isdigit():
            continue
        found.append((int(path.stem), path))
    return found


def load_fma_tracks(
    metadata_dir: Path,
    fma_small_dir: Path,
    *,
    subset: str = "small",
    limit: int | None = None,
) -> list[FmaTrack]:
    """Load tracks by scanning on-disk audio and joining ``raw_tracks.csv``.

    FMA *small* is **not** ``track_id < 8000`` — it is ~8000 tracks scattered
    across the full catalog. The source of truth is the MP3 files in
    ``fma_small/``.
    """
    metadata = _load_metadata_index(metadata_dir)
    tracks: list[FmaTrack] = []

    for track_id, audio_path in iter_fma_audio_files(fma_small_dir):
        row = metadata.get(track_id)
        if row is None:
            continue

        tracks.append(
            FmaTrack(
                track_id=str(track_id),
                title=(row.get("track_title") or f"track_{track_id}").strip(),
                artist=(row.get("artist_name") or "").strip() or None,
                album=(row.get("album_title") or "").strip() or None,
                genre=_parse_tags(row.get("tags")),
                duration_sec=parse_duration_sec(row.get("track_duration")),
                local_audio_path=audio_path,
            )
        )

        if limit is not None and len(tracks) >= limit:
            break

    if subset != "small":
        raise ValueError(f"Unsupported subset: {subset}")

    return tracks
