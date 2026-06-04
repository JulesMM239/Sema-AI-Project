from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from worker.db import fetch_corpus_rows
from worker.job_utils import update_job


def run(job_id: int, model_version: str):
    """Train a light dialect classifier (KIV vs KAT).

    Training data sources:
    - corpus_items table (admin-added text)
    - built-in corpora in /app/data/corpus_* (if present)

    Output:
    - /models/trained/dialect/<version>/dialect_clf.joblib
    - ...
    """
    out_root = Path(os.getenv("TRAIN_OUTPUT_DIR", "/models/trained"))
    out_dir = out_root / "dialect" / model_version
    out_dir.mkdir(parents=True, exist_ok=True)

    update_job(job_id, "running", notes="Training dialect classifier (TF-IDF + LogisticRegression)")

    rows = fetch_corpus_rows()
    texts = []
    labels = []

    for r in rows:
        d = (r.get("dialect") or "").strip().upper()
        if d not in {"KIV", "KAT"}:
            continue
        t = (r.get("text") or "").strip()
        if len(t) < 2:
            continue
        texts.append(t)
        labels.append(d)

    # Fallback: read bundled text corpora if DB has too little data
    data_dir = Path("/app/data")
    for f, d in [(data_dir / "corpus_kivu_swahili_v1.txt", "KIV"), (data_dir / "corpus_katanga_swahili_v1.txt", "KAT")]:
        if f.exists():
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if len(line) > 5:
                    texts.append(line)
                    labels.append(d)

    if len(texts) < 200:
        update_job(job_id, "failed", notes=f"Not enough training text. Need ~200 lines min; got {len(texts)}")
        return

    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42, stratify=labels)

    clf = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000)),
            ("lr", LogisticRegression(max_iter=200, n_jobs=1)),
        ]
    )
    clf.fit(X_train, y_train)

    report = classification_report(y_test, clf.predict(X_test), output_dict=True)
    joblib.dump(clf, out_dir / "dialect_clf.joblib")
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    update_job(job_id, "done", notes=f"Dialect classifier trained. Samples={len(texts)}", model_version=model_version)
