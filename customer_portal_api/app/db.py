from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
import os

from sqlalchemy.pool import QueuePool
from sqlmodel import Session, SQLModel, create_engine


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_database_url() -> str:
    database_path = Path(__file__).resolve().parent.parent / "customer_portal.db"
    return f"sqlite:///{database_path}"


DATABASE_URL = os.getenv("PORTAL_DATABASE_URL", _default_database_url())
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}),
)


def init_portal_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
