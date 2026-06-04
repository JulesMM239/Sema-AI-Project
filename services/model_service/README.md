# SEMA Model Service (MVP) — versioned datasets + training pipeline + inference API

This is a **standalone microservice** that manages:
- **Dataset ingestion** (glossary, corpus, labeled audios)
- **Dataset revisioning** (every upload creates/updates a dataset revision)
- **Training runs** that produce **versioned model artifacts**
- **Model registry** (activate a version; list versions)
- **Inference API** (MVP translator using glossary/corpus; optional GGUF runtime hook)

It is designed to run as a separate service and communicate with **SEMA.AI** via HTTP.

> MVP note: the "training" step is a safe placeholder that produces a versioned artifact and registry entry.
> You can later plug your real pipeline (LoRA finetune + GGUF export) in `app/training/pipeline.py`.

---

## Quick start (Docker)

```bash
docker compose up -d --build
docker compose logs -f api worker
```

API: http://localhost:8010  
Swagger: http://localhost:8010/docs

---

## Key concepts

### Dataset revisions
A dataset revision groups:
- `glossary.csv`
- `corpus.jsonl`
- `audio/` wav files + `audio_labels.jsonl`

Every time you upload new data, a new `dataset_revision` can be created, or you can append to a draft revision.

### Model versions
A model version is created by a training run and produces a directory:

`/data/models/<model_id>/<version>/`
- `artifact.gguf` (placeholder file for MVP)
- `meta.json`

The service keeps a registry and one **active version** per model.

---

## Endpoints (core)

### Health
- `GET /health`

### Datasets
- `POST /datasets/revisions` create a new revision (draft)
- `POST /datasets/revisions/{rev_id}/glossary` upload CSV
- `POST /datasets/revisions/{rev_id}/corpus` upload JSONL
- `POST /datasets/revisions/{rev_id}/audio` upload WAV + labels (form fields)
- `POST /datasets/revisions/{rev_id}/finalize` finalize revision (immutable)
- `GET /datasets/revisions` list revisions

### Training / versioning
- `POST /train/start` (body: model_id, rev_id) -> returns run_id
- `GET /train/runs/{run_id}` -> status, produced version
- `GET /models` list model versions + active
- `POST /models/{model_id}/activate/{version}` activate version

### Inference (MVP)
- `POST /infer/translate` (source_dialect, target_dialect, text, model_id, version optional)

MVP translation uses the glossary in the **active** dataset revision linked to the active model version.
Later you can route to GGUF runtime.

---

## Integration with SEMA.AI

In SEMA.AI backend, call:

- `GET http://model-service:8010/models` to list versions
- `POST http://model-service:8010/infer/translate` to translate
- Optional: trigger training via `POST /train/start`

In docker-compose of SEMA.AI, add:

```yaml
model_service:
  build: ./sema_model_service_mvp
  ports: ["8010:8010"]
  environment:
    - DATABASE_URL=postgresql+psycopg://sema:sema@model_db:5432/sema_model
    - REDIS_URL=redis://model_redis:6379/0
    - DATA_DIR=/data
  volumes:
    - model_data:/data
```

---

## Default credentials / config
No auth in MVP. Add auth (API key/JWT) later in `app/security.py`.

---

## Notes for real training (next step)
Recommended practical path:
1) Prepare parallel corpus + glossary + audio labels
2) Train a small bilingual adapter (LoRA) on a base model
3) Merge/export to GGUF
4) Register the produced GGUF path in this service

Plug these steps in `app/training/pipeline.py`.
