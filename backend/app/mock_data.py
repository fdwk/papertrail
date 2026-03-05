"""
In-memory mock DB keyed by UUID, mirroring the schema in models.py.
Populated from the same content as frontend static-data (trails, papers, edges).
No DB connection required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

# Deterministic UUIDs so we can reference across modules
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "papertrail.mock")

def _id(s: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, s)


# ----- Users -----
MOCK_USERS: list[dict[str, Any]] = [
    {
        "id": _id("user-demo"),
        "email": "demo@papertrail.dev",
        "password_hash": "password123",  # plaintext for mock
    }
]


def get_user_by_email(email: str) -> dict | None:
    for u in MOCK_USERS:
        if u["email"] == email:
            return u
    return None
