from __future__ import annotations

import re
from typing import Literal
import os
from pathlib import Path

_CLF = None


def _load_clf():
    """Load a trained dialect classifier if available."""
    global _CLF
    if _CLF is not None:
        return _CLF
    try:
        import joblib
    except Exception:
        return None

    trained_root = Path(os.getenv("TRAINED_ROOT", "/models/trained"))
    dialect_dir = trained_root / "dialect"
    if not dialect_dir.exists():
        return None
    versions = sorted([p for p in dialect_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
    for v in reversed(versions):
        f = v / "dialect_clf.joblib"
        if f.exists():
            _CLF = joblib.load(f)
            return _CLF
    return None

Dialect = Literal["KAT", "KIV", "AUTO"]

# Very simple heuristic starter. Replace with a real classifier later.
KIVU_HINTS = [
    r"\bhela\b",
    r"\bhivi\s+sasa\b",
    r"\bnjia\b",
    r"\bmugenzi\b",
]

KATANGA_HINTS = [
    r"\btelefon\b",
    r"\bnetwork\b",
    r"\bmgodini\b",
]


def detect_dialect(text: str) -> Dialect:
    # Prefer trained classifier if available
    clf = _load_clf()
    if clf is not None:
        try:
            pred = clf.predict([text])[0]
            if pred in {"KIV", "KAT"}:
                return pred  # type: ignore[return-value]
        except Exception:
            pass

    t = text.lower()
    score_kiv = sum(1 for p in KIVU_HINTS if re.search(p, t))
    score_kat = sum(1 for p in KATANGA_HINTS if re.search(p, t))
    if score_kiv > score_kat and score_kiv > 0:
        return "KIV"
    if score_kat > score_kiv and score_kat > 0:
        return "KAT"
    return "AUTO"
