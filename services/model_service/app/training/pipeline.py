from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from app.storage import model_root, revision_root
from app.utils import sha256_dir
from app.training.lora_finetune import run_lora_sft

def compute_revision_fingerprint(rev_id: int) -> str:
    return sha256_dir(revision_root(rev_id))

def next_version(existing_versions: list[str]) -> str:
    # versions like v1, v2...
    nums = []
    for v in existing_versions:
        if v.startswith("v"):
            try:
                nums.append(int(v[1:]))
            except Exception:
                pass
    n = max(nums) + 1 if nums else 1
    return f"v{n}"

def run_training(model_id: str, rev_id: int, version: str) -> dict:
    """Training entrypoint.

    Strategies:
      - TRAIN_STRATEGY=stub (default): produces placeholder artifact.gguf
      - TRAIN_STRATEGY=lora: runs LoRA SFT and outputs adapter weights (and a placeholder gguf marker)

    Env:
      - TRAIN_STRATEGY: stub|lora
      - LORA_BASE_MODEL: HF model id/path (e.g. Qwen/Qwen2.5-0.5B-Instruct)
      - LORA_MAX_STEPS: int
      - LORA_LR: float
    """
    rev_dir = revision_root(rev_id)
    fp = sha256_dir(rev_dir)

    out_dir = model_root(model_id, version)
    meta = out_dir / "meta.json"

    strategy = os.getenv("TRAIN_STRATEGY", "stub").lower().strip()

    result: dict = {"strategy": strategy}

    if strategy == "lora":
        base_model = os.getenv("LORA_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        max_steps = int(os.getenv("LORA_MAX_STEPS", "200"))
        lr = float(os.getenv("LORA_LR", "0.0002"))
        corpus_path = rev_dir / "corpus.jsonl"

        lora_out = run_lora_sft(
            base_model=base_model,
            corpus_path=corpus_path,
            output_dir=out_dir,
            max_steps=max_steps,
            lr=lr,
        )

        # Keep an "artifact.gguf" placeholder so the rest of the system can keep a consistent contract.
        # You will later replace it with a real GGUF export (merge + llama.cpp conversion).
        artifact = out_dir / "artifact.gguf"
        artifact.write_text(
            "LORA_ADAPTER_OUTPUT\n"
            f"adapter_dir={lora_out['adapter_dir']}\n"
            f"base_model={lora_out['base_model']}\n",
            encoding="utf-8",
        )

        result.update({"artifact_path": str(artifact), "adapter_dir": lora_out["adapter_dir"], "base_model": lora_out["base_model"]})
    else:
        # Placeholder GGUF artifact (replace with real export later)
        artifact = out_dir / "artifact.gguf"
        artifact.write_text(
            f"MVP GGUF PLACEHOLDER\nmodel_id={model_id}\nversion={version}\nrevision={rev_id}\nfingerprint={fp}\n",
            encoding="utf-8",
        )
        result.update({"artifact_path": str(artifact)})

    meta_obj = {
        "model_id": model_id,
        "version": version,
        "dataset_revision_id": rev_id,
        "dataset_fingerprint": fp,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "strategy": strategy,
        **{k: v for k, v in result.items() if k != "artifact_path"},
    }
    meta.write_text(json.dumps(meta_obj, indent=2), encoding="utf-8")

    result.update({"meta_path": str(meta), "fingerprint": fp})
    return result
