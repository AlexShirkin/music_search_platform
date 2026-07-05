"""Unit tests for MusiCNN embedder (mocked ONNX)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from music_platform.audio.spectrogram import SAMPLE_RATE
from music_platform.inference.musicnn import MusiCNNEmbedder, extract_basic_features


def test_extract_basic_features_on_sine():
    duration = 5.0
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    features = extract_basic_features(audio, SAMPLE_RATE)
    assert "tempo" in features
    assert "energy" in features
    assert features["scale"] in {"major", "minor"}


@patch("onnxruntime.InferenceSession")
@patch.object(Path, "is_file", return_value=True)
def test_musicnn_embedder_mock(_mock_is_file, mock_session_cls):
    mock_session_cls.side_effect = _build_mock_sessions

    embedder = MusiCNNEmbedder(
        embedding_model_path="/fake/embedding.onnx",
        prediction_model_path="/fake/prediction.onnx",
    )

    audio = _sine(duration_sec=5.0)
    result = embedder.embed_audio(audio, SAMPLE_RATE)

    assert result.embedding.shape == (200,)
    assert abs(float(np.linalg.norm(result.embedding)) - 1.0) < 1e-5
    assert result.num_patches >= 1
    assert result.moods is not None
    assert "rock" in result.moods


def _sine(duration_sec: float, freq_hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def _build_mock_sessions(model_path, providers=None):
    session = MagicMock()
    if "embedding" in str(model_path):
        session.get_inputs.return_value = [MagicMock(name="input")]
        session.get_outputs.return_value = [MagicMock(name="output")]

        def run(outputs, feeds):
            batch = next(iter(feeds.values()))
            n = batch.shape[0]
            return [np.ones((n, 200), dtype=np.float32)]

        session.run.side_effect = run
    else:
        session.get_inputs.return_value = [MagicMock(name="pred_in")]
        session.get_outputs.return_value = [MagicMock(name="pred_out")]

        def run(outputs, feeds):
            batch = next(iter(feeds.values()))
            n = batch.shape[0]
            return [np.zeros((n, 50), dtype=np.float32)]

        session.run.side_effect = run
    return session


def test_musicnn_embedder_rejects_short_audio():
    with patch("onnxruntime.InferenceSession") as mock_session_cls:
        mock_session_cls.return_value = MagicMock()
        embedder = MusiCNNEmbedder(embedding_model_path="/fake/embedding.onnx")
        with pytest.raises(ValueError, match="too short"):
            embedder.embed_audio(_sine(duration_sec=1.0), SAMPLE_RATE)
