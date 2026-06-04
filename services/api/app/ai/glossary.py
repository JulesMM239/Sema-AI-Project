import csv
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path("./data")
GLOSSARY_PATH = DATA_DIR / "glossary_kat_kiv.csv"


def load_glossary() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if not GLOSSARY_PATH.exists():
        return items
    with GLOSSARY_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    return items


def glossary_snippet(max_items: int = 30) -> str:
    """Return a compact snippet to inject in prompts."""
    items = load_glossary()[:max_items]
    lines = []
    for it in items:
        kat = it.get("katanga", "")
        kiv = it.get("kivu", "")
        if kat and kiv:
            lines.append(f"- KAT: {kat} | KIV: {kiv}")
    return "\n".join(lines)
