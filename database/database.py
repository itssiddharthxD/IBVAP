"""Database engine and session management."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from core.config import get_config
from core.logging_config import get_logger
from .models import Base

logger = get_logger(__name__)

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        cfg = get_config()
        db_path = cfg.get("storage", "database_path", default="data/ibvap.db")
        url = f"sqlite:///{db_path}"
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")
