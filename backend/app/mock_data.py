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


"""
NOTE: User data has moved to the real database (models.User).
This module now only holds mock trails/papers/user_papers for
graph-related endpoints.
"""
