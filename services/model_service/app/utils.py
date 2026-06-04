from __future__ import annotations
from pathlib import Path
import hashlib

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_dir(path: Path) -> str:
    h = hashlib.sha256()
    files = sorted([p for p in path.rglob("*") if p.is_file()])
    for p in files:
        h.update(p.relative_to(path).as_posix().encode())
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()
