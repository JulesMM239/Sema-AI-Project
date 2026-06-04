from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.ai.pipelines import transcribe_audio, translate_text as local_translate_text, tts
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import TranslateTextResponse
from app.integrations.model_service_client import ModelServiceClient

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/translate", tags=["translate"])


async def _translate_via_best_available(
    text: str,
    source_dialect: str,
    target_dialect: str,
    model_id: str | None,
    version: str | None,
) -> str:
    """Prefer external model_service if configured; fallback to local GGUF."""
    client = ModelServiceClient()
    if client.enabled():
        try:
            out = await client.translate(
                source_dialect=source_dialect,
                target_dialect=target_dialect,
                text=text,
                model_id=model_id or "sema-kiv-kat",
                version=version,
            )
            return out.get("translated_text", text)
        except Exception:
            # fallback to local
            pass

    return local_translate_text(text, source=source_dialect, target=target_dialect, model_id=model_id)  # type: ignore


@router.post("/text", response_model=TranslateTextResponse)
async def translate_text(
    source_dialect: str = Form(...),
    target_dialect: str = Form(...),
    text: str = Form(...),
    model_id: str | None = Form(None),
    version: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out_text = await _translate_via_best_available(text, source_dialect, target_dialect, model_id, version)
    audio_bytes = tts(out_text)
    filename = f"{uuid4().hex}.wav"
    (AUDIO_DIR / filename).write_bytes(audio_bytes)
    return TranslateTextResponse(translated_text=out_text, audio_path=f"audio/{filename}")


@router.post("/audio", response_model=TranslateTextResponse)
async def translate_audio(
    source_dialect: str = Form(...),
    target_dialect: str = Form(...),
    model_id: str | None = Form(None),
    version: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    audio_bytes = await file.read()
    text = transcribe_audio(audio_bytes, filename=file.filename or "audio.wav")
    out_text = await _translate_via_best_available(text, source_dialect, target_dialect, model_id, version)

    audio_bytes2 = tts(out_text)
    filename = f"{uuid4().hex}.wav"
    (AUDIO_DIR / filename).write_bytes(audio_bytes2)

    return TranslateTextResponse(translated_text=out_text, audio_path=f"audio/{filename}")
