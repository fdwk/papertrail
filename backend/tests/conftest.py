from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure `import app...` works when running pytest from backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Prefer in-memory SQLite for tests so `pytest` does not require DATABASE_URL or Postgres.
# Set DATABASE_URL before any `app` import (integration / prod-like runs can export it first).
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture(scope="session", autouse=True)
def _ensure_schema() -> None:
    """
    Ensure ORM tables exist on the test engine.

    SQLite: full schema (typical when DATABASE_URL defaulted in this file).
    Postgres: only missing tables are created (e.g. password_reset_tokens if alembic not applied locally).
    """
    import app.models  # noqa: F401 — register models on Base.metadata

    from app.database import Base, engine

    Base.metadata.create_all(bind=engine)
