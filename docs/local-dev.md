# Local development

## Prerequisites

- Python **3.11+**
- `make`, `curl`
- Docker + Docker Compose (этап 1+)

## Setup

```bash
cd music_search_platform

python3 -m venv .venv
source .venv/bin/activate

make install-dev
cp .env.example .env
```

## Этап 0 — проверка

```bash
make lint
make test
make download-models    # ~10 MB, MusiCNN ONNX
make smoke-musicnn      # synthetic audio → 200-d embedding
```

## Структура PYTHONPATH

Пакет `music_platform` живёт в `libs/`. Установка editable:

```bash
pip install -e .
```

Импорт:

```python
from music_platform.audio.spectrogram import prepare_spectrogram_patches
from music_platform.config import get_settings
```

## Порты (когда поднимется docker-compose)

| Сервис | URL |
|--------|-----|
| Web UI | http://localhost:3000 |
| Search API | http://localhost:8000/docs |
| Airflow | http://localhost:8080 |
| MinIO console | http://localhost:9001 |

## Troubleshooting

**`librosa` / `soundfile` ошибка при load:** на macOS может понадобиться `brew install libsndfile`.

**Модели не найдены:** `make download-models`, проверьте `MUSICNN_EMBEDDING_PATH` в `.env`.
