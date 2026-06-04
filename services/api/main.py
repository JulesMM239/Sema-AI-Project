from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

from app.db.database import Base, engine
from app.routers import admin, auth, chat, conversations, translate, meta, model_admin

# Create tables (MVP). For production, use migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kivu–Katanga Swahili AI API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated audio
app.mount("/media", StaticFiles(directory="./data"), name="media")

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(translate.router)
app.include_router(admin.router)
app.include_router(model_admin.router)
app.include_router(meta.router)


@app.on_event("startup")
def _startup_paths():
    """Ensure important mounted directories exist.

    This avoids 'No such file or directory' issues when the host ./models folder
    is empty on first run.
    """
    # Training outputs live on the shared /models volume
    train_root = Path(os.getenv("TRAIN_OUTPUT_DIR", "/models/trained"))
    (train_root / "translate").mkdir(parents=True, exist_ok=True)
    (train_root / "dialect").mkdir(parents=True, exist_ok=True)
    (train_root / "asr").mkdir(parents=True, exist_ok=True)
    (train_root / "tts").mkdir(parents=True, exist_ok=True)

    # Model storage
    Path("/models/gguf").mkdir(parents=True, exist_ok=True)

    # App data dir (media)
    Path("./data").mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {"ok": True, "docs": "/docs"}
