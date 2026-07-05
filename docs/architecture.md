# Architecture

> Music search platform — high-level design. Детали: [plans.md](./plans.md).

## Data flow

```
ingest → Spark ETL → inference (batch) → parquet → Qdrant index → search-api → web-ui
```

## Components

| Компонент | Роль |
|-----------|------|
| **Airflow** | Расписание, DAG, retry, запуск Spark / inference / index jobs |
| **Spark** | ETL, feature store, batch transforms |
| **Object Storage (MinIO / S3)** | Аудио, parquet, модели, DAG-артефакты |
| **PostgreSQL** | Метаданные треков |
| **inference-audio** | MusiCNN ONNX: waveform → 200-d embedding |
| **inference-text** | CLAP: text query → embedding (этап 4+) |
| **index-builder** | parquet → Qdrant upsert |
| **Qdrant** | ANN index (HNSW) |
| **search-api** | REST: similar, text search |
| **web-ui** | Лендинг + форма поиска |

## Локальные порты (целевые)

| Сервис | Порт |
|--------|------|
| web-ui | 3000 |
| search-api | 8000 |
| inference-audio | 8001 |
| inference-text | 8002 |
| Airflow UI | 8080 |
| PostgreSQL | 5432 |
| Qdrant | 6333 |
| MinIO | 9000 / 9001 |

## Репозиторий

Monorepo: `libs/` (общий код), `services/` (микросервисы), `dags/`, `spark_jobs/`, `deploy/`.
