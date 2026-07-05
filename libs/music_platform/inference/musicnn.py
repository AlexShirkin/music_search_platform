"""MusiCNN ONNX inference: mel patches → embedding + optional mood tags."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from music_platform.audio.spectrogram import SAMPLE_RATE, prepare_spectrogram_patches
from music_platform.constants import MOOD_LABELS


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


def extract_basic_features(audio: np.ndarray, sr: int) -> dict[str, float | str]:
    """Tempo, RMS energy, and rough key estimate (major/minor)."""
    _keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    _major = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
    _minor = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    energy = float(np.mean(librosa.feature.rms(y=audio)))
    chroma_mean = np.mean(librosa.feature.chroma_stft(y=audio, sr=sr), axis=1)
    maj = np.array([np.corrcoef(chroma_mean, np.roll(_major, i))[0, 1] for i in range(12)])
    mnr = np.array([np.corrcoef(chroma_mean, np.roll(_minor, i))[0, 1] for i in range(12)])
    mi, ni = int(np.argmax(maj)), int(np.argmax(mnr))
    if maj[mi] > mnr[ni]:
        return {"tempo": float(tempo), "energy": energy, "key": _keys[mi], "scale": "major"}
    return {"tempo": float(tempo), "energy": energy, "key": _keys[ni], "scale": "minor"}


@dataclass
class MusiCNNResult:
    embedding: np.ndarray
    num_patches: int
    tempo: float | None = None
    energy: float | None = None
    key: str | None = None
    scale: str | None = None
    moods: dict[str, float] | None = None


class MusiCNNEmbedder:
    def __init__(
        self,
        embedding_model_path: str | Path,
        prediction_model_path: str | Path | None = None,
    ) -> None:
        import onnxruntime as ort

        self._embedding_path = Path(embedding_model_path)
        self._prediction_path = Path(prediction_model_path) if prediction_model_path else None
        self._embedding_sess = ort.InferenceSession(
            str(self._embedding_path),
            providers=["CPUExecutionProvider"],
        )
        self._prediction_sess = None
        if self._prediction_path and self._prediction_path.is_file():
            self._prediction_sess = ort.InferenceSession(
                str(self._prediction_path),
                providers=["CPUExecutionProvider"],
            )
        self._embed_input = self._embedding_sess.get_inputs()[0].name
        self._embed_output = self._embedding_sess.get_outputs()[0].name

    def embed_audio(self, audio: np.ndarray, sr: int = SAMPLE_RATE) -> MusiCNNResult:
        if audio.size == 0 or not np.any(audio):
            raise ValueError("Empty audio signal")

        patches = prepare_spectrogram_patches(audio, sr)
        if patches is None:
            raise ValueError("Track too short for MusiCNN patches (~3 s minimum)")

        embeddings_per_patch = self._run_embedding(patches)
        vector = np.mean(embeddings_per_patch, axis=0)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        basic = extract_basic_features(audio, sr)
        moods = self._predict_moods(embeddings_per_patch) if self._prediction_sess else None

        return MusiCNNResult(
            embedding=vector.astype(np.float32),
            num_patches=int(patches.shape[0]),
            tempo=basic["tempo"],
            energy=basic["energy"],
            key=str(basic["key"]),
            scale=str(basic["scale"]),
            moods=moods,
        )

    def _run_embedding(self, patches: np.ndarray) -> np.ndarray:
        outputs = []
        for patch in patches:
            batch = patch[np.newaxis, ...].astype(np.float32)
            out = self._embedding_sess.run(
                [self._embed_output],
                {self._embed_input: batch},
            )[0]
            outputs.append(out[0])
        return np.stack(outputs, axis=0)

    def _predict_moods(self, embeddings_per_patch: np.ndarray) -> dict[str, float]:
        assert self._prediction_sess is not None
        pred_input = self._prediction_sess.get_inputs()[0].name
        pred_output = self._prediction_sess.get_outputs()[0].name
        (logits,) = self._prediction_sess.run(
            [pred_output],
            {pred_input: embeddings_per_patch.astype(np.float32)},
        )
        probs = _sigmoid(np.mean(_sigmoid(logits), axis=0))
        return {label: float(score) for label, score in zip(MOOD_LABELS, probs, strict=False)}


def top_moods(moods: dict[str, float] | None, n: int = 5) -> dict[str, float]:
    if not moods:
        return {}
    ranked = sorted(moods.items(), key=lambda item: item[1], reverse=True)
    return dict(ranked[:n])
