#!/usr/bin/env python3
"""Smoke test: synthetic audio → MusiCNN ONNX embedding (200-d, L2-normalized)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from music_platform.audio.spectrogram import SAMPLE_RATE, prepare_spectrogram_patches  # noqa: E402
from music_platform.config import get_settings  # noqa: E402


def synthesize_audio(duration_sec: float = 5.0, freq_hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def embed_patches(patches: np.ndarray, model_path: Path) -> np.ndarray:
    import onnxruntime as ort

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name
    per_patch = []
    for patch in patches:
        batch = patch[np.newaxis, ...]
        out = session.run(None, {input_name: batch})[0]
        per_patch.append(out[0])

    vector = np.mean(per_patch, axis=0)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.astype(np.float32)


def main() -> int:
    settings = get_settings()
    model_path = Path(settings.musicnn_embedding_path)
    if not model_path.is_file():
        print(f"Model not found: {model_path}")
        print("Run: make download-models")
        return 1

    patches = prepare_spectrogram_patches(synthesize_audio(), SAMPLE_RATE)
    if patches is None:
        print("Failed to build spectrogram patches")
        return 1

    embedding = embed_patches(patches, model_path)
    print(f"patches: {patches.shape}")
    print(f"embedding dim: {embedding.shape[0]}")
    print(f"embedding norm: {np.linalg.norm(embedding):.4f}")
    print(f"first 5 values: {embedding[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
