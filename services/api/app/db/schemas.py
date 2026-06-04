from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False


class CreateConversationResponse(BaseModel):
    conversation_id: int
    title: str


class ChatTextRequest(BaseModel):
    conversation_id: int
    text: str
    dialect: str = "AUTO"  # KAT/KIV/AUTO
    model_id: str | None = None


class ChatReplyResponse(BaseModel):
    conversation_id: int
    detected_dialect: str
    assistant_text: str
    assistant_audio_path: str


class TranslateTextRequest(BaseModel):
    text: str
    source_dialect: str
    target_dialect: str


class TranslateTextResponse(BaseModel):
    translated_text: str
    audio_path: str


class AdminRetrainResponse(BaseModel):
    job_id: int
    status: str
    model_version: str
