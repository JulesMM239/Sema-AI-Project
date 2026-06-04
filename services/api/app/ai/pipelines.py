from __future__ import annotations

"""
Local AI pipelines (no OpenAI dependency).

Components (all local):
- ASR: faster-whisper
- Chat: llama.cpp via llama-cpp-python (GGUF)
- Dialect translation: glossary-first + local LLM rewriting
- TTS: Piper CLI if available (recommended); otherwise generates a short silent WAV.

Model weights are NOT bundled in the repo. See README for download steps.
"""

import json
import os
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from app.ai.dialect import Dialect, detect_dialect
from app.ai.glossary import glossary_snippet
from app.ai.model_registry import list_registry_models, load_registry


# ----------------------------- ASR (faster-whisper) -----------------------------

_WHISPER_MODEL = None


def _get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL

    # Lazy import to keep startup fast.
    from faster_whisper import WhisperModel

    model_size_or_path = os.environ.get("ASR_MODEL", "small")
    device = os.environ.get("ASR_DEVICE", "cpu")
    compute_type = os.environ.get("ASR_COMPUTE_TYPE", "int8")
    _WHISPER_MODEL = WhisperModel(model_size_or_path, device=device, compute_type=compute_type)
    return _WHISPER_MODEL


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    model = _get_whisper_model()
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        segments, _info = model.transcribe(tmp.name, language="sw")
        return " ".join([seg.text.strip() for seg in segments]).strip()


# ----------------------------- Chat (llama.cpp) --------------------------------

# Cache by model_path to allow switching models later
_LLM_CACHE: Dict[str, object] = {}


def list_available_llm_models() -> List[dict]:
    """Return available GGUF models based on environment variables.

    Supported env:
      - LLM_MODEL_PATH=/models/xxx.gguf
      - LLM_MODEL_PATHS=/models/a.gguf;/models/b.gguf
      - LLM_DEFAULT_MODEL=a.gguf (basename) or full path
    """
    # 1) Registry (admin-managed) has priority
    registry_models = list_registry_models()

    # 2) Env-based list (fallback)
    paths: List[str] = []
    p_single = os.environ.get("LLM_MODEL_PATH", "").strip()
    if p_single:
        paths.append(p_single)

    p_multi = os.environ.get("LLM_MODEL_PATHS", "").strip()
    if p_multi:
        paths.extend([x.strip() for x in p_multi.split(";") if x.strip()])

    default_env = os.environ.get("LLM_DEFAULT_MODEL", "").strip()
    default_reg = (load_registry().get("default") or "").strip()
    out: List[dict] = []

    # Start with registry models
    out.extend(registry_models)

    # Also scan /models for *.gguf (so admins can upload/copy a file and then register it)
    try:
        scanned = []
        for gguf in Path("/models").glob("*.gguf"):
            scanned.append(
                {
                    "id": gguf.name,
                    "path": str(gguf),
                    "exists": True,
                    "is_default": (default_reg == gguf.name or default_reg == str(gguf)),
                    "source": "scan",
                }
            )
        # Don't duplicate ids already in registry
        existing_ids = {m.get("id") for m in out}
        for s in scanned:
            if s.get("id") not in existing_ids:
                out.append(s)
    except Exception:
        pass
    seen = set(m.get("path") for m in out if m.get("path"))
    for p in paths:
        try:
            mp = Path(p)
            key = str(mp.resolve())
        except Exception:
            key = p
            mp = Path(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": mp.name,
                "path": str(mp),
                "exists": mp.exists(),
                "is_default": (
                    default_reg == str(mp)
                    or default_reg == mp.name
                    or default_env == str(mp)
                    or default_env == mp.name
                    or ((not default_env and not default_reg) and p == p_single)
                ),
                "source": "env",
            }
        )
    return out


def resolve_llm_model_path(model_id: Optional[str] = None) -> Optional[str]:
    """Resolve a model id (basename or full path) to an existing file path if possible."""
    candidates = list_available_llm_models()
    if not candidates:
        return _resolve_model_path()

    if model_id:
        mid = model_id.strip()
        for c in candidates:
            if c.get("path") == mid or c.get("id") == mid:
                return c.get("path")

    # fallback to default
    for c in candidates:
        if c.get("is_default"):
            return c.get("path")
    return candidates[0].get("path")


