from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


REGISTRY_PATH = Path(os.getenv("LLM_REGISTRY_PATH", "/models/registry.json"))


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_registry() -> Dict[str, Any]:
    """Return registry structure.

    Format:
    {
      "default": "MyModel.gguf",
      "models": [
        {"id": "MyModel.gguf", "path": "/models/MyModel.gguf", "label": "MyModel"}
      ]
    }
    """
    data = _safe_read_json(REGISTRY_PATH)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("default", "")
    data.setdefault("models", [])
    if not isinstance(data["models"], list):
        data["models"] = []
    return data


def save_registry(data: Dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_registry_models() -> List[dict]:
    reg = load_registry()
    default = (reg.get("default") or "").strip()
    out: List[dict] = []
    for m in reg.get("models", []):
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id") or "").strip()
        path = str(m.get("path") or "").strip()
        if not mid or not path:
            continue
        out.append(
            {
                "id": mid,
                "path": path,
                "label": str(m.get("label") or mid),
                "exists": Path(path).exists(),
                "is_default": (default == mid or default == path),
                "source": "registry",
            }
        )
    return out


def upsert_registry_model(model_id: str, path: str, label: Optional[str] = None) -> Dict[str, Any]:
    reg = load_registry()
    models = reg.get("models", [])
    model_id = model_id.strip()
    path = path.strip()
    if not model_id or not path:
        raise ValueError("model_id and path are required")

    updated = False
    for m in models:
        if isinstance(m, dict) and str(m.get("id")) == model_id:
            m["path"] = path
            if label is not None:
                m["label"] = label
            updated = True
            break
    if not updated:
        models.append({"id": model_id, "path": path, "label": label or model_id})
    reg["models"] = models
    save_registry(reg)
    return reg


def set_default_model(model_id_or_path: str) -> Dict[str, Any]:
    reg = load_registry()
    reg["default"] = model_id_or_path.strip()
    save_registry(reg)
    return reg


def delete_registry_model(model_id: str) -> Dict[str, Any]:
    reg = load_registry()
    model_id = model_id.strip()
    reg["models"] = [m for m in reg.get("models", []) if not (isinstance(m, dict) and str(m.get("id")) == model_id)]
    if reg.get("default") == model_id:
        reg["default"] = ""
    save_registry(reg)
    return reg
