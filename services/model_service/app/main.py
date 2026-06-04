from __future__ import annotations

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi import Form as FORM
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import DatasetRevision, TrainingRun, ModelVersion
from app.schemas import (
    RevisionCreate, RevisionOut,
    TrainStart, TrainRunOut,
    ModelVersionOut,
    TranslateIn, TranslateOut,
)
from app.storage import revision_root
from app.utils import sha256_dir
from app.queue import get_queue
from app.jobs import training_job
from app.config import settings
from app.infer.translator import naive_translate

app = FastAPI(title="SEMA Model Service (MVP)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}

# -------------------------- Dataset revisions --------------------------

@app.post("/datasets/revisions", response_model=RevisionOut)
def create_revision(body: RevisionCreate, db: Session = Depends(get_db)):
    rev = DatasetRevision(name=body.name, status="draft")
    db.add(rev)
    db.commit()
    db.refresh(rev)
    # create folder
    revision_root(rev.id)
    return RevisionOut.model_validate(rev, from_attributes=True)

@app.get("/datasets/revisions", response_model=list[RevisionOut])
def list_revisions(db: Session = Depends(get_db)):
    revs = db.query(DatasetRevision).order_by(DatasetRevision.id.desc()).all()
    return [RevisionOut.model_validate(r, from_attributes=True) for r in revs]

def _get_rev(db: Session, rev_id: int) -> DatasetRevision:
    rev = db.get(DatasetRevision, rev_id)
    if not rev:
        raise HTTPException(status_code=404, detail="revision not found")
    return rev

@app.post("/datasets/revisions/{rev_id}/glossary", response_model=RevisionOut)
async def upload_glossary(rev_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    rev = _get_rev(db, rev_id)
    if rev.status != "draft":
        raise HTTPException(status_code=400, detail="revision is finalized")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="upload a .csv file")
    rev_dir = revision_root(rev_id)
    out = rev_dir / "glossary.csv"
    content = await file.read()
    out.write_bytes(content)
    rev.glossary_path = str(out)
    db.commit()
    db.refresh(rev)
    return RevisionOut.model_validate(rev, from_attributes=True)

@app.post("/datasets/revisions/{rev_id}/corpus", response_model=RevisionOut)
async def upload_corpus(rev_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    rev = _get_rev(db, rev_id)
    if rev.status != "draft":
        raise HTTPException(status_code=400, detail="revision is finalized")
    if not file.filename.lower().endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="upload a .jsonl file")
    rev_dir = revision_root(rev_id)
    out = rev_dir / "corpus.jsonl"
    out.write_bytes(await file.read())
    rev.corpus_path = str(out)
    db.commit()
    db.refresh(rev)
    return RevisionOut.model_validate(rev, from_attributes=True)

@app.post("/datasets/revisions/{rev_id}/audio", response_model=RevisionOut)
async def upload_audio(
    rev_id: int,
    dialect: str = FORM(...),
    text: str = FORM(...),
    speaker: str = FORM("default"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    rev = _get_rev(db, rev_id)
    if rev.status != "draft":
        raise HTTPException(status_code=400, detail="revision is finalized")
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="upload a .wav file")

    rev_dir = revision_root(rev_id)
    audio_dir = rev_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out = audio_dir / file.filename
    out.write_bytes(await file.read())

    labels = rev_dir / "audio_labels.jsonl"
    with open(labels, "a", encoding="utf-8") as w:
        w.write(
            f'{{"file":"{out.name}","dialect":"{dialect}","text":{text!r},"speaker":"{speaker}"}}\n'
        )

    rev.audio_dir = str(audio_dir)
    rev.audio_labels_path = str(labels)
    db.commit()
    db.refresh(rev)
    return RevisionOut.model_validate(rev, from_attributes=True)

@app.post("/datasets/revisions/{rev_id}/finalize", response_model=RevisionOut)
def finalize_revision(rev_id: int, db: Session = Depends(get_db)):
    rev = _get_rev(db, rev_id)
    if rev.status != "draft":
        return RevisionOut.model_validate(rev, from_attributes=True)
    rev.status = "final"
    rev.finalized_at = datetime.utcnow()
    rev.fingerprint = sha256_dir(revision_root(rev_id))
    db.commit()
    db.refresh(rev)
    return RevisionOut.model_validate(rev, from_attributes=True)

# -------------------------- Training runs --------------------------

@app.post("/train/start", response_model=TrainRunOut)
def train_start(body: TrainStart, db: Session = Depends(get_db)):
    rev = _get_rev(db, body.revision_id)
    if rev.status != "final":
        raise HTTPException(status_code=400, detail="revision must be finalized before training")

    run = TrainingRun(model_id=body.model_id, dataset_revision_id=rev.id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)

    q = get_queue()
    q.enqueue(training_job, run.id, settings.database_url)

    return TrainRunOut(id=run.id, model_id=run.model_id, revision_id=run.dataset_revision_id, status=run.status)

@app.get("/train/runs/{run_id}", response_model=TrainRunOut)
def train_status(run_id: int, db: Session = Depends(get_db)):
    run = db.get(TrainingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return TrainRunOut(
        id=run.id,
        model_id=run.model_id,
        revision_id=run.dataset_revision_id,
        status=run.status,
        produced_version=run.produced_version,
        error=run.error,
    )

# -------------------------- Model registry --------------------------

@app.get("/models")
def list_models(db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).order_by(ModelVersion.model_id, ModelVersion.created_at.desc()).all()
    out = {}
    for r in rows:
        out.setdefault(r.model_id, [])
        out[r.model_id].append(
            ModelVersionOut(
                model_id=r.model_id,
                version=r.version,
                is_active=r.is_active,
                artifact_path=r.artifact_path,
            ).model_dump()
        )
    return out

@app.post("/models/{model_id}/activate/{version}")
def activate_model(model_id: str, version: str, db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="model not found")
    target = None
    for r in rows:
        r.is_active = False
        if r.version == version:
            target = r
            r.is_active = True
    if not target:
        raise HTTPException(status_code=404, detail="version not found")
    db.commit()
    return {"ok": True, "model_id": model_id, "version": version}

def _get_active_version(db: Session, model_id: str) -> ModelVersion:
    mv = db.query(ModelVersion).filter(ModelVersion.model_id == model_id, ModelVersion.is_active == True).first()
    if not mv:
        # fallback: latest
        mv = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).order_by(ModelVersion.created_at.desc()).first()
    if not mv:
        raise HTTPException(status_code=404, detail="no model versions available")
    return mv

# -------------------------- Inference --------------------------

@app.post("/infer/translate", response_model=TranslateOut)
def infer_translate(body: TranslateIn, db: Session = Depends(get_db)):
    mv = _get_active_version(db, body.model_id) if not body.version else         db.query(ModelVersion).filter(ModelVersion.model_id == body.model_id, ModelVersion.version == body.version).first()

    if not mv:
        raise HTTPException(status_code=404, detail="model version not found")

    rev = db.get(DatasetRevision, mv.dataset_revision_id)
    glossary_path = rev.glossary_path if rev else None

    translated, method = naive_translate(body.text, glossary_path)

    return TranslateOut(
        model_id=mv.model_id,
        version=mv.version,
        translated_text=translated,
        method=method,
    )
