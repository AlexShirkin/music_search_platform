"""FastAPI service: MP3 → MusiCNN embedding."""

from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import librosa
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from music_platform.audio.load import load_audio
from music_platform.config import Settings, get_settings
from music_platform.constants import EMBEDDING_DIM
from music_platform.db import connect
from music_platform.inference.musicnn import MusiCNNEmbedder, top_moods
from music_platform.schemas import EmbedRequest, EmbedResponse

app = FastAPI(title="inference-audio", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    model: str
    embedding_dim: int


@lru_cache
def get_embedder() -> MusiCNNEmbedder:
    settings = get_settings()
    return MusiCNNEmbedder(
        embedding_model_path=settings.musicnn_embedding_path,
        prediction_model_path=settings.musicnn_prediction_path,
    )


def _to_response(result, track_id: str | None = None) -> EmbedResponse:
    moods = result.moods
    return EmbedResponse(
        track_id=track_id,
        embedding=result.embedding.tolist(),
        embedding_dim=EMBEDDING_DIM,
        num_patches=result.num_patches,
        tempo=result.tempo,
        energy=result.energy,
        key=result.key,
        scale=result.scale,
        moods=moods,
        top_moods=top_moods(moods, n=5) if moods else None,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model="musicnn",
        embedding_dim=EMBEDDING_DIM,
    )


@app.post("/api/v1/embed", response_model=EmbedResponse)
async def embed_upload(file: UploadFile = File(...)) -> EmbedResponse:
    suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        audio, sr = librosa.load(tmp_path, sr=16000, mono=True)
        result = get_embedder().embed_audio(np.asarray(audio, dtype=np.float32), sr)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return _to_response(result)


@app.post("/api/v1/embed/path", response_model=EmbedResponse)
def embed_from_path(
    body: EmbedRequest,
    settings: Settings = Depends(get_settings),
) -> EmbedResponse:
    file_path = body.file_path
    track_id = body.track_id

    if not file_path and track_id:
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT file_path FROM tracks WHERE track_id = %s",
                    (track_id,),
                )
                row = cur.fetchone()
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail=f"Track not found: {track_id}")
        file_path = row[0]

    if not file_path:
        raise HTTPException(status_code=422, detail="Provide file_path or track_id")

    try:
        audio, sr = load_audio(file_path, settings=settings)
        result = get_embedder().embed_audio(audio, sr)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    return _to_response(result, track_id=track_id)
