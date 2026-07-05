#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT}/data/fma"
FMA_BASE="https://os.unil.cloud.switch.ch/fma"

mkdir -p "${DATA_DIR}"

download_zip() {
  local name="$1"
  local dest="${DATA_DIR}/${name}"
  local url="${FMA_BASE}/${name}"

  if [[ -d "${DATA_DIR}/${name%.zip}" ]]; then
    echo "✓ ${name%.zip}/ already extracted"
    return 0
  fi
  if [[ -f "${dest}" ]]; then
    echo "✓ ${name} already downloaded"
  else
    echo "↓ downloading ${name} ..."
    curl -L --progress-bar -o "${dest}" "${url}"
  fi

  echo "↻ extracting ${name} ..."
  python3 - <<PY
import zipfile
from pathlib import Path

archive = Path("${dest}")
target = Path("${DATA_DIR}")
with zipfile.ZipFile(archive) as zf:
    zf.extractall(target)
print(f"extracted to {target}")
PY
}

echo "=== FMA metadata (~350 MB compressed) ==="
download_zip "fma_metadata.zip"

if [[ "${1:-}" == "--with-audio" ]]; then
  echo ""
  echo "=== FMA small audio (~7 GB compressed) ==="
  download_zip "fma_small.zip"
else
  echo ""
  echo "Audio not downloaded. To fetch fma_small (~7 GB):"
  echo "  bash scripts/download_fma.sh --with-audio"
  echo "  # or: make download-fma-audio"
fi

echo ""
echo "Expected layout:"
echo "  ${DATA_DIR}/fma_metadata/raw_tracks.csv"
echo "  ${DATA_DIR}/fma_small/000/000002.mp3"
echo ""
echo "Next: make infra-up && make ingest-fma [--with-s3]"
