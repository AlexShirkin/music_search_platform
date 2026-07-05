# music_search_platform

Production-ready music search platform: **Airflow + Spark + Qdrant**.

## Roadmap

Полный чеклист: [docs/plans_checklist.md](docs/plans_checklist.md) · **Текущий фокус:** этап 2

- [x] Этап 0 — Фундамент: monorepo, `libs/`, MusiCNN, CI skeleton
- [x] Этап 1 — Данные: FMA small в MinIO + catalog в PostgreSQL
- [ ] Этап 2 — Inference slice: `inference-audio`, MP3 → 200-d embedding через HTTP
- [ ] Этап 3 — Similar search: Qdrant + `search-api`, k-NN по `track_id`
- [ ] Этап 4 — Text search + UI: лендинг, форма поиска, demo в браузере
- [ ] Этап 5 — Airflow offline: DAG analyze → embed → index
- [ ] Этап 6 — Spark ETL: PySpark catalog parquet, export embeddings
- [ ] Этап 7 — CI/CD: build images, Helm, deploy staging
- [ ] Этап 8 — cloud.ru staging: публичный URL, end-to-end в облаке
- [ ] Этап 9 — cloud.ru prod: deploy по tag, TLS, smoke tests
- [ ] Этап 10 — Расширения (опционально): lyrics, clustering, nDCG

Цепочка: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → (10)

## Quick start (этап 0)

```bash
python3.13 -m venv .venv && source .venv/bin/activate
make install-dev
make lint test
make download-models
make smoke-musicnn
```

## Quick start (этап 1 — данные)

```bash
cp .env.example .env
make infra-up                 # Postgres + MinIO + Qdrant
make download-fma             # metadata ~350 MB
make download-fma-audio       # audio ~7 GB (отдельно, долго)
make ingest-fma               # PostgreSQL + MinIO
```

Подробнее: [docs/datasets.md](docs/datasets.md)

## Документация

| Документ | Описание |
|----------|----------|
| [docs/plans.md](docs/plans.md) | Архитектурный план |
| [docs/plans_checklist.md](docs/plans_checklist.md) | Чеклист реализации |
| [docs/architecture.md](docs/architecture.md) | Компоненты и data flow |
| [docs/models.md](docs/models.md) | MusiCNN preprocessing, лицензии |
| [docs/local-dev.md](docs/local-dev.md) | Локальная разработка |
| [docs/datasets.md](docs/datasets.md) | FMA, ingest, MinIO |

## Makefile targets

| Target | Описание |
|--------|----------|
| `make install-dev` | editable install + dev/inference deps |
| `make lint` | ruff check + format check |
| `make test` | pytest unit |
| `make download-models` | MusiCNN ONNX (ISC) |
| `make smoke-musicnn` | локальный inference smoke |
| `make infra-up` / `make infra-down` | Postgres + MinIO + Qdrant (этап 1) |
| `make download-fma` | FMA metadata |
| `make download-fma-audio` | FMA small audio (~7 GB) |
| `make ingest-fma` | ingest в PostgreSQL + MinIO |
| `make up` / `make down` | полный docker-compose (этап 4+) |
