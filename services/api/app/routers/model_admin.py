from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from app.core.deps import get_admin_user
from app.integrations.model_service_client import ModelServiceClient

router = APIRouter(prefix="/admin/model-service", tags=["admin-model-service"])


def _client() -> ModelServiceClient:
    c = ModelServiceClient()
    if not c.enabled():
        raise HTTPException(status_code=400, detail="MODEL_SERVICE_URL not configured")
    return c


@router.get("/models")
async def models(admin=Depends(get_admin_user)):
    return await _client().list_models()


@router.post("/models/{model_id}/activate/{version}")
async def activate(model_id: str, version: str, admin=Depends(get_admin_user)):
    return await _client().activate_model(model_id, version)


@router.get("/revisions")
async def list_revisions(admin=Depends(get_admin_user)):
    return await _client().list_revisions()


@router.post("/revisions/create")
async def create_revision(name: str = Form("default"), admin=Depends(get_admin_user)):
    return await _client().create_revision(name)


@router.post("/revisions/{rev_id}/upload/glossary")
async def upload_glossary(
    rev_id: int,
    file: UploadFile = File(...),
    admin=Depends(get_admin_user),
):
    content = await file.read()
    return await _client().upload_glossary(rev_id, file.filename or "glossary.csv", content)


@router.post("/revisions/{rev_id}/upload/corpus")
async def upload_corpus(
    rev_id: int,
    file: UploadFile = File(...),
    admin=Depends(get_admin_user),
):
    content = await file.read()
    return await _client().upload_corpus(rev_id, file.filename or "corpus.jsonl", content)


@router.post("/revisions/{rev_id}/upload/audio")
async def upload_audio(
    rev_id: int,
    dialect: str = Form(...),
    text: str = Form(...),
    speaker: str = Form("default"),
    file: UploadFile = File(...),
    admin=Depends(get_admin_user),
):
    content = await file.read()
    return await _client().upload_audio(rev_id, dialect, text, speaker, file.filename or "audio.wav", content)


@router.post("/revisions/{rev_id}/finalize")
async def finalize_revision(rev_id: int, admin=Depends(get_admin_user)):
    return await _client().finalize_revision(rev_id)


@router.post("/train/start")
async def start_training(model_id: str = Form(...), revision_id: int = Form(...), admin=Depends(get_admin_user)):
    return await _client().start_training(model_id, revision_id)


@router.get("/train/runs/{run_id}")
async def run_status(run_id: int, admin=Depends(get_admin_user)):
    return await _client().run_status(run_id)
