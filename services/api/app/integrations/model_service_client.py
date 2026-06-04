from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class ModelServiceClient:
    """HTTP client for the external SEMA Model Service microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("MODEL_SERVICE_URL", "")).rstrip("/")

    def enabled(self) -> bool:
        return bool(self.base_url)

    async def _get(self, path: str) -> Dict[str, Any]:
        if not self.enabled():
            raise RuntimeError("MODEL_SERVICE_URL is not set")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}{path}")
            r.raise_for_status()
            return r.json()

    async def _post(self, path: str, json_body: Dict[str, Any] | None = None, files=None, data=None) -> Dict[str, Any]:
        if not self.enabled():
            raise RuntimeError("MODEL_SERVICE_URL is not set")
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}{path}", json=json_body, files=files, data=data)
            r.raise_for_status()
            return r.json()

    async def health(self) -> Dict[str, Any]:
        return await self._get("/health")

    async def list_models(self) -> Dict[str, Any]:
        return await self._get("/models")

    async def list_revisions(self) -> list[Dict[str, Any]]:
        return await self._get("/datasets/revisions")  # type: ignore

    async def create_revision(self, name: str) -> Dict[str, Any]:
        return await self._post("/datasets/revisions", json_body={"name": name})

    async def upload_glossary(self, rev_id: int, filename: str, content: bytes) -> Dict[str, Any]:
        files = {"file": (filename, content, "text/csv")}
        return await self._post(f"/datasets/revisions/{rev_id}/glossary", files=files)

    async def upload_corpus(self, rev_id: int, filename: str, content: bytes) -> Dict[str, Any]:
        files = {"file": (filename, content, "application/jsonl")}
        return await self._post(f"/datasets/revisions/{rev_id}/corpus", files=files)

    async def upload_audio(self, rev_id: int, dialect: str, text: str, speaker: str, filename: str, content: bytes) -> Dict[str, Any]:
        data = {"dialect": dialect, "text": text, "speaker": speaker}
        files = {"file": (filename, content, "audio/wav")}
        return await self._post(f"/datasets/revisions/{rev_id}/audio", files=files, data=data)

    async def finalize_revision(self, rev_id: int) -> Dict[str, Any]:
        return await self._post(f"/datasets/revisions/{rev_id}/finalize")

    async def start_training(self, model_id: str, revision_id: int) -> Dict[str, Any]:
        return await self._post("/train/start", json_body={"model_id": model_id, "revision_id": revision_id})

    async def run_status(self, run_id: int) -> Dict[str, Any]:
        return await self._get(f"/train/runs/{run_id}")

    async def activate_model(self, model_id: str, version: str) -> Dict[str, Any]:
        return await self._post(f"/models/{model_id}/activate/{version}")

    async def translate(self, source_dialect: str, target_dialect: str, text: str, model_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "source_dialect": source_dialect,
            "target_dialect": target_dialect,
            "text": text,
            "model_id": model_id,
        }
        if version:
            payload["version"] = version
        return await self._post("/infer/translate", json_body=payload)
