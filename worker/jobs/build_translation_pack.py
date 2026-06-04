from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from worker.job_utils import update_job


def _load_glossary(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Accept both old and new column names
            kat = (r.get("katanga") or r.get("kat") or r.get("kat_word") or "").strip()
            kiv = (r.get("kivu") or r.get("kiv") or r.get("kivu_word") or "").strip()
            if kat and kiv:
                rows.append({"katanga": kat, "kivu": kiv})
    return rows


def run(job_id: int, model_version: str):
    """Build a translation 'pack' (glossary + normalization rules).

    This MVP pack is a deterministic translator used by the API.
    It is versioned and hot-swappable, and can be enhanced over time.

    Output:
      /models/trained/translate/<version>/phrase_table.json
      /models/trained/translate/<version>/meta.json
    """
    out_root = Path(os.getenv("TRAIN_OUTPUT_DIR", "/models/trained"))
    out_dir = out_root / "translate" / model_version
    out_dir.mkdir(parents=True, exist_ok=True)

    update_job(job_id, "running", notes="Building translation pack from glossary")

    # Source glossary path mounted from api data
    glossary_path = Path("/app/data") / "glossary_kat_kiv.csv"
    rows = _load_glossary(glossary_path)
    if len(rows) < 50:
        update_job(job_id, "failed", notes=f"Glossary too small: {len(rows)} rows. Add more entries and retry.")
        return

    # Build two maps (lowercase)
    kat_to_kiv = {}
    kiv_to_kat = {}
    for r in rows:
        kat_to_kiv[r["katanga"].lower()] = r["kivu"]
        kiv_to_kat[r["kivu"].lower()] = r["katanga"]

    phrase_table = {
        "kat_to_kiv": kat_to_kiv,
        "kiv_to_kat": kiv_to_kat,
    }

    (out_dir / "phrase_table.json").write_text(json.dumps(phrase_table, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "version": model_version,
        "glossary_rows": len(rows),
        "source": str(glossary_path),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    update_job(job_id, "done", notes=f"Translation pack built. Glossary rows={len(rows)}", model_version=model_version)
