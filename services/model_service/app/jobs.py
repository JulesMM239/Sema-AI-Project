from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session

from app.training.pipeline import run_training
from app.models import TrainingRun, ModelVersion
from app.storage import model_root

def training_job(run_id: int, db_url: str):
    # Late imports so RQ worker can run cleanly
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db: Session = SessionLocal()
    try:
        run = db.get(TrainingRun, run_id)
        if not run:
            return

        run.status = "running"
        run.updated_at = datetime.utcnow()
        db.commit()

        # compute next version based on existing versions
        existing = db.query(ModelVersion).filter(ModelVersion.model_id == run.model_id).all()
        versions = [m.version for m in existing]
        # choose next
        from app.training.pipeline import next_version
        version = next_version(versions)

        out = run_training(run.model_id, run.dataset_revision_id, version)

        mv = ModelVersion(
            model_id=run.model_id,
            version=version,
            dataset_revision_id=run.dataset_revision_id,
            artifact_path=out["artifact_path"],
            meta_path=out["meta_path"],
            is_active=False,
        )
        db.add(mv)

        run.status = "success"
        run.produced_version = version
        run.updated_at = datetime.utcnow()
        run.logs = (run.logs or "") + f"\nProduced {version} at {out['artifact_path']}\n"
        db.commit()

    except Exception as e:
        run = db.get(TrainingRun, run_id)
        if run:
            run.status = "failed"
            run.error = str(e)
            run.updated_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
