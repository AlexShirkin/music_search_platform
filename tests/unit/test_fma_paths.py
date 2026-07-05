"""Tests for FMA path helpers and track loading."""

from pathlib import Path

import pytest

from music_platform.fma import (
    fma_audio_path,
    fma_audio_relpath,
    iter_fma_audio_files,
    load_fma_tracks,
    parse_duration_sec,
    s3_audio_key,
)


def test_fma_audio_relpath():
    assert fma_audio_relpath(2) == Path("000/000002.mp3")
    assert fma_audio_relpath(1234) == Path("001/001234.mp3")
    assert fma_audio_relpath(135054) == Path("135/135054.mp3")


def test_fma_audio_path():
    root = Path("/data/fma_small")
    assert fma_audio_path(root, 42) == Path("/data/fma_small/000/000042.mp3")


def test_s3_audio_key():
    assert s3_audio_key(42) == "raw/audio/000/000042.mp3"


def test_parse_duration_sec():
    assert parse_duration_sec("02:48") == 168.0
    assert parse_duration_sec("1:05:00") == 3900.0
    assert parse_duration_sec("") is None


def test_iter_fma_audio_files(tmp_path: Path):
    audio_dir = tmp_path / "fma_small" / "135"
    audio_dir.mkdir(parents=True)
    (audio_dir / "135054.mp3").write_bytes(b"fake")
    found = iter_fma_audio_files(tmp_path / "fma_small")
    assert found == [(135054, audio_dir / "135054.mp3")]


def test_load_fma_tracks_joins_metadata_with_files(tmp_path: Path):
    metadata_dir = tmp_path / "fma_metadata"
    audio_dir = tmp_path / "fma_small"
    metadata_dir.mkdir()
    (audio_dir / "000").mkdir(parents=True)
    (audio_dir / "135").mkdir(parents=True)
    (audio_dir / "000" / "000002.mp3").write_bytes(b"fake")
    (audio_dir / "135" / "135054.mp3").write_bytes(b"fake")

    (metadata_dir / "raw_tracks.csv").write_text(
        "track_id,track_title,artist_name,album_title,tags,track_duration\n"
        "2,Food,AWOL,AWOL - A Way Of Life,[],02:48\n"
        "135054,Example,Artist,Album,\"['rock', 'guitar']\",03:10\n"
        "999999,Missing,Artist,Album,[],02:00\n",
        encoding="utf-8",
    )

    tracks = load_fma_tracks(metadata_dir, audio_dir)
    assert len(tracks) == 2
    assert {track.track_id for track in tracks} == {"2", "135054"}
    assert tracks[0].title == "Food"
    assert tracks[1].genre == "rock, guitar"


@pytest.mark.integration
def test_load_fma_tracks_from_real_dataset_if_present():
    root = Path(__file__).resolve().parents[2] / "data" / "fma"
    metadata_dir = root / "fma_metadata"
    audio_dir = root / "fma_small"
    if not metadata_dir.is_dir() or not audio_dir.is_dir():
        pytest.skip("FMA dataset not available locally (expected in CI)")

    tracks = load_fma_tracks(metadata_dir, audio_dir)
    mp3_count = len(list(audio_dir.rglob("*.mp3")))
    assert len(tracks) == mp3_count
    assert len(tracks) >= 1000
    assert all(track.local_audio_path is not None for track in tracks)
