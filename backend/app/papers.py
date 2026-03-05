"""Paper user-state: star and note (per user)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import require_user
from .database import get_db
from .repositories.papers import update_user_paper_state as update_user_paper_state_db

router = APIRouter(prefix="/papers", tags=["papers"])


class PaperUserStateUpdate(BaseModel):
    isRead: bool | None = None
    isStarred: bool | None = None
    note: str | None = None


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
