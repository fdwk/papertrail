"""Trails API: list (lightweight) and detail (with graph)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_user
from .mock_data import (
    _id,
    build_trail_graph,
    get_edges_for_trail,
    get_has_read,
    get_trail,
    get_trails_for_user,
)
from .schemas import DAGNodeOut, PaperOut, TrailDetailOut, TrailSummaryOut

router = APIRouter(prefix="/trails", tags=["trails"])


def _parse_trail_id(trail_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(trail_id)
    except ValueError:
        return _id(trail_id)


@router.get("/", response_model=list[TrailSummaryOut])
def list_trails(
    user_id: Annotated[uuid.UUID, Depends(require_user)],
) -> list[TrailSummaryOut]:
    """Called after login: returns all trails for the user without nodes/edges."""
    trails = get_trails_for_user(user_id)
    result = []
    for t in trails:
        tid = t["id"]
        edges = get_edges_for_trail(tid)
        all_keys = set()
        for from_k, to_k in edges:
            all_keys.add(from_k)
            all_keys.add(to_k)
        total = len(all_keys)
        read_count = sum(1 for k in all_keys if get_has_read(user_id, k))
        result.append(
            TrailSummaryOut(
                id=t.get("slug") or str(t["id"]),
                topic=t.get("name") or "Untitled",
                createdAt=t["date_created"].strftime("%Y-%m-%d"),
                readCount=read_count,
                totalCount=total,
            )
        )
    return result


@router.get("/{trail_id}", response_model=TrailDetailOut)
def get_trail_detail(
    trail_id: str,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
) -> TrailDetailOut:
    """Fetched when a trail is selected: returns full trail with nodes (graph)."""
    tid = _parse_trail_id(trail_id)
    trail = get_trail(tid)
    if not trail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")
    if trail["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trail not found")

    nodes_data = build_trail_graph(tid, user_id)
    nodes = [DAGNodeOut(**n) for n in nodes_data]

    return TrailDetailOut(
        id=trail.get("slug") or str(trail["id"]),
        topic=trail.get("name") or "Untitled",
        createdAt=trail["date_created"].strftime("%Y-%m-%d"),
        nodes=nodes,
    )
