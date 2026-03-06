"""Trails API: list (lightweight) and detail (with graph)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import require_user
from .database import get_db
from .repositories.trails import (
    create_trail_with_random_graph as create_trail_with_random_graph_db,
    get_trail_detail as get_trail_detail_db,
    list_trails_for_user as list_trails_for_user_db,
)
from .schemas import CreateTrailIn, TrailDetailOut, TrailSummaryOut

router = APIRouter(prefix="/trails", tags=["trails"])

@router.get("/", response_model=list[TrailSummaryOut])
def list_trails_from_db(
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TrailSummaryOut]:
    """List trails for the current user from the database (no mock data)."""
    return list_trails_for_user_db(db, user_id)


@router.post("/", response_model=TrailSummaryOut, status_code=status.HTTP_201_CREATED)
def create_trail(
    body: CreateTrailIn,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TrailSummaryOut:
    """Create a new trail for the user with a random graph of 3-4 papers from the DB."""
    return create_trail_with_random_graph_db(db, user_id, body.topic)


@router.get("/{trail_id}", response_model=TrailDetailOut)
def get_trail_detail_from_db(
    trail_id: str,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TrailDetailOut:
    """Fetch trail with full graph from DB (no mock data)."""
    try:
        tid = uuid.UUID(trail_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    result = get_trail_detail_db(db, tid, user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    return result
