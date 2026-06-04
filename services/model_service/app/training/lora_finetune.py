from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Dict, Any, List, Optional

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def build_sft_texts(corpus_path: Path) -> List[str]:
    """Build supervised fine-tuning texts from either:
    - parallel format: {src, tgt, source, target}
    - mono format: {text, dialect}
    """
    rows = _read_jsonl(corpus_path)
    texts: List[str] = []
    for r in rows:
        if "src" in r and "tgt" in r:
            src = str(r.get("src", "")).strip()
            tgt = str(r.get("tgt", "")).strip()
            s = str(r.get("source", "KIV"))
            t = str(r.get("target", "KAT"))
            if src and tgt:
                texts.append(f"Translate {s} to {t}.\nInput: {src}\nOutput: {tgt}")
        elif "text" in r:
            txt = str(r.get("text", "")).strip()
            if txt:
                texts.append(txt)
    return texts

def run_lora_sft(
    base_model: str,
    corpus_path: Path,
    output_dir: Path,
    max_steps: int = 200,
    lr: float = 2e-4,
):
    """Minimal LoRA SFT pipeline (optional).

    Requires: torch, transformers, datasets, peft, accelerate
    Produces: adapter weights + tokenizer + training meta.

    Note: This does NOT export GGUF by itself. Use a separate merge+convert step (llama.cpp) afterwards.
    """
    try:
        import torch
        from datasets import Dataset
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
        from peft import LoraConfig, get_peft_model
    except Exception as e:
        raise RuntimeError(
            "LoRA deps not installed. Rebuild model_service with WITH_LORA=1 (see Dockerfile) "
            f"or install requirements-lora.txt. Details: {e}"
        )

    texts = build_sft_texts(corpus_path)
    if not texts:
        raise RuntimeError("Corpus is empty — upload corpus.jsonl before LoRA training.")

    ds = Dataset.from_dict({"text": texts})

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(base_model)
    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=512)

    ds_tok = ds.map(tok, batched=True, remove_columns=["text"])
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=lr,
        max_steps=max_steps,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to=[],
    )

    trainer = Trainer(model=model, args=args, train_dataset=ds_tok, data_collator=collator)
    trainer.train()

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir / "adapter"))
    tokenizer.save_pretrained(str(output_dir / "adapter"))

    return {"adapter_dir": str(output_dir / "adapter"), "base_model": base_model, "steps": max_steps, "lr": lr}
