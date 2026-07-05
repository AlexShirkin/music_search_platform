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

## Этап 1 — проверка

```bash
cp .env.example .env
make infra-up
make download-fma
make download-fma-audio   # ~7 GB
make ingest-fma
```

Gate: `SELECT COUNT(*) FROM tracks` > 1000. См. [datasets.md](./datasets.md).

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
