from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.pipelines import chat_reply, transcribe_audio, tts
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, Message, User
from app.db.schemas import ChatReplyResponse, ChatTextRequest

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/chat", tags=["chat"])


def _ensure_conv(db: Session, user: User, conversation_id: int) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _history_for_llm(db: Session, conversation_id: int):
    msgs = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return [{"role": m.role, "content": m.text} for m in msgs if m.text]


@router.post("/text", response_model=ChatReplyResponse)
def chat_text(payload: ChatTextRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = _ensure_conv(db, user, payload.conversation_id)

    # store user msg
    u = Message(conversation_id=conv.id, role="user", text=payload.text, dialect=payload.dialect)
    db.add(u)

    history = _history_for_llm(db, conv.id)
    assistant_text, detected = chat_reply(
        payload.text,
        history=history,
        target_dialect=payload.dialect,
        model_id=getattr(payload, "model_id", None),
    )  # type: ignore

    audio_bytes = tts(assistant_text)
    filename = f"{uuid4().hex}.wav"
    audio_path = str((AUDIO_DIR / filename).as_posix())
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    a = Message(conversation_id=conv.id, role="assistant", text=assistant_text, dialect=detected, audio_path=f"audio/{filename}")
    db.add(a)

    # update title & updated_at
    if conv.title == "New chat":
        conv.title = (payload.text[:40] + "...") if len(payload.text) > 40 else payload.text
    conv.updated_at = datetime.utcnow()

    db.commit()

    return ChatReplyResponse(
        conversation_id=conv.id,
        detected_dialect=detected,
        assistant_text=assistant_text,
        assistant_audio_path=a.audio_path,
    )


@router.post("/audio", response_model=ChatReplyResponse)
async def chat_audio(
    conversation_id: int = Form(...),
    dialect: str = Form("AUTO"),
    model_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = _ensure_conv(db, user, conversation_id)
    audio_bytes = await file.read()

    user_text = transcribe_audio(audio_bytes, filename=file.filename or "audio.wav")
    u = Message(conversation_id=conv.id, role="user", text=user_text, dialect=dialect)
    db.add(u)

    history = _history_for_llm(db, conv.id)
    assistant_text, detected = chat_reply(user_text, history=history, target_dialect=dialect, model_id=model_id)  # type: ignore

    assistant_audio = tts(assistant_text)
    filename = f"{uuid4().hex}.wav"
    audio_path = str((AUDIO_DIR / filename).as_posix())
    with open(audio_path, "wb") as f:
        f.write(assistant_audio)

    a = Message(conversation_id=conv.id, role="assistant", text=assistant_text, dialect=detected, audio_path=f"audio/{filename}")
    db.add(a)

    if conv.title == "New chat":
        conv.title = (user_text[:40] + "...") if len(user_text) > 40 else user_text
    conv.updated_at = datetime.utcnow()

    db.commit()

    return ChatReplyResponse(
        conversation_id=conv.id,
        detected_dialect=detected,
        assistant_text=assistant_text,
        assistant_audio_path=a.audio_path,
    )
