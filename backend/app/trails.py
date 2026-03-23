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
    count_trails_for_user as count_trails_for_user_db,
    create_trail_with_random_graph as create_trail_with_random_graph_db,
    delete_trail as delete_trail_db,
    get_trail_detail as get_trail_detail_db,
    list_trails_for_user as list_trails_for_user_db,
)
from .schemas import (
    CreateTrailIn,
    TrailDetailOut,
    TrailExpansionConfirmIn,
    TrailExpansionIn,
    TrailExpansionProposalOut,
    TrailSummaryOut,
)
from .services.trail_generator import (
    TrailGenerationError,
    apply_expansion,
    generate_expansion,
    generate_trail,
    generate_trail_stream,
)

router = APIRouter(prefix="/trails", tags=["trails"])
logger = logging.getLogger(__name__)
FREE_TRAIL_LIMIT = 3


def _enforce_trail_limit_for_user(db: Session, user_id: uuid.UUID) -> None:
    """
    Free-tier users can have at most FREE_TRAIL_LIMIT trails.
    Enforce before expensive generation calls.
    """
    from .models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if (user.tier or "Reader") != "Reader":
        return
    if count_trails_for_user_db(db, user_id) >= FREE_TRAIL_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Free plan limit reached ({FREE_TRAIL_LIMIT} trails). Delete a trail or upgrade your plan.",
        )

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
    _enforce_trail_limit_for_user(db, user_id)
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
    _enforce_trail_limit_for_user(db, user_id)

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


@router.post(
    "/{trail_id}/expand",
    response_model=TrailExpansionProposalOut,
    status_code=status.HTTP_200_OK,
)
def propose_trail_expansion(
    trail_id: str,
    body: TrailExpansionIn,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TrailExpansionProposalOut:
    """Propose an ephemeral expansion from a given node in a trail.

    This does not modify the trail in the database; it simply returns a small
    set of related papers and edges for the frontend to stage visually.
    """
    try:
        tid = uuid.UUID(trail_id)
        source_node_uuid = uuid.UUID(body.sourceNodeId)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id format")

    try:
        return generate_expansion(db, user_id, tid, source_node_uuid)
    except TrailGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{trail_id}/expand/confirm",
    response_model=TrailDetailOut,
    status_code=status.HTTP_200_OK,
)
def confirm_trail_expansion(
    trail_id: str,
    body: TrailExpansionConfirmIn,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TrailDetailOut:
    """Persist an accepted expansion into the trail and return the updated graph."""
    try:
        tid = uuid.UUID(trail_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid trail id")

    try:
        detail = apply_expansion(db, user_id, tid, body)
    except TrailGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if detail is None:
        # Should not normally happen, but guard in case the repository returns None.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    return detail
