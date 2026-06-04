from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import Form as FORM
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.core.queue import get_queue
from app.db.database import get_db
from app.db.models import CorpusItem, TrainingJob
from app.db.schemas import AdminRetrainResponse

from app.ai.model_registry import (
    REGISTRY_PATH,
    delete_registry_model,
    list_registry_models,
    set_default_model,
    upsert_registry_model,
)

DATA_DIR = Path("./data")
GLOSSARY_FILE = DATA_DIR / "glossary_kat_kiv.csv"
LABELS_FILE = DATA_DIR / "audio_labels.jsonl"
UPLOAD_AUDIO_DIR = DATA_DIR / "audio_uploads"

MODELS_DIR = Path("/models")
GGUF_DIR = MODELS_DIR / "gguf"

router = APIRouter(prefix="/admin", tags=["admin"])


# ----------------------------- Model registry (GGUF) -----------------------------


@router.get("/models")
def list_models(admin=Depends(get_admin_user)):
    """
    List available GGUF models.

    Sources:
      - registry.json (admin-managed)
      - scan of /models/*.gguf and /models/gguf/*.gguf
      - optional: app.ai.pipelines.list_available_llm_models() if present
    """
    GGUF_DIR.mkdir(parents=True, exist_ok=True)

    scanned = []
    for p in list(MODELS_DIR.glob("*.gguf")) + list(GGUF_DIR.glob("*.gguf")):
        scanned.append({"id": p.name, "path": str(p), "exists": True, "source": "scan"})

    # Optional: if you have a helper that also returns registry/availability
    extra = None
    try:
        from app.ai.pipelines import list_available_llm_models  # type: ignore

        extra = list_available_llm_models()
    except Exception:
        extra = None

    return {
        "registry_path": str(REGISTRY_PATH),
        "registered": list_registry_models(),
        "scanned": scanned,
        "available": extra,
    }


