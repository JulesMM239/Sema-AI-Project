from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import settings


def online_model_enabled() -> bool:
    return bool(settings.hf_model_repo and settings.hf_model_file)


def online_model_info() -> dict:
    return {
        "model_id": settings.hf_model_id,
        "version": "hf",
        "is_active": online_model_enabled(),
        "artifact_path": f"hf://{settings.hf_model_repo}/{settings.hf_model_file}",
        "source": "huggingface",
    }


@lru_cache(maxsize=1)
def _download_hf_model() -> str:
    if not online_model_enabled():
        raise RuntimeError("HF_MODEL_REPO and HF_MODEL_FILE must be configured")

    from huggingface_hub import hf_hub_download

    token = settings.hf_token or None
    return hf_hub_download(
        repo_id=settings.hf_model_repo,
        filename=settings.hf_model_file,
        cache_dir=settings.hf_cache_dir,
        token=token,
        local_files_only=False,
    )


@lru_cache(maxsize=2)
def _load_llama(model_path: str):
    from llama_cpp import Llama

    return Llama(
        model_path=model_path,
        n_ctx=settings.llm_ctx,
        n_threads=settings.llm_threads,
        n_gpu_layers=settings.llm_gpu_layers,
        verbose=False,
    )


def _glossary_context(glossary_path: Optional[str], limit: int = 80) -> str:
    if not glossary_path:
        return ""
    path = Path(glossary_path)
    if not path.exists():
        return ""

    rows: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            src, tgt = row[0].strip(), row[1].strip()
            if src and tgt:
                rows.append(f"- {src} => {tgt}")
            if len(rows) >= limit:
                break
    return "\n".join(rows)


def _complete(system: str, user: str) -> str:
    model_path = _download_hf_model()
    llm = _load_llama(model_path)

    if hasattr(llm, "create_chat_completion"):
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        text = response["choices"][0]["message"]["content"]
        return (text or "").strip()

    prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}\n\nASSISTANT:\n"
    response = llm(
        prompt,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        stop=["USER:", "SYSTEM:"],
    )
    return (response["choices"][0]["text"] or "").strip()


def translate_with_online_llm(
    text: str,
    source_dialect: str,
    target_dialect: str,
    glossary_path: Optional[str] = None,
) -> tuple[str, str]:
    glossary = _glossary_context(glossary_path)
    system = (
        "You are SEMA AI, a concise translator for Congolese Swahili dialects. "
        "Translate between Kivu Swahili and Katanga Swahili. Keep the meaning exact. "
        "Return only the translated text, with no explanation."
    )
    user = (
        f"Source dialect: {source_dialect}\n"
        f"Target dialect: {target_dialect}\n"
        f"Glossary hints:\n{glossary or '(none)'}\n\n"
        f"Text:\n{text}"
    )
    translated = _complete(system, user)
    return translated or text, "hf-gguf-llm"
