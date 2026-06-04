from __future__ import annotations
from pathlib import Path
import csv
import re
import json

def load_glossary(glossary_path: str | None) -> list[tuple[str, str]]:
    if not glossary_path:
        return []
    p = Path(glossary_path)
    if not p.exists():
        return []
    pairs = []
    with open(p, "r", encoding="utf-8") as f:
        # Accept either 2-column CSV (src,tgt) or header-based
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            a, b = row[0].strip(), row[1].strip()
            if not a or not b:
                continue
            pairs.append((a, b))
    # longest first to avoid partial replacements
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs

def glossary_translate(text: str, pairs: list[tuple[str, str]]) -> str:
    out = text
    for src, tgt in pairs:
        # word boundary-ish replacement, but also allow phrases
        pattern = re.compile(rf"(?i)\b{re.escape(src)}\b")
        out = pattern.sub(tgt, out)
    return out

def naive_translate(text: str, glossary_path: str | None) -> tuple[str, str]:
    pairs = load_glossary(glossary_path)
    if pairs:
        return glossary_translate(text, pairs), "glossary"
    return text, "echo"
