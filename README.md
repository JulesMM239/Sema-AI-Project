# SEMA AI MVP

SEMA AI is a voice-first MVP for Congolese Swahili dialect support, focused on Kivu and Katanga Swahili.

Stack:
- Next.js web UI in `apps/web`
- FastAPI application API in `services/api`
- Dedicated model microservice in `services/model_service`
- Redis/Postgres workers for dataset and training jobs

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Local URLs:
- Web UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Model service docs: `http://localhost:8010/docs`

## Online Hugging Face GGUF Model

The model service can download and run an online GGUF model from Hugging Face through `llama-cpp-python`.

Example `.env` values for Qwen2.5 0.5B Instruct Q4_K_M:

```env
MODEL_SERVICE_URL=http://model_service:8010

HF_MODEL_ID=qwen2.5-0.5b-instruct-q4_k_m
HF_MODEL_REPO=bartowski/Qwen2.5-0.5B-Instruct-GGUF
HF_MODEL_FILE=Qwen2.5-0.5B-Instruct-Q4_K_M.gguf
HF_TOKEN=

LLM_CTX=4096
LLM_THREADS=4
LLM_GPU_LAYERS=0
LLM_MAX_TOKENS=256
```

On first inference, the model is downloaded into:

```text
./models/model_service_data/hf_cache
```

The API calls the model service through:

```text
services/api -> MODEL_SERVICE_URL -> services/model_service -> Hugging Face GGUF
```

## Local Or Online Deployment URLs

For local Docker without Nginx:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_MEDIA_BASE_URL=http://localhost:8000/media
```

For deployment behind the provided Nginx config:

```env
NEXT_PUBLIC_API_BASE_URL=/api
NEXT_PUBLIC_MEDIA_BASE_URL=/media
```

## MVP Notes

- Text/audio translation routes prefer the model microservice when `MODEL_SERVICE_URL` is configured.
- If no Hugging Face GGUF is configured, translation falls back to the local glossary/echo MVP behavior.
- `TRAIN_STRATEGY=stub` still produces placeholder artifacts. Use `TRAIN_STRATEGY=lora` only after installing the heavier LoRA dependencies and completing the export path.
