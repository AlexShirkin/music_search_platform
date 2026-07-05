# inference-audio

MusiCNN ONNX service: audio file → 200-d embedding.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| POST | `/api/v1/embed` | Multipart file upload |
| POST | `/api/v1/embed/path` | JSON `{ "file_path": "..." }` or `{ "track_id": "2" }` |

## Run locally

```bash
make run-inference-audio
curl http://localhost:8001/health
curl -F file=@data/fma/fma_small/000/000002.mp3 http://localhost:8001/api/v1/embed
```

## Env

See root `.env.example` — `MUSICNN_EMBEDDING_PATH`, `MUSICNN_PREDICTION_PATH`, `DATABASE_URL`, S3 vars for `/embed/path`.
