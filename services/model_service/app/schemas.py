from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

class RevisionCreate(BaseModel):
    name: str = "default"

class RevisionOut(BaseModel):
    id: int
    name: str
    status: str
    glossary_path: Optional[str] = None
    corpus_path: Optional[str] = None
    audio_dir: Optional[str] = None
    audio_labels_path: Optional[str] = None
    fingerprint: Optional[str] = None

class TrainStart(BaseModel):
    model_id: str = Field(..., examples=["sema-kiv-kat"])
    revision_id: int

class TrainRunOut(BaseModel):
    id: int
    model_id: str
    revision_id: int
    status: str
    produced_version: Optional[str] = None
    error: Optional[str] = None

class ModelVersionOut(BaseModel):
    model_id: str
    version: str
    is_active: bool
    artifact_path: str

class TranslateIn(BaseModel):
    source_dialect: str
    target_dialect: str
    text: str
    model_id: str = "sema-kiv-kat"
    version: Optional[str] = None

class TranslateOut(BaseModel):
    model_id: str
    version: str
    translated_text: str
    method: str
