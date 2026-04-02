from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

# Default to in-memory SQLite so local tools and pytest can run without Postgres.
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite+pysqlite:///:memory:"

_engine_kwargs: dict = {"echo": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@compiles(PG_UUID, "sqlite")
def _compile_pg_uuid_for_sqlite(_type, compiler, **kw):
    return "CHAR(36)"


SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass