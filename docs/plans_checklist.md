# Чеклист реализации: Music Search Platform

> Эволюционный пошаговый план. Каждый этап даёт **рабочий инкремент** — можно остановиться и уже иметь демо.  
> Основной документ: [plans.md](./plans.md).  
> Обновляйте чекбоксы: `- [ ]` → `- [x]` по мере выполнения.

**Легенда:** `[ ]` не начато · `[~]` в работе · `[x]` готово · `[-]` пропущено / отложено

---

## Прогресс (сводка)

| Этап | Название | Статус | Gate (критерий готовности) |
|------|----------|--------|----------------------------|
| 0 | Фундамент | `[x]` | Репозиторий, модели, CI skeleton |
| 1 | Данные | `[ ]` | FMA small в MinIO + catalog в PostgreSQL |
| 2 | Inference slice | `[ ]` | 1 MP3 → 200-d vector через API |
| 3 | Similar search | `[ ]` | k-NN по track_id через Qdrant |
| 4 | Text search + UI | `[ ]` | Лендинг + форма → результаты в браузере |
| 5 | Airflow offline | `[ ]` | DAG analyze → index без ручных скриптов |
| 6 | Spark ETL | `[ ]` | Parquet catalog + export embeddings |
| 7 | CI/CD | `[ ]` | PR checks + build images on main |
| 8 | cloud.ru staging | `[ ]` | Staging URL открывается, поиск работает |
| 9 | cloud.ru prod | `[ ]` | Tag deploy + TLS + smoke tests |
| 10 | Расширения | `[-]` | Lyrics, clustering, метрики (опционально) |

**Текущий фокус:** _этап 1_

---

## Принцип эволюции

```
[0 Foundation] → [1 Data] → [2 Inference] → [3 Similar] → [4 Text+UI]
       → [5 Airflow] → [6 Spark] → [7 CI/CD] → [8 Staging] → [9 Prod] → [10 Optional]
```

Не перескакивать этапы: **Similar search (3)** возможен только после **Inference (2)**; **Text+UI (4)** — после индекса; **Airflow (5)** автоматизирует то, что уже работает вручную из (2–4).

---

## Этап 0 — Фундамент (≈ 3–5 дней)

**Цель:** скелет monorepo, модели на диске, минимальный CI.

### 0.1 Репозиторий и структура

