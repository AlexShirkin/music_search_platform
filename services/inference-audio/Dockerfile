FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY libs ./libs
COPY services/inference-audio/app ./services/inference-audio/app

RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -e ".[inference,api]"

ENV PYTHONPATH=/app/libs
ENV MUSICNN_EMBEDDING_PATH=/models/musicnn/musicnn_embedding.onnx
ENV MUSICNN_PREDICTION_PATH=/models/musicnn/musicnn_prediction.onnx

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--app-dir", "/app/services/inference-audio"]
