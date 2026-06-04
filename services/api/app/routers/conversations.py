from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, Message, User
from app.db.schemas import CreateConversationResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/new", response_model=CreateConversationResponse)
def new_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = Conversation(user_id=user.id, title="New chat")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return CreateConversationResponse(conversation_id=conv.id, title=conv.title)


@router.get("/list")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()}
        for c in convs
    ]


@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "text": m.text,
            "dialect": m.dialect,
            "audio_path": m.audio_path,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]