def _resolve_model_path() -> Optional[str]:
    """
    Primary:
      - LLM_MODEL_PATH=/models/gguf/xxx.gguf

    Optional multi-model:
      - LLM_MODEL_PATHS=/models/a.gguf;/models/b.gguf
      - LLM_DEFAULT_MODEL=... (full path or filename)
    """
    p = os.environ.get("LLM_MODEL_PATH")
    if p:
        return p

    paths = os.environ.get("LLM_MODEL_PATHS", "").strip()
    if not paths:
        return None

    candidates = [x.strip() for x in paths.split(";") if x.strip()]
    if not candidates:
        return None

    default = os.environ.get("LLM_DEFAULT_MODEL", "").strip()
    if default:
        # allow matching by full path or basename
        for c in candidates:
            if c == default or Path(c).name == default:
                return c

    return candidates[0]


def _get_llm(model_path: Optional[str] = None):
    """
    Return a llama.cpp model instance.

    Requires GGUF file path (env LLM_MODEL_PATH or resolved via _resolve_model_path()).
    """
    model_path = model_path or _resolve_model_path()
    if not model_path:
        return None

    mp = Path(model_path)
    if not mp.exists():
        return None

    key = str(mp.resolve())
    if key in _LLM_CACHE:
        return _LLM_CACHE[key]

    from llama_cpp import Llama

    n_ctx = int(os.environ.get("LLM_CTX", "4096"))
    n_threads = int(os.environ.get("LLM_THREADS", "4"))
    n_gpu_layers = int(os.environ.get("LLM_GPU_LAYERS", "0"))

    llm = Llama(
        model_path=key,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )
    _LLM_CACHE[key] = llm
    return llm


def _system_prompt(target_dialect: Dialect) -> str:
    g = glossary_snippet(60)
    return (
        "You are a helpful, friendly voice-first assistant for Congolese Swahili, focused on two dialects: "
        "Katanga (KAT) and Kivu (KIV).\n"
        "Rules:\n"
        "- If user chooses a dialect, reply in that dialect. If AUTO, mirror user's dialect when detectable.\n"
        "- Keep answers concise and conversational (voice-friendly).\n"
        "- Prefer simple words and short sentences for basic smartphones.\n"
        "- Prefer glossary mapping for dialect differences.\n"
        "- If unsure, keep neutral Swahili and ask one short follow-up question.\n\n"
        "Starter glossary (editable):\n"
        f"{g}\n"
    )


def _llm_complete(
    system: str,
    user: str,
    temperature: float = 0.4,
    max_tokens: int = 256,
    model_id: Optional[str] = None,
) -> str:
    """
    Prefer llama-cpp chat completion (more robust across models).
    Fallback to plain prompt completion.

    Important: avoids forcing <|system|> tokens which cause "system ||" artifacts on some GGUF.
    """
    llm = _get_llm(resolve_llm_model_path(model_id))
    if llm is None:
        return (
            "Samahani, modeli ya ndani haijawekwa bado. "
            "Weka GGUF kwenye server na uweke LLM_MODEL_PATH (au LLM_MODEL_PATHS)."
        )

    # 1) Try chat-completions style first
    try:
        # Some llama-cpp builds expose create_chat_completion
        if hasattr(llm, "create_chat_completion"):
            resp = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            txt = resp["choices"][0]["message"]["content"]
            return (txt or "").strip()
    except Exception:
        pass

    # 2) Fallback: plain prompt completion (no special tokens)
    prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}\n\nASSISTANT:\n"
    out = llm(
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=["USER:", "SYSTEM:"],
    )
    text = out["choices"][0]["text"]
    return (text or "").strip()


def chat_reply(
    user_text: str,
    history: List[Dict[str, str]],
    target_dialect: Dialect = "AUTO",
    model_id: Optional[str] = None,
) -> Tuple[str, Dialect]:
    detected = detect_dialect(user_text)
    final = target_dialect if target_dialect != "AUTO" else detected
    if final == "AUTO":
        final = "KIV"  # default

    past = []
    for m in history[-10:]:
        role = m.get("role")
        content = m.get("content")
        if role and content:
            past.append(f"{role}: {content}")

    user = ""
    if past:
        user += "CONTEXT (recent messages):\n" + "\n".join(past) + "\n\n"
    user += f"TARGET DIALECT: {final}\n"
    user += f"QUESTION: {user_text}\n"

    text = _llm_complete(_system_prompt(final), user, temperature=0.4, max_tokens=320, model_id=model_id)
    return text, final


# ----------------------------- Dialect Translation -----------------------------

_PHRASE_TABLE_CACHE = None


