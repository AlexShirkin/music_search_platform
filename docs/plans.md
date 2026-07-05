# План: музыкальный search-платформа на Airflow + Spark

> Цель: построить сервис, **функционально близкий к AudioMuse-AI** (анализ аудио → эмбеддинги → ANN-поиск → API), но на стеке **Apache Airflow + Apache Spark**, с микросервисной архитектурой для **docker-compose (локально)** и **Kubernetes (cloud.ru)**.  
> Дата: июль 2026  
> Чеклист реализации: [plans_checklist.md](./plans_checklist.md)

### Расположение документации

| Папка | Назначение |
|-------|------------|
| **`docs/`** (корень этого репозитория) | План, чеклист, architecture, API, Airflow, Spark, cloud.ru, датасеты |
| **Материалы подготовки к собеседованию** | Вне репозитория (локальный workspace): анализ AudioMuse, ответы на интервью |

Вся документация по реализации — в **`docs/`** этого репозитория.

---

## Содержание

1. [Видение и границы MVP](#1-видение-и-границы-mvp)
2. [Зачем Airflow и Spark (роли компонентов)](#2-зачем-airflow-и-spark-роли-компонентов)
3. [Целевая архитектура](#3-целевая-архитектура)
4. [Микросервисы](#4-микросервисы)
5. [Модели: AudioMuse vs open-source](#5-модели-audiomuse-vs-open-source)
6. [Структура репозитория](#6-структура-репозитория)
7. [Локальный запуск: docker-compose](#7-локальный-запуск-docker-compose)
8. [Продакшен: cloud.ru](#8-продакшен-cloudru)
9. [Airflow DAG-и (черновик)](#9-airflow-dag-и-черновик)
10. [Spark jobs (черновик)](#10-spark-jobs-черновик)
11. [Документация в репозитории](#11-документация-в-репозитории)
12. [Фазы реализации](#12-фазы-реализации)
13. [Риски и решения](#13-риски-и-решения)
14. [Чеклист перед стартом на cloud.ru](#14-чеклист-перед-стартом-на-cloudru)
15. [Веб-лендинг и UI поиска](#15-веб-лендинг-и-ui-поиска)
16. [CI/CD](#16-cicd)

---

## 1. Видение и границы MVP

### Что строим

Платформу **music understanding + search** для каталога треков:

| Функция | MVP | Позже |
|---------|-----|-------|
| Batch-анализ аудио (embedding, mood, tempo) | ✅ | — |
| Текстовый поиск по звуку (CLAP-like) | ✅ | — |
| Поиск похожих треков (k-NN) | ✅ | — |
| **Веб-лендинг + форма поиска** | ✅ | — |
| **CI/CD** (test → build → deploy) | ✅ | prod/staging gates |
| Lyrics pipeline (ASR + text embedding) | ⚠️ опционально | полный parity с AudioMuse |
| Кластеризация / auto-playlists | ⚠️ Spark MLlib | эволюционный отбор как в AudioMuse |
| LLM chat-плейлисты | ❌ | фаза 3 |
| Интеграция с Jellyfin/Plex | ❌ | фаза 3 |

### Чем отличаемся от AudioMuse-AI

| | AudioMuse-AI | Наш проект |
|---|--------------|------------|
| Оркестрация | RQ + cron | **Airflow** |
| Batch ETL / feature store | PostgreSQL + Python workers | **Spark** на Object Storage |
| Inference | ONNX в worker-процессе | **Отдельный inference-сервис** (GPU pod) |
| Поиск | Custom paged IVF в PostgreSQL | **Qdrant / Milvus** (+ опционально Spark для batch scoring) |
| Деплой | monolith-ish containers | **Микросервисы** + Helm + **CI/CD** |

### Для чего это полезно на собеседовании (Сбер Звук)

Демонстрирует понимание **production search pipeline**: ingest → Spark features → embedding → index → serving API — на том же языке, что в вакансии (Python, PySpark, Airflow).

---

## 2. Зачем Airflow и Spark (роли компонентов)

### Apache Airflow — «когда и в каком порядке»

**Назначение:** оркестратор **batch/offline** пайплайнов с расписанием, retry, мониторингом и зависимостями между этапами.

| Задача | Почему Airflow, а не cron/RQ |
|--------|------------------------------|
| Ежедневный ingest новых треков | DAG с sensors, backfill, SLA alerts |
| Цепочка analyze → index → quality checks | Явные зависимости `task_a >> task_b` |
| Пересборка индекса после анализа | Trigger rule, branch по результатам |
| Запуск Spark job на cloud.ru | `SparkSubmitOperator` / REST к Managed Spark |
| Передача метаданных между этапами | XCom + пути в S3 (не большие данные) |

**Что Airflow НЕ делает:**
- не хранит терабайты аудио (→ Object Storage);
- не выполняет тяжёлый ML inference в scheduler (→ inference service / Spark);
- не обслуживает online search latency (→ search-api).

### Apache Spark — «массовая обработка данных»

**Назначение:** распределённая обработка каталога, join'ы, агрегации, подготовка feature store, batch-скоринг.

| Задача | Почему Spark |
|--------|--------------|
| Каталог 100K–10M треков | Параллельный scan metadata + join с логами |
| Feature engineering | Агрегации по artist/album/genre, temporal windows |
| Запись Parquet/Delta в S3 | Стандартный формат для ML pipelines |
| Дедупликация / data quality | Great Expectations + Spark |
| Кластеризация (KMeans/GMM) | Spark MLlib на embedding-матрице |
| Batch export в vector DB | Spark → write embeddings parquet → loader job |

**Что Spark НЕ делает в MVP:**
- real-time inference на каждый HTTP-запрос (слишком тяжело; → GPU inference pod);
- low-latency k-NN при поиске (→ Qdrant HNSW).

### Сводная таблица «кто за что отвечает»

| Компонент | Ответственность |
|-----------|-----------------|
| **Airflow** | Расписание, DAG, retry, запуск Spark/inference/index jobs |
| **Spark** | ETL, feature store, batch transforms, MLlib clustering |
| **Object Storage (S3)** | Аудио, parquet, артефакты, DAG-файлы (cloud.ru) |
| **PostgreSQL** | Метаданные треков, task lineage, конфиг |
| **Inference Service** | ONNX/PyTorch: waveform → embedding |
| **Index Service / Qdrant** | ANN index build + query |
| **Search API** | REST: text search, similar, health |
| **Web UI** | Лендинг + форма поиска для пользователей |
| **Redis** | Кэш hot queries, rate limit (опционально) |
| **Kubernetes** | Runtime для микросервисов |

---

## 3. Целевая архитектура

```
                         ┌─────────────────────────────────────┐
                         │     Evolution Managed Airflow        │
                         │  DAGs из S3: s3://bucket/dags/      │
                         └──────────────┬──────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
   ┌─────────────┐              ┌───────────────┐              ┌──────────────┐
   │  Ingest     │              │ Spark Job     │              │ Index Build  │
   │  (metadata) │─────────────►│ (ETL/features)│─────────────►│ (Qdrant)     │
   └─────────────┘              └───────┬───────┘              └──────┬───────┘
          │                             │                             │
          ▼                             ▼                             ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │              Evolution Object Storage (S3-compatible)                    │
   │  raw/audio/  staging/parquet/  embeddings/  jobs/  dags/  logs/       │
   └─────────────────────────────────────────────────────────────────────────┘
          │                             │
          ▼                             ▼
   ┌─────────────┐              ┌───────────────┐
   │ Inference   │◄─────────────│ Airflow trigger│
   │ Service GPU │   batch      │ (K8s Job/Cron) │
   └──────┬──────┘              └───────────────┘
          │
          ▼
   ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
   │  Qdrant     │◄────│  Search API  │◄────│  Web UI     │
   │  (ANN)      │     │  (FastAPI)   │     │  (лендинг)  │
   └─────────────┘     └──────────────┘     └──────┬──────┘
          ▲                                        │
   ┌──────┴──────┐                                 ▼
   │ PostgreSQL  │                          Users (browser)
   └─────────────┘

   ┌─────────────────────────────────────────┐
   │   Managed Kubernetes (cloud.ru)         │
   │   web-ui / search-api / inference / …   │
   └─────────────────────────────────────────┘

   ┌─────────────────────────────────────────┐
   │   CI/CD (GitHub Actions → Registry → K8s)│
   └─────────────────────────────────────────┘
```

---

## 4. Микросервисы

| Сервис | Стек | Порт | Назначение |
|--------|------|------|------------|
| `web-ui` | HTML/CSS/JS или Vite + nginx | 3000 / 80 | Лендинг, форма поиска, выдача результатов |
| `search-api` | FastAPI | 8000 | REST: search, similar, health, OpenAPI |
| `inference-audio` | Python + ONNX Runtime / PyTorch | 8001 | MusiCNN/CLAP embedding из аудио |
| `inference-text` | FastAPI + transformers | 8002 | Text query → embedding (CLAP text / GTE) |
| `index-builder` | Python | — | Batch job: parquet → Qdrant upsert |
| `catalog-api` | FastAPI | 8003 | CRUD метаданных треков (опционально) |
| `qdrant` | Qdrant | 6333 | Vector DB |
| `postgres` | PostgreSQL 15 | 5432 | Метаданные |
| `redis` | Redis 7 | 6379 | Кэш (опционально) |
| `minio` | MinIO | 9000 | S3 локально (вместо cloud Object Storage) |
| `airflow` | Airflow 2.x | 8080 | Локально; в cloud.ru — **Managed Airflow** |
| `spark` | Spark master/worker | — | Локально; в cloud.ru — **Managed Spark** |

**Принцип:** каждый сервис — отдельная папка в `services/`, свой `Dockerfile`, Helm chart в `deploy/helm/charts/<name>/`.

---

## 5. Модели: AudioMuse vs open-source

### Можно ли взять модели из AudioMuse?

Модели **публично доступны** на GitHub Releases, но с **разными лицензиями**:

| Модель | Источник | Лицензия | Можно в коммерческий продукт? |
|--------|----------|----------|-------------------------------|
| MusiCNN embedding/prediction | [v5.0.0-model](https://github.com/NeptuneHub/AudioMuse-AI/releases/tag/v5.0.0-model) | **ISC** | ✅ Да |
| CLAP text (`clap_text_model.onnx`) | тот же release | **CC0** (по LICENSE AudioMuse) | ✅ Да |
| DCLAP audio (`model_epoch_36.onnx`) | [AudioMuse-AI-DCLAP](https://github.com/NeptuneHub/AudioMuse-AI-DCLAP) | **AGPL-3.0** | ⚠️ Только при соблюдении AGPL или замене |
| Whisper-small (lyrics) | `lyrics_model_whisper.tar.gz` | OpenAI Whisper — **MIT** | ✅ Да |
| Silero VAD | release bundle | MIT (Silero) | ✅ Да |
| GTE multilingual INT8 | `lyrics_model_gte_vnni.tar.gz` | Проверить карточку модели | ⚠️ Уточнить |
| Код AudioMuse-AI | GitHub | **AGPL-3.0** | ⚠️ Нельзя копировать код в закрытый продукт без AGPL |

**Рекомендация для проекта:**

1. **MVP audio embedding:** взять **MusiCNN ONNX с release v5.0.0-model** (ISC) — совместим с вашим анализом AudioMuse, можно конвертировать pipeline 1:1.
2. **Text-to-audio search:** не DCLAP (AGPL), а **HuggingFace `laion/larger_clap_music`** (CC-BY 4.0) или `laion/larger_clap_music_and_speech` (Apache 2.0).
3. **Lyrics (фаза 2):** `openai/whisper-small` (MIT) + `thenlper/gte-small` или `intfloat/multilingual-e5-small` (Apache 2.0).
4. **Не использовать MERT** для коммерции — лицензия **CC-BY-NC 4.0** (non-commercial).

### Рекомендуемый model stack (open-source)

| Роль | Модель HF / источник | Размерность | Формат serving |
|------|----------------------|-------------|----------------|
| Audio similarity (основной) | MusiCNN ONNX (ISC, release) | 200 | ONNX Runtime |
| Text ↔ audio search | `laion/larger_clap_music` | 512 | PyTorch / ONNX export |
| Lyrics ASR | `openai/whisper-small` | — | faster-whisper / ONNX |
| Lyrics text embed | `thenlper/gte-small` | 384 | ONNX / sentence-transformers |
| Mood/tags (опционально) | MusiCNN prediction head | multi-label | ONNX |

### Где хранить веса

```
s3://<bucket>/models/
  musicnn/
    musicnn_embedding.onnx
    musicnn_prediction.onnx
  clap/
    laion_larger_clap_music/   # или свой ONNX export
  whisper/
    ...
```

Локально: volume `models/` монтируется в `inference-audio`. В CI: скачивание при сборке образа (как в AudioMuse Dockerfile) или init-container в K8s.

---

## 6. Структура репозитория

Корень репозитория `music_search_platform/` — monorepo deployable-проекта.

```
music_search_platform/                 # корень репозитория
├── README.md
├── Makefile
├── pyproject.toml
│
├── docs/                              # документация решения
│   ├── plans.md                       # этот файл
│   ├── plans_checklist.md             # пошаговый чеклист реализации
│   ├── architecture.md
│   ├── airflow.md
│   ├── spark.md
│   ├── models.md
│   ├── datasets.md
│   ├── cloudru.md
│   ├── local-dev.md
│   ├── api.md
│   ├── web-ui.md
│   └── cicd.md
│
├── dags/                              # Airflow DAG-и (синхронизируются в S3)
│   ├── daily_ingest.py
│   ├── analyze_embeddings.py
│   ├── build_search_index.py
│   └── data_quality.py
│
├── spark_jobs/                        # PySpark → s3a://bucket/jobs/
│   ├── ingest_catalog.py
│   ├── merge_features.py
│   ├── export_embeddings.py
│   └── cluster_tracks.py
│
├── libs/
│   └── music_platform/
│       ├── config.py
│       ├── s3.py
│       ├── audio/spectrogram.py
│       └── …
│
├── services/
│   ├── web-ui/                        # лендинг + search form
│   ├── search-api/
│   ├── inference-audio/
│   ├── inference-text/
│   ├── index-builder/
│   └── catalog-api/
│
├── deploy/
│   ├── docker-compose/
│   ├── helm/
│   └── ci/                            # GitHub Actions / GitLab CI
│       └── github/
│           ├── ci.yml                 # lint + test
│           ├── build.yml              # docker build + push
│           └── deploy.yml             # helm upgrade (manual/ tag)
│
├── tests/
└── scripts/
    ├── download_models.sh
    ├── sync_dags_to_s3.sh
    └── submit_spark_job.sh
```

### Правила организации кода

1. **`libs/`** — единственное место для общей логики (спектрограммы, S3 paths). Сервисы не дублируют код.
2. **`dags/`** — тонкие DAG-и: только оркестрация, бизнес-логика в `spark_jobs/` и `services/`.
3. **Версионирование образов:** `registry/cloudru/music-search/<service>:<git-sha>`.
4. **Конфиг:** env vars + `config.py` в libs; секреты — K8s Secrets / cloud.ru Secret Management.
5. **Документация:** всё про реализацию — в `docs/` этого репозитория; чеклист — [plans_checklist.md](./plans_checklist.md).

---

## 7. Локальный запуск: docker-compose

### Минимальный `docker-compose.yml` (концепт)

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: music_search
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]

  redis:
    image: redis:7-alpine

  inference-audio:
    build: ./services/inference-audio
    volumes:
      - ./models:/models:ro
    environment:
      MUSICNN_EMBEDDING_PATH: /models/musicnn_embedding.onnx

  search-api:
    build: ./services/search-api
    ports: ["8000:8000"]
    depends_on: [qdrant, postgres, inference-text]

  web-ui:
    build: ./services/web-ui
    ports: ["3000:80"]
    environment:
      SEARCH_API_URL: http://search-api:8000
    depends_on: [search-api]

  inference-text:
    build: ./services/inference-text

  airflow-webserver:
    image: apache/airflow:2.9.3
    # ... executor Local/Celery, mount ./dags

  airflow-scheduler:
    image: apache/airflow:2.9.3

  spark-master:
    image: bitnami/spark:3.5
    # для локальной отладки spark_jobs
```

### Локальный vs cloud.ru

| Компонент | Локально | cloud.ru |
|-----------|----------|----------|
| Airflow | Docker `apache/airflow` | **Managed Airflow** |
| Spark | `bitnami/spark` или `spark-submit` local | **Managed Spark** |
| S3 | MinIO | **Evolution Object Storage** |
| K8s | docker-compose (без K8s) или kind/minikube | **Managed Kubernetes** |
| Секреты | `.env` | **Secret Management** |

---

## 8. Продакшен: cloud.ru

### Официальная документация (ключевые ссылки)

| Сервис | Документация | Как используем |
|--------|--------------|----------------|
| **Managed Kubernetes** | [Обзор K8s](https://cloud.ru/docs/kubernetes-evolution/ug/index) | Runtime микросервисов (search-api, inference, qdrant) |
| **Managed Airflow** | [Обзор Airflow](https://cloud.ru/docs/managed-airflow/ug/doc-contents) | Оркестрация DAG |
| **DAG из S3** | [Туториал S3 DAG](https://cloud.ru/docs/managed-airflow/ug/topics/tutorials__s3-dag) | `dags/` → bucket → Airflow подхватывает |
| **Managed Spark** | [Продукт Spark](https://cloud.ru/products/evolution-managed-spark) | ETL, feature engineering |
| **Spark + S3** | [Туториал Spark S3](https://cloud.ru/docs/tutorials-evolution/list/topics/managed-spark__spark-s3) | `s3a://bucket/jobs/*.py` |
| **Data Platform** | [Платформа данных](https://cloud.ru/docs/tutorials-evolution/list/topics/index__dataplatform?source-platform=Evolution) | Единый кластер для Spark/Airflow |
| **Evolution Artifact Registry** | (из описания Spark) | Custom Docker images для inference |

### Типовой bootstrap на cloud.ru

```
1. Создать VPC / подсеть / DNS (по туториалам)
2. Создать Object Storage bucket:
      dags/
      jobs/          # spark_jobs
      raw/audio/
      staging/
      embeddings/
      models/
3. Создать кластер Data Platform
4. Создать инстанс Managed Airflow (публичный хост для UI)
      → привязать bucket, папка dags/
5. Создать инстанс Managed Spark
      → секрет в Secret Management для Spark UI
6. Создать Managed Kubernetes кластер
      → установить Helm charts (search-api, inference, qdrant)
      → GPU node pool для inference (Time-Slicing GPU — [документация K8s](https://cloud.ru/docs/kubernetes-evolution/ug/index))
7. CI/CD: push image → Artifact Registry → helm upgrade
8. GitHub Actions: PR → test; merge main → build + deploy staging
```

### Связка Airflow → Spark на cloud.ru

Паттерн из [туториала Spark](https://cloud.ru/docs/tutorials-evolution/list/topics/managed-spark__spark-s3):

1. Airflow DAG task загружает/обновляет `spark_jobs/merge_features.py` в `s3a://bucket/jobs/`.
2. Task вызывает **Managed Spark API** (создание задачи с путём `s3a://bucket/jobs/merge_features.py`).
3. Sensor/wait task ждёт статус «Выполнено».
4. Следующий task триггерит index-builder (K8s Job или HTTP к index-builder service).

> **Примечание:** точный Airflow operator для Managed Spark зависит от API cloud.ru — в фазе 0 проверить в личном кабинете: REST submit vs KubernetesPodOperator с spark-submit sidecar. Заложить абстракцию `SparkJobSubmitter` в `libs/`.

### Связка Airflow → Inference

Inference **не в Spark** (GPU, ONNX, мелкие батчи):

```
Airflow PythonOperator / K8sPodOperator:
  - читает список новых track_id из PostgreSQL / parquet
  - батчами вызывает inference-audio HTTP API
  - пишет embeddings в s3://embeddings/dt=2026-07-05/
```

---

## 9. Airflow DAG-и (черновик)

### `daily_ingest`

```
check_new_tracks >> ingest_metadata_to_pg >> sync_audio_to_s3 >> trigger_analyze
```

### `analyze_embeddings`

```
get_pending_tracks >> batch_inference_audio >> validate_embeddings >> write_parquet_s3
```

### `build_search_index`

```
export_embeddings_parquet >> build_qdrant_index >> smoke_test_search >> notify_success
```

### `data_quality`

```
check_null_embeddings >> check_duplicate_tracks >> report_metrics
```

**Передача данных между tasks:** только `s3://path` и `run_id` через XCom, не сами векторы.

---

## 10. Spark jobs (черновик)

### `ingest_catalog.py`

- Input: CSV/API dump каталога в S3
- Output: `staging/catalog/` parquet
- Join с существующими track_id в PostgreSQL (через JDBC)

### `merge_features.py`

- Input: catalog parquet + logs (plays, skips) + embeddings parquet
- Output: `features/track_features/` — табличные признаки для LTR (фаза 2)

### `export_embeddings.py`

- Input: `embeddings/*.parquet`
- Output: нормализованный датасет для Qdrant loader + статистики для DQ

### `cluster_tracks.py`

- Input: embedding matrix
- Spark MLlib KMeans / GMM
- Output: `clusters/` + playlist candidates

---

## 11. Документация

### `docs/` (этот репозиторий)

Каждый файл отвечает на вопрос **«что это и зачем»**:

| Файл | Содержание |
|------|------------|
| `plans.md` | Архитектурный план (этот документ) |
| `plans_checklist.md` | Пошаговый чеклист реализации |
| `architecture.md` | Диаграммы, data flow, границы сервисов |
| `airflow.md` | Список DAG, операторы, Managed Airflow + S3 |
| `spark.md` | Spark jobs, схемы parquet, submit в Managed Spark |
| `models.md` | Препроцессинг (mel-spec), лицензии, версии ONNX |
| `datasets.md` | Датасеты, ссылки на выгрузку, ingest |
| `cloudru.md` | Пошаговый bootstrap, ссылки, секреты, сеть |
| `local-dev.md` | `make up`, порты, тестовые запросы |
| `api.md` | OpenAPI контракт search-api |
| `web-ui.md` | Лендинг, UX, интеграция с search-api |
| `cicd.md` | Pipeline, secrets, окружения staging/prod |

В каждом сервисе: `services/<name>/README.md` — env vars, endpoints, healthcheck.

---

## 12. Фазы реализации

### Фаза 0 — Подготовка (1 неделя)

- [x] Создать репозиторий по структуре выше
- [x] `scripts/download_models.sh` — MusiCNN (ISC); CLAP — этап 4
- [x] `libs/music_platform/audio/spectrogram.py` — порт логики из AudioMuse
- [x] Документация в `docs/`: `architecture.md`, `models.md`
- [x] Skeleton `deploy/ci/github/ci.yml` (lint + pytest)

### Фаза 1 — Локальный MVP (2–3 недели)

- [ ] `inference-audio` — ONNX MusiCNN, POST `/embed`
- [ ] `search-api` — POST `/similar`, POST `/search/text`, GET `/health`
- [ ] `web-ui` — лендинг + форма текстового поиска + список результатов
- [ ] Qdrant + index-builder
- [ ] docker-compose полный стек
- [ ] Airflow local: DAG `analyze_embeddings` + `build_search_index`
- [ ] Spark local: `export_embeddings.py`

### Фаза 2 — cloud.ru (2–3 недели)

- [ ] Bucket + Data Platform cluster
- [ ] Managed Airflow: sync `dags/` в S3
- [ ] Managed Spark: первый ETL job
- [ ] K8s: Helm deploy web-ui + search-api + inference
- [ ] CI/CD: GitHub Actions build → Artifact Registry → helm upgrade
- [ ] End-to-end: DAG → Spark → inference → Qdrant → API → web-ui

### Фаза 3 — Search parity (по желанию)

- [ ] CLAP text search (`inference-text`)
- [ ] Lyrics pipeline (Whisper + GTE)
- [ ] Spark MLlib clustering
- [ ] Метрики nDCG offline, мониторинг

---

## 13. Риски и решения

| Риск | Митигация |
|------|-----------|
| AGPL DCLAP / код AudioMuse | Использовать ISC MusiCNN + HF CLAP, не копировать AGPL-код |
| Managed Spark ↔ Airflow интеграция не документирована детально | Абстракция submitter + fallback K8s Spark pod |
| GPU на cloud.ru | K8s GPU node pool, Time-Slicing; CPU fallback для dev |
| Inference bottleneck | Батчинг, горизонтальный scale inference pods |
| Холодный старт CLAP text (~478MB) | Warmup endpoint + lazy load как в AudioMuse |
| Лицензия MERT (NC) | Не использовать в коммерции |
| CORS web-ui ↔ search-api | Настроить `CORSMiddleware` в FastAPI + env `WEB_UI_ORIGIN` |
| Сломанный deploy без rollback | Helm `--atomic`, хранить предыдущий image tag |

---

## 15. Веб-лендинг и UI поиска

### Зачем

- **Демо для портфолио и собеседования** — видимый продукт, не только API в Swagger.
- **Smoke-test** production-пайплайна: пользователь вводит запрос → search-api → Qdrant → результаты на экране.
- Отделение **presentation layer** от backend (как в production search-системах).

### Сервис `web-ui`

| | |
|---|---|
| **Стек (MVP)** | Статический фронт (HTML + CSS + vanilla JS) или **Vite** + минимальный JS, сборка в nginx-образ |
| **Деплой** | Отдельный Docker-контейнер; в K8s — Ingress route `/` → web-ui, `/api` → search-api |
| **Конфиг** | `SEARCH_API_URL` — базовый URL search-api (в docker-compose: `http://search-api:8000`, в prod: публичный URL или same-origin через reverse proxy) |

### Структура страниц (MVP)

```
/                     # лендинг
├── hero: название проекта, краткое описание (music search demo)
├── search-form       # главный CTA
└── footer: ссылка на GitHub, Swagger /api/docs

/search               # опционально отдельный route; на MVP всё на /
```

### Форма поиска (MVP)

| Поле | Тип | Пример |
|------|-----|--------|
| **Query** | text input, required | `calm piano`, `energetic rock` |
| **Mode** | select (optional) | `text` (CLAP) / `similar` (disabled до фазы 3) |
| **Limit** | number, default 20 | top-K результатов |
| **Submit** | button | → POST `/api/v1/search/text` |

### UX результатов

- Список карточек: **title**, **artist**, **genre** (из PostgreSQL через search-api), **score** (similarity).
- Состояния: loading spinner, empty state («ничего не найдено»), error toast.
- Клик по треку (фаза 1.5): «найти похожие» → POST `/api/v1/search/similar?track_id=…`.

### Интеграция с search-api

```javascript
// web-ui вызывает search-api (CORS разрешён для WEB_UI_ORIGIN)
const resp = await fetch(`${SEARCH_API_URL}/api/v1/search/text`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, limit: 20 }),
});
```

Search-api обогащает Qdrant hits метаданными из PostgreSQL и возвращает JSON для UI.

### Reverse proxy (prod)

Чтобы не возиться с CORS, рекомендуется **единый домен**:

```
https://music-search.example.com/          → web-ui
https://music-search.example.com/api/      → search-api (Ingress path prefix)
```

Nginx Ingress или Traefik в K8s; локально — optional nginx sidecar в docker-compose.

### Helm

- Chart `deploy/helm/charts/web-ui/`
- ConfigMap: `SEARCH_API_URL=/api` (relative) при same-origin proxy
- Ingress: host + TLS (cert-manager на cloud.ru)

---

## 16. CI/CD

### Цели

| Цель | Как |
|------|-----|
| Не ломать main | lint + unit tests на каждый PR |
| Воспроизводимый образ | Docker build с tag = `git sha` |
| Безопасный deploy | staging автоматически, prod — по tag / manual approval |
| DAG/Spark jobs | sync в S3 отдельным workflow |

### Платформа

**GitHub Actions** (репозиторий на GitHub) — основной вариант.  
Альтернатива: GitLab CI (`.gitlab-ci.yml`) с теми же stages.

### Pipeline overview

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   PR push   │───►│  ci.yml     │───►│  build.yml   │───►│ deploy.yml  │
│             │    │ lint+test   │    │ docker push  │    │ helm upgrade│
└─────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                          │                                      │
                          ▼                                      ▼
                   merge blocked if fail              Artifact Registry → K8s
```

### Workflow `ci.yml` (на каждый PR и push)

| Job | Что делает |
|-----|------------|
| `lint-python` | `ruff check` libs/, services/, dags/, spark_jobs/ |
| `test-unit` | `pytest tests/unit` |
| `lint-dags` | `python -m py_compile dags/*.py` |
| `build-web-ui` | `npm ci && npm run build` в `services/web-ui` (fail fast) |

Без доступа к GPU и тяжёлым моделям в CI — inference тестируется mock'ами.

### Workflow `build.yml` (push в `main`, tags `v*`)

| Job | Что делает |
|-----|------------|
| `build-and-push` | matrix: `search-api`, `inference-audio`, `inference-text`, `web-ui`, `index-builder` |
| | `docker build -t $REGISTRY/$IMAGE:$SHA .` |
| | push в **Evolution Artifact Registry** (cloud.ru) |
| `sync-dags` | `aws s3 sync dags/ s3://$BUCKET/dags/` (Managed Airflow подхватывает) |
| `sync-spark-jobs` | `aws s3 sync spark_jobs/ s3://$BUCKET/jobs/` |

Secrets в GitHub: `CLOUDRU_REGISTRY_USER`, `CLOUDRU_REGISTRY_PASSWORD`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.

### Workflow `deploy.yml`

| Trigger | Действие |
|---------|----------|
| push `main` | auto deploy → **staging** namespace |
| tag `v*.*.*` | deploy → **production** (optional manual approval gate) |

```bash
helm upgrade --install music-search deploy/helm/umbrella \
  --namespace music-search-staging \
  --set global.imageTag=$GITHUB_SHA \
  --atomic --wait
```

Charts получают `imageTag` для всех сервисов из одного values.

### Окружения

| Env | K8s namespace | Домен | Данные |
|-----|---------------|-------|--------|
| **local** | docker-compose | localhost:3000 | MinIO + FMA small |
| **staging** | `music-search-staging` | staging.example.com | subset каталога |
| **prod** | `music-search-prod` | music-search.example.com | полный каталог |

### Что НЕ в CI (пока)

- Полный E2E с inference на GPU (дорого; отдельный nightly job позже).
- Обучение моделей — только inference pre-trained weights.
- Managed Spark/Airflow deploy — конфигурируется в cloud.ru UI, CI только sync scripts.

### Файлы в репозитории

```
deploy/ci/github/
├── ci.yml
├── build.yml
└── deploy.yml
```

Документация: `docs/cicd.md`.

---

## 14. Чеклист перед стартом на cloud.ru

- [ ] Аккаунт Cloud.ru, биллинг, квоты K8s/Spark
- [ ] Root-сертификат установлен ([инструкция Airflow](https://cloud.ru/docs/managed-airflow/ug/topics/tutorials__s3-dag))
- [ ] Object Storage bucket создан
- [ ] Data Platform cluster создан
- [ ] Managed Airflow инстанс + папка `dags/` в bucket
- [ ] Managed Spark инстанс + пароль в Secret Management
- [ ] Managed Kubernetes + `kubectl` доступ ([документация](https://cloud.ru/docs/kubernetes-evolution/ug/index))
- [ ] Artifact Registry для Docker images
- [ ] Модели загружены в `s3://bucket/models/`
- [ ] CI/CD: GitHub Actions (`ci.yml`, `build.yml`, `deploy.yml`) настроены
- [ ] Secrets в GitHub / Secret Management для registry и S3
- [ ] Ingress + TLS для web-ui и search-api
- [ ] Smoke-test после deploy: curl API + открыть лендинг в браузере

---

## Следующий шаг

Рекомендуемый порядок работ:

1. Пройти [чеклист](./plans_checklist.md) — этап 0: модели, `libs/`, CI skeleton.
2. Реализовать `libs/music_platform/audio/spectrogram.py` + `inference-audio` с MusiCNN ONNX (ISC).
3. Поднять `docker-compose` и прогнать один трек end-to-end.
4. Добавить `web-ui` с формой текстового поиска → `search-api`.
5. Параллельно завести `docs/architecture.md`, `cicd.md`, `web-ui.md`.

Если нужно — могу в следующем шаге сгенерировать скелет репозитория (папки, docker-compose, пустые сервисы, `download_models.sh`).
