from __future__ import annotations
from pathlib import Path
from app.config import settings

def data_root() -> Path:
    p = Path(settings.data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p

def revision_root(rev_id: int) -> Path:
    p = data_root() / "datasets" / f"rev_{rev_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def model_root(model_id: str, version: str) -> Path:
    p = data_root() / "models" / model_id / version
    p.mkdir(parents=True, exist_ok=True)
    return p