@router.post("/models/register")
def register_model(
    model_id: str,
    path: str,
    label: str | None = None,
    admin=Depends(get_admin_user),
):
    """Register an existing GGUF file (path inside container)."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {path}")
    if p.suffix.lower() != ".gguf":
        raise HTTPException(status_code=400, detail="Only .gguf files can be registered")

    upsert_registry_model(model_id=model_id, path=str(p), label=label)
    return {"ok": True}


@router.post("/models/set_default")
def set_default(model: str, admin=Depends(get_admin_user)):
    """Set default GGUF model (by id or filename/path depending on your registry impl)."""
    set_default_model(model)
    return {"ok": True}


@router.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    label: str | None = None,
    set_as_default: bool = False,
    admin=Depends(get_admin_user),
):
    """
    Upload a GGUF model into /models/gguf and register it.

    Uses streaming to disk to avoid RAM spikes.
    """
    if not file.filename or not file.filename.lower().endswith(".gguf"):
        raise HTTPException(status_code=400, detail="Please upload a .gguf file")

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GGUF_DIR / Path(file.filename).name

    # Stream to disk (safe for big files)
    with open(out_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            f.write(chunk)

    model_id = out_path.name
    upsert_registry_model(model_id=model_id, path=str(out_path), label=label or out_path.stem)

    if set_as_default:
        set_default_model(model_id)

    return {"ok": True, "id": model_id, "path": str(out_path), "default": set_as_default}


@router.delete("/models/{model_id}")
def delete_model(model_id: str, delete_file: bool = False, admin=Depends(get_admin_user)):
    """Remove model from registry. Optionally delete the underlying file."""
    reg_models = list_registry_models()
    target = next((m for m in reg_models if m.get("id") == model_id), None)

    delete_registry_model(model_id)

    if delete_file and target and target.get("path"):
        try:
            Path(str(target["path"])).unlink(missing_ok=True)
        except Exception:
            pass

    return {"ok": True}


# --------------------------------- Retrain/Jobs ---------------------------------


@router.post("/retrain", response_model=AdminRetrainResponse)
def retrain(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    """Enqueue a full 'retrain' pipeline (dialect + translate pack + dataset prep)."""

    last = db.query(TrainingJob).order_by(TrainingJob.id.desc()).first()
    next_ver = (
        f"v{(int(last.model_version[1:]) + 1) if last and last.model_version and last.model_version.startswith('v') else 1}"
    )

    job = TrainingJob(
        status="queued",
        model_version=next_ver,
        notes="Enqueued: dialect + translate + asr/tts manifests",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q = get_queue()
    q.enqueue("jobs.train_dialect_classifier:run", job.id, next_ver)
    q.enqueue("jobs.build_translation_pack:run", job.id, next_ver)
    q.enqueue("jobs.prepare_asr_dataset:run", job.id, next_ver)
    q.enqueue("jobs.prepare_tts_dataset:run", job.id, next_ver)

    return AdminRetrainResponse(job_id=job.id, status=job.status, model_version=job.model_version)


@router.post("/enqueue")
def enqueue(kind: str, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    """Enqueue a single training step: dialect, translate, asr_manifest, tts_manifest"""
    kind = kind.strip().lower()
    if kind not in {"dialect", "translate", "asr_manifest", "tts_manifest"}:
        raise HTTPException(status_code=400, detail="Invalid kind")

    last = db.query(TrainingJob).order_by(TrainingJob.id.desc()).first()
    next_ver = (
        f"v{(int(last.model_version[1:]) + 1) if last and last.model_version and last.model_version.startswith('v') else 1}"
    )

    job = TrainingJob(status="queued", model_version=next_ver, notes=f"Enqueued: {kind}")
    db.add(job)
    db.commit()
    db.refresh(job)

    q = get_queue()
    if kind == "dialect":
        q.enqueue("jobs.train_dialect_classifier:run", job.id, next_ver)
    elif kind == "translate":
        q.enqueue("jobs.build_translation_pack:run", job.id, next_ver)
    elif kind == "asr_manifest":
        q.enqueue("jobs.prepare_asr_dataset:run", job.id, next_ver)
    else:
        q.enqueue("jobs.prepare_tts_dataset:run", job.id, next_ver)

    return {"ok": True, "job_id": job.id, "model_version": next_ver}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    jobs = db.query(TrainingJob).order_by(TrainingJob.id.desc()).limit(20).all()
    return [
        {
            "id": j.id,
            "status": j.status,
            "model_version": j.model_version,
            "notes": j.notes,
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
        }
        for j in jobs
    ]


# -------------------------------- Uploads / Data --------------------------------


@router.post("/upload_glossary")
async def upload_glossary(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    content = await file.read()
    GLOSSARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOSSARY_FILE, "wb") as f:
        f.write(content)
    return {"ok": True, "path": str(GLOSSARY_FILE)}


@router.post("/upload_audio")
async def upload_audio(
    dialect: str = FORM(...),
    text: str = FORM(...),
    speaker: str = FORM("default"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user),
):
    """Upload a labeled wav file for future ASR/TTS training."""
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Please upload a .wav file")

    dialect = dialect.strip().upper()
    if dialect not in {"KIV", "KAT"}:
        raise HTTPException(status_code=400, detail="dialect must be KIV or KAT")

    UPLOAD_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = UPLOAD_AUDIO_DIR / file.filename

    content = await file.read()
    with open(out_path, "wb") as f:
        f.write(content)

    LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LABELS_FILE, "a", encoding="utf-8") as w:
        w.write(
            json.dumps(
                {"file": out_path.name, "dialect": dialect, "text": text, "speaker": speaker},
                ensure_ascii=False,
            )
            + "\n"
        )

    return {"ok": True, "file": out_path.name}


@router.post("/add_corpus")
async def add_corpus(
    dialect: str,
    text: str,
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user),
):
    item = CorpusItem(source="admin", dialect=dialect, text=text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}
