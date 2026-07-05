#!/usr/bin/env python3
"""Smoke test: synthetic audio → MusiCNN ONNX embedding (200-d, L2-normalized)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from music_platform.audio.spectrogram import SAMPLE_RATE  # noqa: E402
from music_platform.config import get_settings  # noqa: E402
from music_platform.inference.musicnn import MusiCNNEmbedder, top_moods  # noqa: E402


def synthesize_audio(duration_sec: float = 5.0, freq_hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def main() -> int:
    settings = get_settings()
    model_path = Path(settings.musicnn_embedding_path)
    if not model_path.is_file():
        print(f"Model not found: {model_path}")
        print("Run: make download-models")
        return 1

    embedder = MusiCNNEmbedder(
        embedding_model_path=settings.musicnn_embedding_path,
        prediction_model_path=settings.musicnn_prediction_path,
    )
    result = embedder.embed_audio(synthesize_audio(), SAMPLE_RATE)

    print(f"patches: {result.num_patches}")
    print(f"embedding dim: {result.embedding.shape[0]}")
    print(f"embedding norm: {np.linalg.norm(result.embedding):.4f}")
    print(f"tempo: {result.tempo:.1f}")
    print(f"top moods: {top_moods(result.moods, n=3)}")
    print(f"first 5 values: {result.embedding[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
