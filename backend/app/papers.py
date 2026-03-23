"""Paper user-state: star and note (per user)."""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import require_user
from .database import get_db
from .models import Trail
from .repositories.papers import (
    list_user_papers_with_state,
    update_user_paper_state as update_user_paper_state_db,
)

router = APIRouter(prefix="/papers", tags=["papers"])


class PaperUserStateUpdate(BaseModel):
    isRead: bool | None = None
    isStarred: bool | None = None
    note: str | None = None


class UserPaperOut(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    url: str
    isRead: bool
    isStarred: bool
    note: str | None = None
    trailTopics: List[str] = []


# Declare before /{paper_id}/... so GET /papers/user is not captured as paper_id="user"
@router.get("/user", response_model=List[UserPaperOut])
def list_user_papers(
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserPaperOut]:
    """
    Return all papers for the authenticated user with their per-user state,
    aggregated from the database.
    """
    rows = list_user_papers_with_state(db, user_id)
    result: list[UserPaperOut] = []

    for up, paper, trails in rows:
        # Authors: current model has a single `author` string; wrap in list if present.
        authors: list[str] = []
        if paper.author:
            authors.append(paper.author)

        year = paper.date.year
        trail_topics = sorted({t.topic for t in trails if isinstance(t, Trail)})
        if not trail_topics:
            # Hide stale user-paper state rows that are no longer linked to any trail.
            continue

        result.append(
            UserPaperOut(
                id=str(paper.id),
                title=paper.title,
                authors=authors,
                year=year,
                abstract=paper.abstract or "",
                url=paper.url or "",
                isRead=up.has_read,
                isStarred=up.is_starred,
                note=up.note,
                trailTopics=trail_topics,
            )
        )

    return result


@router.patch("/{paper_id}/user-state")
def update_paper_user_state(
    paper_id: str,
    body: PaperUserStateUpdate,
    user_id: Annotated[uuid.UUID, Depends(require_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    # Try UUID first (DB-backed trails)
    try:
        pid = uuid.UUID(paper_id)
        if update_user_paper_state_db(
            db,
            user_id,
            pid,
            has_read=body.isRead,
            note=body.note,
            is_starred=body.isStarred,
        ):
            return {"ok": True}
    except ValueError:
        pass
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
