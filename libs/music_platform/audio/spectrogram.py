"""MusiCNN mel-spectrogram preprocessing (compatible with AudioMuse / v5.0.0-model ONNX)."""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16_000
N_FFT = 512
HOP_LENGTH = 256
MEL_BANDS = 96
PATCH_FRAMES = 187
LOG_SCALE = 10_000.0


def prepare_spectrogram_patches(
    audio: np.ndarray,
    sr: int,
    *,
    n_mels: int = MEL_BANDS,
    hop_length: int = HOP_LENGTH,
    n_fft: int = N_FFT,
    frame: int = PATCH_FRAMES,
) -> np.ndarray | None:
    """Convert waveform to non-overlapping MusiCNN patches.

    Returns array of shape ``(num_patches, frame, n_mels)`` or ``None`` if the
    track is too short for at least one patch (~3 s at 16 kHz).
    """
    import librosa

    if audio.size == 0:
        return None

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
        window="hann",
        center=False,
        power=2.0,
        norm="slaney",
        htk=False,
    )
    log_mel = np.log10(1.0 + LOG_SCALE * np.maximum(mel, 0.0))

    patches = [
        log_mel[:, start : start + frame] for start in range(0, log_mel.shape[1] - frame + 1, frame)
    ]
    if not patches:
        return None

    return np.array(patches, dtype=np.float32).transpose(0, 2, 1)
