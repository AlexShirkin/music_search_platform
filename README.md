# music_search_platform

Production-ready music search platform: **Airflow + Spark + Qdrant**.

## Quick start (этап 0)

```bash
python3 -m venv .venv && source .venv/bin/activate
make install-dev
make lint test
make download-models
make smoke-musicnn
```

## Документация

| Документ | Описание |
|----------|----------|
| [docs/plans.md](docs/plans.md) | Архитектурный план |
| [docs/plans_checklist.md](docs/plans_checklist.md) | Чеклист реализации |
| [docs/architecture.md](docs/architecture.md) | Компоненты и data flow |
| [docs/models.md](docs/models.md) | MusiCNN preprocessing, лицензии |
| [docs/local-dev.md](docs/local-dev.md) | Локальная разработка |

## Makefile targets

| Target | Описание |
|--------|----------|
| `make install-dev` | editable install + dev/inference deps |
| `make lint` | ruff check + format check |
| `make test` | pytest unit |
| `make download-models` | MusiCNN ONNX (ISC) |
| `make smoke-musicnn` | локальный inference smoke |
| `make up` / `make down` | docker-compose (этап 1+) |