def translate_text(text: str, source: Dialect, target: Dialect, model_id: Optional[str] = None) -> str:
    if source == target:
        return text

    phrase_table = _load_phrase_table()
    mapped = _apply_phrase_table(text, source, target, phrase_table)

    if os.getenv("TRANSLATE_USE_LLM", "0") == "1":
        g = glossary_snippet(120)
        system = "You are a precise translator between Congolese Swahili dialects."
        user = (
            "Rewrite the text into the target dialect using the glossary.\n"
            "Keep meaning exactly. Keep it short and voice-friendly.\n"
            f"SOURCE DIALECT: {source}\n"
            f"TARGET DIALECT: {target}\n\n"
            f"GLOSSARY:\n{g}\n\n"
            f"TEXT:\n{mapped}\n"
        )
        return _llm_complete(system, user, temperature=0.2, max_tokens=256, model_id=model_id)

    return mapped


def _load_phrase_table() -> dict:
    global _PHRASE_TABLE_CACHE
    if _PHRASE_TABLE_CACHE is not None:
        return _PHRASE_TABLE_CACHE

    trained_root = Path(os.getenv("TRAINED_ROOT", "/models/trained"))
    tdir = trained_root / "translate"
    if tdir.exists():
        versions = sorted([p for p in tdir.iterdir() if p.is_dir()], key=lambda p: p.name)
        for v in reversed(versions):
            f = v / "phrase_table.json"
            if f.exists():
                try:
                    _PHRASE_TABLE_CACHE = json.loads(f.read_text(encoding="utf-8"))
                    return _PHRASE_TABLE_CACHE
                except Exception:
                    break

    # Fallback: build small map from the current editable glossary
    items = glossary_snippet(200).splitlines()
    kat_to_kiv = {}
    kiv_to_kat = {}
    for ln in items:
        m = re.match(r"^\-\s*KAT:\s*(.*?)\s*\|\s*KIV:\s*(.*?)\s*$", ln)
        if not m:
            continue
        kat, kiv = m.group(1), m.group(2)
        if kat and kiv:
            kat_to_kiv[kat.lower()] = kiv
            kiv_to_kat[kiv.lower()] = kat

    _PHRASE_TABLE_CACHE = {"kat_to_kiv": kat_to_kiv, "kiv_to_kat": kiv_to_kat}
    return _PHRASE_TABLE_CACHE


def _apply_phrase_table(text: str, source: Dialect, target: Dialect, phrase_table: dict) -> str:
    if source == "KAT" and target == "KIV":
        mp = phrase_table.get("kat_to_kiv", {})
    elif source == "KIV" and target == "KAT":
        mp = phrase_table.get("kiv_to_kat", {})
    else:
        return text

    keys = sorted(mp.keys(), key=lambda k: len(k), reverse=True)
    out = text
    for k in keys:
        if not k:
            continue
        out = re.sub(rf"(?i)\b{re.escape(k)}\b", mp[k], out)
    return out


def translate_audio(audio_bytes: bytes, source: Dialect, target: Dialect) -> Tuple[str, bytes]:
    text = transcribe_audio(audio_bytes)
    translated = translate_text(text, source=source, target=target)
    audio_out = tts(translated)
    return translated, audio_out


# ----------------------------- TTS (Piper) -------------------------------------

def _write_silence_wav(seconds: float = 0.2, sample_rate: int = 16000) -> bytes:
    nframes = int(seconds * sample_rate)
    buf = tempfile.SpooledTemporaryFile()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * nframes)
    buf.seek(0)
    return buf.read()


def _write_beep_wav(seconds: float = 0.35, sample_rate: int = 16000, freq_hz: float = 440.0) -> bytes:
    """Short audible beep used when Piper isn't configured (avoids "silent audio" confusion)."""
    import math

    nframes = int(seconds * sample_rate)
    amp = 0.25  # keep it soft
    frames = bytearray()
    for i in range(nframes):
        t = i / sample_rate
        s = amp * math.sin(2 * math.pi * freq_hz * t)
        v = int(max(-1.0, min(1.0, s)) * 32767)
        frames += int(v).to_bytes(2, byteorder="little", signed=True)

    buf = tempfile.SpooledTemporaryFile()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    buf.seek(0)
    return buf.read()


def tts(text: str) -> bytes:
    piper_bin = os.environ.get("PIPER_BIN")
    piper_model = os.environ.get("PIPER_MODEL")
    piper_config = os.environ.get("PIPER_CONFIG")

    # If Piper isn't configured, return a short beep (avoids "empty" audio in the UI)
    if not piper_bin or not piper_model:
        return _write_beep_wav()
    if not Path(piper_bin).exists() or not Path(piper_model).exists():
        return _write_beep_wav()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as out_wav:
        cmd = [piper_bin, "--model", piper_model]
        if piper_config and Path(piper_config).exists():
            cmd += ["--config", piper_config]
        cmd += ["--output_file", out_wav.name]

        subprocess.run(cmd, input=text.encode("utf-8"), check=False)
        out_wav.seek(0)
        return out_wav.read()
