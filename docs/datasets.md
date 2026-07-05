# Datasets

## FMA small (MVP)

| | |
|---|---|
| **Источник** | [FMA — Free Music Archive](https://github.com/mdeff/fma) |
| **Зеркало** | https://os.unil.cloud.switch.ch/fma/ |
| **Размер** | metadata ~350 MB; audio (fma_small) ~7 GB compressed, ~8 000 треков |
| **Лицензия** | Разная по трекам (CC). Для demo/исследований — OK; для prod уточнять per-track |

### Структура после загрузки

```
data/fma/
├── fma_metadata/
│   ├── raw_tracks.csv      # основной источник для ingest
│   └── genres.csv
└── fma_small/
    ├── 000/
    │   ├── 000002.mp3
    │   └── ...
    └── 001/
        └── ...
```

FMA *small* — **8 000 треков**, но `track_id` **не** ограничены диапазоном 0–7999.  
Ingest сканирует все MP3 в `fma_small/` и подтягивает metadata из `raw_tracks.csv`.

## Команды

```bash
# 1. Metadata (~350 MB)
make download-fma

# 2. Audio (~7 GB) — отдельно, долго
make download-fma-audio

# 3. Инфраструктура
cp .env.example .env
make infra-up

# 4. Ingest в PostgreSQL + MinIO
make ingest-fma          # с upload в S3
make ingest-fma-local    # только PostgreSQL, локальные пути
```

### Проверка gate этапа 1

```bash
docker exec -it msp-postgres psql -U app -d music_search \
  -c "SELECT COUNT(*) FROM tracks WHERE file_path IS NOT NULL;"
# ожидается > 1000
```

MinIO console: http://localhost:9001 (minioadmin / minioadmin)  
Bucket: `music-search`, prefix: `raw/audio/`

## Ingest options

```bash
python scripts/ingest_fma.py --help

python scripts/ingest_fma.py --limit 100              # smoke ingest
python scripts/ingest_fma.py --upload-s3              # + MinIO
python scripts/ingest_fma.py --data-dir /path/to/fma
```

## Дальше

После ingest — **этап 2**: `inference-audio` сервис, batch embed → parquet.
