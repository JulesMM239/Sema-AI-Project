from __future__ import annotations

from fastapi import APIRouter

from app.ai.pipelines import list_available_llm_models
from app.integrations.model_service_client import ModelServiceClient


router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/models")
async def models():
    """List server-side available models.

    Returns:
      - local: GGUF models available to the SEMA.AI API
      - model_service: versions managed by the external model microservice (if configured)
    """
    local = list_available_llm_models()
    client = ModelServiceClient()

    model_service = None
    if client.enabled():
        try:
            model_service = await client.list_models()
        except Exception:
            # Keep UI working even if microservice is down
            model_service = {"error": "model_service_unreachable"}

    return {"models": local, "local": local, "model_service": model_service}


@router.get("/health")
def health():
    return {"ok": True}
