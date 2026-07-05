import numpy as np

from music_platform.audio.spectrogram import (
    MEL_BANDS,
    PATCH_FRAMES,
    SAMPLE_RATE,
    prepare_spectrogram_patches,
)


def _sine_wave(duration_sec: float, freq_hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def test_prepare_spectrogram_patches_shape_and_dtype():
    audio = _sine_wave(duration_sec=5.0)
    patches = prepare_spectrogram_patches(audio, SAMPLE_RATE)

    assert patches is not None
    assert patches.dtype == np.float32
    assert patches.ndim == 3
    assert patches.shape[1] == PATCH_FRAMES
    assert patches.shape[2] == MEL_BANDS
    assert patches.shape[0] >= 1


def test_prepare_spectrogram_patches_too_short_returns_none():
    audio = _sine_wave(duration_sec=1.0)
    assert prepare_spectrogram_patches(audio, SAMPLE_RATE) is None


def test_prepare_spectrogram_patches_empty_returns_none():
    assert prepare_spectrogram_patches(np.array([], dtype=np.float32), SAMPLE_RATE) is None