- [x] Репозиторий `music_search_platform` создан (GitHub)
- [x] Monorepo-структура по [plans.md §6](./plans.md#6-структура-репозитория) (dags/, services/, libs/, …)
- [x] `README.md` — как поднять проект одной командой (placeholder ok)
- [x] `Makefile` — targets: `up`, `down`, `test`, `lint`
- [x] `pyproject.toml` — ruff, pytest, общие dev-зависимости
- [x] `.env.example` — шаблон переменных (без секретов)
- [x] `.gitignore` — models/, .env, __pycache__, .venv

### 0.2 Общая библиотека `libs/`

- [x] `libs/music_platform/config.py` — чтение env (DATABASE_URL, QDRANT_URL, S3_*)
- [x] `libs/music_platform/schemas.py` — pydantic: Track, SearchResult, EmbedRequest
- [x] `libs/music_platform/audio/spectrogram.py` — `prepare_spectrogram_patches()` (порт из AudioMuse)
- [x] Unit-тест spectrogram на синтетическом сигнале

### 0.3 Модели

- [x] `scripts/download_models.sh` — MusiCNN ONNX (ISC) с GitHub release v5.0.0-model
- [x] Модели лежат в `models/musicnn/` (gitignored)
- [x] Проверен inference MusiCNN локально (один скрипт smoke, без сервиса)

### 0.4 CI skeleton

- [x] `deploy/ci/github/ci.yml` — ruff + pytest на PR
- [x] `.github/workflows/ci.yml` — GitHub Actions workflow
- [x] CI проходит на пустом/минимальном коде (локально: `make lint test`)

### 0.5 Документация

- [x] `docs/architecture.md` — диаграмма + таблица сервисов
- [x] `docs/models.md` — лицензии, preprocessing mel-spec
- [x] `docs/local-dev.md` — порты, prerequisites

**Gate этапа 0:** `make lint test` зелёный; модели скачаны; spectrogram тест проходит.

---

## Этап 1 — Данные (≈ 2–4 дня)

**Цель:** каталог треков и аудио в инфраструктуре, без ML.

### 1.1 Локальная инфраструктура (docker-compose dev)

- [ ] `deploy/docker-compose/docker-compose.dev.yml` — postgres, minio, qdrant
- [ ] PostgreSQL: схема `tracks` (track_id, title, artist, album, genre, file_path, …)
- [ ] MinIO: bucket `music-search`, папки `raw/audio/`, `staging/`, `embeddings/`
- [ ] `make infra-up` поднимает только dev-стек

### 1.2 Датасет FMA small

- [ ] Скачан `fma_metadata.zip` + `fma_small.zip`
- [ ] Скрипт `scripts/ingest_fma.py` — парсинг metadata → PostgreSQL
- [ ] Аудио залито в MinIO `raw/audio/` (или локальный volume)
- [ ] В БД ≥ 1000 треков с валидным `file_path`
- [ ] `docs/datasets.md` — откуда данные, лицензия, команды ingest

**Gate этапа 1:** SQL `SELECT count(*) FROM tracks` > 1000; файлы доступны из MinIO.

---

## Этап 2 — Inference vertical slice (≈ 3–5 дней)

**Цель:** один HTTP-сервис: MP3 → embedding vector.

### 2.1 `services/inference-audio`

- [ ] FastAPI app: `GET /health`, `POST /api/v1/embed`
- [ ] Загрузка ONNX MusiCNN при старте (lazy ok)
- [ ] Input: file upload или path в MinIO
- [ ] Output: `{ "embedding": [200 floats], "tempo": …, "moods": … }`
- [ ] Dockerfile + healthcheck
- [ ] Unit-тест с mock ONNX или маленьким fixture

### 2.2 Batch-скрипт (до Airflow)

- [ ] `scripts/batch_embed.py` — N треков → parquet в MinIO `embeddings/dt=…/`
- [ ] Прогнано на 50–100 треках FMA small
- [ ] Запись embedding + track_id в PostgreSQL (таблица `embeddings` или jsonb в tracks)

**Gate этапа 2:** `curl -F file=@track.mp3 http://localhost:8001/api/v1/embed` → 200-d vector; batch parquet существует.

---

## Этап 3 — Similar search (≈ 3–5 дней)

**Цель:** «найти похожие» по audio embedding через Qdrant.

### 3.1 Qdrant + index-builder

- [ ] Collection `tracks_audio` (size=200, distance=Cosine)
- [ ] `services/index-builder` — читает parquet/PostgreSQL → upsert в Qdrant
- [ ] Id mapping: Qdrant point id ↔ track_id
- [ ] Пересборка индекса idempotent (upsert, не duplicate)

### 3.2 `services/search-api` (minimal)

- [ ] `GET /health`
- [ ] `POST /api/v1/search/similar` — `{ "track_id": "…", "limit": 20 }`
- [ ] Обогащение результатов metadata из PostgreSQL
- [ ] Dockerfile
- [ ] Добавлен в docker-compose рядом с qdrant, postgres

### 3.3 Smoke

- [ ] Index-builder залил ≥ 100 vectors
- [ ] Similar query возвращает осмысленные соседи (same genre чаще)
- [ ] `docs/api.md` — контракт similar search

**Gate этапа 3:** API similar search работает через curl/Postman без UI.

---

## Этап 4 — Text search + Web UI (≈ 4–7 дней)

**Цель:** лендинг с формой; текстовый запрос → результаты.

### 4.1 `services/inference-text`

- [ ] Загрузка `laion/larger_clap_music` (или ONNX export)
- [ ] `POST /api/v1/embed/text` — `{ "query": "calm piano" }` → 512-d
- [ ] Warmup endpoint (опционально)
- [ ] Dockerfile

### 4.2 Text index в Qdrant

- [ ] Отдельная collection `tracks_clap` или shared с payload `model=clap`
- [ ] Batch: embed catalog text-side через CLAP **audio** embeddings (offline) + text query at search time
- [ ] `POST /api/v1/search/text` в search-api

### 4.3 `services/web-ui`

- [ ] Лендинг: hero, описание проекта, форма поиска
- [ ] Поля: query (text), limit (number), submit
- [ ] JS fetch → search-api `POST /api/v1/search/text`
- [ ] Карточки результатов: title, artist, genre, score
- [ ] Состояния: loading / empty / error
- [ ] nginx Dockerfile; env `SEARCH_API_URL`
- [ ] CORS в search-api или same-origin proxy

### 4.4 Полный docker-compose

- [ ] `docker-compose.yml` — все сервисы: infra + inference-* + search-api + web-ui
- [ ] `make up` — открыть http://localhost:3000 → поиск работает
- [ ] `docs/web-ui.md` — UX, env, скриншоты (placeholder)

**Gate этапа 4:** пользователь в браузере вводит «calm piano» → видит список треков. **Demo-ready для портфолио.**

---

## Этап 5 — Airflow offline pipeline (≈ 4–7 дней)

**Цель:** автоматизировать analyze → embed → index (локальный Airflow).

### 5.1 Локальный Airflow

- [ ] Airflow в docker-compose (webserver + scheduler) или standalone
- [ ] `./dags` смонтирован в container
- [ ] Подключение (connection) к PostgreSQL, MinIO

### 5.2 DAG `analyze_embeddings`

- [ ] Task: получить pending tracks из PostgreSQL
- [ ] Task: batch call inference-audio (HTTP)
- [ ] Task: write parquet в MinIO
- [ ] Task: update status в PostgreSQL
- [ ] Retry + timeout на tasks

### 5.3 DAG `build_search_index`

- [ ] Task: trigger index-builder (PythonOperator / HTTP)
- [ ] Task: smoke `search/similar` + `search/text`
- [ ] Расписание: manual trigger сначала, `@daily` позже

### 5.4 DAG `data_quality` (minimal)

- [ ] Проверка: нет null embeddings, нет duplicate track_id
- [ ] Log metrics count в XCom или PostgreSQL

- [ ] `docs/airflow.md` — описание DAG, как запустить UI

**Gate этапа 5:** trigger DAG в Airflow UI → index обновлён → search работает без ручных скриптов.

---

## Этап 6 — Spark ETL (≈ 5–7 дней)

**Цель:** catalog/features через PySpark; подготовка к масштабу.

### 6.1 Локальный Spark

- [ ] Spark master/worker в docker-compose (или local `spark-submit`)
- [ ] Jars / config для MinIO (`s3a://`)

### 6.2 Spark jobs

- [ ] `spark_jobs/ingest_catalog.py` — metadata → `staging/catalog/` parquet
- [ ] `spark_jobs/export_embeddings.py` — normalize для index-builder
- [ ] `spark_jobs/merge_features.py` — stub или join с fake logs (фаза 2 LTR)
- [ ] Smoke: job отрабатывает на FMA small

### 6.3 Интеграция с Airflow

- [ ] DAG task запускает `spark-submit` (локально) или REST (cloud.ru позже)
- [ ] XCom передаёт output path parquet
- [ ] `docs/spark.md` — схемы, команды запуска

**Gate этапа 6:** Spark пишет parquet; Airflow DAG включает Spark step перед index build.

---

## Этап 7 — CI/CD (≈ 3–5 дней)

**Цель:** автоматическая проверка и сборка образов.

### 7.1 CI (`ci.yml`)

- [ ] Job: ruff lint
- [ ] Job: pytest unit
- [ ] Job: compile dags
- [ ] Job: build web-ui (npm build)
- [ ] Required check на PR в GitHub

### 7.2 Build (`build.yml`)

- [ ] Matrix docker build: search-api, inference-audio, inference-text, web-ui, index-builder
- [ ] Push в registry (локально — GHCR; cloud.ru — Artifact Registry позже)
- [ ] Tag = git SHA

### 7.3 Deploy (`deploy.yml`) — staging local/kind опционально

- [ ] Helm umbrella chart skeleton
- [ ] Charts: search-api, web-ui, inference-audio, qdrant (bitnami или custom)
- [ ] `helm upgrade --atomic` в kind/minikube (dry-run минимум)
- [ ] `docs/cicd.md` — secrets, triggers, rollback

**Gate этапа 7:** merge в main → images собраны; PR без зелёного CI не мержится.

---

## Этап 8 — cloud.ru staging (≈ 1–2 недели)

**Цель:** тот же функционал на облаке, публичный staging URL.

### 8.1 Инфраструктура cloud.ru

- [ ] Аккаунт, биллинг, квоты
- [ ] Object Storage bucket + структура папок (`dags/`, `jobs/`, `raw/`, `embeddings/`, `models/`)
- [ ] Data Platform cluster
- [ ] Managed Kubernetes + `kubectl` access
- [ ] Artifact Registry + push images
- [ ] Secret Management / GitHub secrets

### 8.2 Managed Airflow + Spark

- [ ] Managed Airflow инстанс; DAGs sync в S3 (`scripts/sync_dags_to_s3.sh`)
- [ ] Managed Spark инстанс; первый job `ingest_catalog.py`
- [ ] Airflow DAG вызывает Spark (API или documented workaround)
- [ ] `docs/cloudru.md` — пошаговый bootstrap

### 8.3 Deploy staging

- [ ] Namespace `music-search-staging`
- [ ] Helm deploy: web-ui, search-api, inference-*, qdrant, postgres (или managed DB)
- [ ] Ingress: staging.example.com → web-ui; `/api` → search-api
- [ ] TLS (cert-manager или cloud.ru)
- [ ] Модели в `s3://bucket/models/`
- [ ] FMA subset или полный ingest в staging bucket

### 8.4 Smoke staging

- [ ] `curl https://staging…/api/health` → 200
- [ ] Браузер: текстовый поиск возвращает результаты
- [ ] Airflow DAG run SUCCESS end-to-end

**Gate этапа 8:** staging URL можно показать на собеседовании / в README.

---

## Этап 9 — Production (≈ 3–5 дней)

**Цель:** стабильный prod deploy по tag.

- [ ] Namespace `music-search-prod`
- [ ] Deploy workflow: tag `v*.*.*` → prod (manual approval)
- [ ] Helm `--atomic` + rollback документирован
- [ ] Мониторинг minimal: health endpoints, логи в cloud.ru logging
- [ ] Backup PostgreSQL / Qdrant snapshot strategy (документ)
- [ ] Rate limit / Redis cache (опционально)
- [ ] README: prod URL, архитектура, demo video link (опционально)

**Gate этапа 9:** prod и staging изолированы; deploy по tag воспроизводим.

---

## Этап 10 — Расширения (опционально)

**Не блокирует MVP.** Отмечать `[x]` только если берётесь.

### 10.1 Lyrics pipeline

- [ ] Whisper-small ASR fallback
- [ ] GTE text embeddings
- [ ] Qdrant collection `tracks_lyrics`
- [ ] `POST /api/v1/search/lyrics`
- [ ] UI: mode «lyrics» в форме

### 10.2 Clustering / playlists

- [ ] `spark_jobs/cluster_tracks.py` — MLlib KMeans
- [ ] Airflow DAG export playlists
- [ ] UI: «playlist by cluster» (опционально)

### 10.3 Качество и метрики

- [ ] Offline nDCG evaluation script
- [ ] `data_quality` DAG расширен (Great Expectations)
- [ ] Prometheus metrics на search-api (latency, QPS)

### 10.4 Similar from UI

- [ ] Кнопка «найти похожие» на карточке трека
- [ ] `POST /api/v1/search/similar` из web-ui

---

## Быстрые команды (напоминание)

```bash
# Этап 0–1
make infra-up
./scripts/download_models.sh
python scripts/ingest_fma.py

# Этап 2–4
make up                    # полный стек
curl localhost:8000/health
open http://localhost:3000

# Этап 5
open http://localhost:8080  # Airflow UI

# Этап 7
git push && gh run list
```

---

## Журнал выполнения

| Дата | Этап | Что сделано |
|------|------|-------------|
| 2026-07-05 | 0 | Репозиторий клонирован; `plans.md` и `plans_checklist.md` перенесены в `docs/` |
| 2026-07-05 | 0 | Monorepo skeleton, libs/, CI, models, smoke MusiCNN — gate пройден |

_Добавляйте строки по мере прогресса._

---

## Связанные документы

| Документ | Путь |
|----------|------|
| Архитектурный план | [plans.md](./plans.md) |
| Разбор AudioMuse | _(локальный workspace)_ `docs/audiomuse-ai-analysis.md` |
| Ответы на интервью | _(локальный workspace)_ `docs/interview_answers.md` |
