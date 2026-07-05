PYTHON ?= $(if $(wildcard .venv/bin/python),$(abspath .venv/bin/python),python3)
PIP ?= pip
COMPOSE_DEV := deploy/docker-compose/docker-compose.dev.yml

.PHONY: install install-dev lint format test test-integration up down infra-up infra-down infra-ps \
        download-models smoke-musicnn download-fma download-fma-audio ingest-fma injest-fma \
        migrate-db run-inference-audio batch-embed

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,inference,api]"

lint:
	ruff check libs scripts tests dags spark_jobs
	ruff format --check libs scripts tests dags spark_jobs

format:
	ruff format libs scripts tests dags spark_jobs

test:
	pytest tests/unit -v

test-integration:
	pytest tests/unit -v -m integration

infra-up:
	docker compose -f $(COMPOSE_DEV) up -d

infra-down:
	docker compose -f $(COMPOSE_DEV) down

infra-ps:
	docker compose -f $(COMPOSE_DEV) ps

up:
	@echo "Полный docker-compose стек — этап 4+"
	@if [ -f deploy/docker-compose/docker-compose.yml ]; then \
		docker compose -f deploy/docker-compose/docker-compose.yml up -d; \
	else \
		echo "deploy/docker-compose/docker-compose.yml ещё не создан"; \
		exit 1; \
	fi

down:
	@if [ -f deploy/docker-compose/docker-compose.yml ]; then \
		docker compose -f deploy/docker-compose/docker-compose.yml down; \
	fi

download-models:
	bash scripts/download_models.sh

download-fma:
	bash scripts/download_fma.sh

download-fma-audio:
	bash scripts/download_fma.sh --with-audio

ingest-fma:
	$(PYTHON) scripts/ingest_fma.py --upload-s3

injest-fma: ingest-fma

ingest-fma-local:
	$(PYTHON) scripts/ingest_fma.py

smoke-musicnn:
	$(PYTHON) scripts/smoke_musicnn.py

migrate-db:
	docker exec -i msp-postgres psql -U app -d music_search < deploy/docker-compose/init-db/002_embeddings.sql

run-inference-audio:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --app-dir services/inference-audio

batch-embed:
	$(PYTHON) scripts/batch_embed.py --limit 100 --upload-s3
