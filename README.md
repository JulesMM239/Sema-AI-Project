<<<<<<< HEAD
# Kivu–Katanga Swahili AI (Local MVP)

This is a production‑oriented MVP (**Next.js UI + FastAPI API**) for a **voice‑first** Congolese Swahili assistant.

## What is local?

All AI operations run locally (no OpenAI / no external APIs):

- **ASR** (speech→text): `faster-whisper`
- **Chat LLM**: `llama.cpp` via `llama-cpp-python` (GGUF)
- **Dialect translation (KAT⇄KIV)**: glossary‑first + local LLM rewrite
- **TTS** (text→speech): Piper CLI (recommended). If Piper is not configured the API returns a short silent wav so the UI still plays audio.

> **Model weights are not bundled**. You place them in `./models/`.

## Quick start (Docker)

1) Copy env:

```bash
cp .env.example .env
```

2) Put your GGUF model in `./models/` and set `LLM_GGUF` in `.env`.

3) (Recommended) Install Piper (see below) and put the Swahili voice model files in `./models/`.

4) Run:

```bash
docker compose up --build
```

UI: http://localhost:3000
API docs: http://localhost:8000/docs

## Choosing an LLM GGUF

Any instruct model in GGUF works. Examples:

- Qwen2.5 Instruct
- Llama 3 Instruct
- Mistral Instruct

Pick a quantized file like `Q4_K_M` for CPU, or larger quant for GPU.

## Piper (TTS)

This MVP calls `./piper/piper` inside the container. You have two options:

### Option A: run without Piper (MVP still works)
Audio output will be a short silent WAV, but the assistant still replies with text.

### Option B: enable Piper (recommended)

1) Download Piper binary for Linux, place it at `./piper/piper` and make it executable:

```bash
chmod +x piper/piper
```

2) Download a Swahili voice model (`*.onnx` and `*.json`) and place them in `./models/`.

3) Set in `.env`:

```
PIPER_ONNX=your_swh_model.onnx
PIPER_JSON=your_swh_model.json
```

## Deploy on Ubuntu + Nginx

Run Docker Compose and reverse proxy with Nginx:

- Web UI (Next.js): `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`

Example Nginx conf is in `infra/nginx/kivu_katanga_ai.conf`.

## Where to edit the glossary

- `services/api/data/glossary_kat_kiv.csv`

You can also upload a new CSV from the Admin page.
=======
# Sema-AI-Project
IA des dialectes swahili de la RDC
>>>>>>> b79cd7515fe81e9df7a2b928c02336183cd52d2d
