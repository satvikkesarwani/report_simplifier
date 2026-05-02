from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

Base = declarative_base()
settings = get_settings()


def _connect_args(database_url: str) -> dict:
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


@lru_cache(maxsize=8)
def get_engine(database_url: Optional[str] = None):
    resolved_url = database_url or settings.DATABASE_URL
    return create_engine(
        resolved_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_connect_args(resolved_url),
    )


@lru_cache(maxsize=8)
def get_session_factory(database_url: Optional[str] = None):
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        autocommit=False,
        future=True,
    )


engine = get_engine()
SessionLocal = get_session_factory()


@contextmanager
def session_scope(database_url: Optional[str] = None) -> Iterator[Session]:
    session = get_session_factory(database_url)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
