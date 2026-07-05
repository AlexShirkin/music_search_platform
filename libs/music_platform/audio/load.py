"""Load audio from local paths or S3-compatible storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

import librosa
import numpy as np

from music_platform.audio.spectrogram import SAMPLE_RATE
from music_platform.config import Settings, get_settings
from music_platform.s3 import get_s3_client


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an s3 URI: {uri}")
    without_scheme = uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid s3 URI: {uri}")
    return bucket, key


def resolve_audio_path(
    file_path: str,
    *,
    settings: Settings | None = None,
) -> Path:
    """Return a local filesystem path for audio (download S3 objects to a temp file)."""
    if file_path.startswith("s3://"):
        cfg = settings or get_settings()
        bucket, key = parse_s3_uri(file_path)
        client = get_s3_client(cfg)
        suffix = Path(key).suffix or ".mp3"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.close()
        client.download_file(bucket, key, tmp.name)
        return Path(tmp.name)
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    return path


def load_audio(
    file_path: str,
    *,
    settings: Settings | None = None,
    sr: int = SAMPLE_RATE,
) -> tuple[np.ndarray, int]:
    local_path = resolve_audio_path(file_path, settings=settings)
    try:
        audio, sample_rate = librosa.load(local_path, sr=sr, mono=True)
    finally:
        if file_path.startswith("s3://"):
            local_path.unlink(missing_ok=True)
    return audio.astype(np.float32), sample_rate
