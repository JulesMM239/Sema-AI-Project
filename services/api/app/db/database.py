from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.settings import settings


def _sqlite_connect_args(url: str):
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


engine = create_engine(settings.app_db_url, connect_args=_sqlite_connect_args(settings.app_db_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
