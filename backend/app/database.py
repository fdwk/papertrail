from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

# Load .env from backend/ when DATABASE_URL not set (e.g. running hypercorn locally)
if not os.getenv("DATABASE_URL"):
    print("DATABASE_URL not set, loading .env from backend/")
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

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