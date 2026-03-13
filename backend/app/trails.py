"""Trails API: list (lightweight) and detail (with graph)."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from .auth import require_user
from .database import get_db
from .repositories.trails import (
    create_trail_with_random_graph as create_trail_with_random_graph_db,
    delete_trail as delete_trail_db,
    get_trail_detail as get_trail_detail_db,
    list_trails_for_user as list_trails_for_user_db,
)
from .schemas import CreateTrailIn, TrailDetailOut, TrailSummaryOut
from .services.trail_generator import (
    TrailGenerationError,
    generate_trail,
    generate_trail_stream,
)

router = APIRouter(prefix="/trails", tags=["trails"])
logger = logging.getLogger(__name__)

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
    """Create a new trail via OpenAlex + GPT generation; fallback to random DB graph."""
    try:
        return generate_trail(db, user_id, body.topic, body.size)
    except TrailGenerationError as exc:
        logger.warning("Trail generation failed, using random fallback: %s", exc)
        return create_trail_with_random_graph_db(db, user_id, body.topic)


@router.post("/stream")
async def create_trail_stream(
    body: CreateTrailIn,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Stream trail generation progress via SSE."""

    async def event_generator():
        async for event in generate_trail_stream(db, user_id, body.topic, body.size):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.delete("/{trail_id}")
def delete_trail(
    trail_id: str,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Delete trail and its paper_graph_edges (cascade)."""
    try:
        tid = uuid.UUID(trail_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    if not delete_trail_db(db, tid, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
