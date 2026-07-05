#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${ROOT}/models/musicnn"
BASE_URL="https://github.com/NeptuneHub/AudioMuse-AI/releases/download/v5.0.0-model"

mkdir -p "${MODEL_DIR}"

download() {
  local name="$1"
  local dest="${MODEL_DIR}/${name}"
  if [[ -f "${dest}" ]]; then
    echo "✓ ${name} already exists"
    return 0
  fi
  echo "↓ downloading ${name}..."
  curl -fsSL -o "${dest}" "${BASE_URL}/${name}"
  echo "✓ ${name}"
}

download "musicnn_embedding.onnx"
download "musicnn_prediction.onnx"

echo ""
echo "Models saved to ${MODEL_DIR}/"
echo "License: ISC (MusiCNN weights from AudioMuse-AI v5.0.0-model release)"
