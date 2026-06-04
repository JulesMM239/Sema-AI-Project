from __future__ import annotations

import json
import os
from pathlib import Path

import soundfile as sf

from worker.job_utils import update_job


def run(job_id: int, model_version: str):
    """Prepare a TTS dataset manifest from uploaded WAV files.

    Validates that each WAV has a corresponding text label in audio_labels.jsonl.

    Output:
      /models/trained/tts/<version>/manifest.jsonl
    """

    update_job(job_id, "running", notes="Preparing TTS dataset manifest from uploaded audio")

    data_dir = Path("/app/data")
    audio_dir = data_dir / "audio_uploads"
    labels_file = data_dir / "audio_labels.jsonl"
    if not audio_dir.exists() or not labels_file.exists():
        update_job(job_id, "failed", notes="Missing audio_uploads/ or audio_labels.jsonl. Upload audio + labels first.")
        return

    labels = {}
    for line in labels_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        fid = obj.get("file")
        if fid:
            labels[fid] = obj

    out_root = Path(os.getenv("TRAIN_OUTPUT_DIR", "/models/trained"))
    out_dir = out_root / "tts" / model_version
    out_dir.mkdir(parents=True, exist_ok=True)
    out_manifest = out_dir / "manifest.jsonl"

    kept = 0
    dropped = 0
    with out_manifest.open("w", encoding="utf-8") as w:
        for wav in sorted(audio_dir.rglob("*.wav")):
            key = wav.name
            meta = labels.get(key)
            if not meta or not meta.get("text"):
                dropped += 1
                continue
            try:
                info = sf.info(str(wav))
            except Exception:
                dropped += 1
                continue
            seconds = float(info.frames) / float(info.samplerate)
            if seconds < 0.6 or seconds > 15:
                dropped += 1
                continue

            w.write(
                json.dumps(
                    {
                        "path": str(wav),
                        "sr": info.samplerate,
                        "seconds": seconds,
                        "channels": info.channels,
                        "dialect": meta.get("dialect", ""),
                        "text": meta.get("text", ""),
                        "speaker": meta.get("speaker", "default"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            kept += 1

    update_job(job_id, "done", notes=f"TTS manifest ready: {kept} files kept, {dropped} dropped.", model_version=model_version)
