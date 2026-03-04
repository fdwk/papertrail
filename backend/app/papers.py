"""Paper user-state: star and note (per user)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .auth import require_user
from .mock_data import PAPERS_BY_KEY, set_user_paper_state

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
) -> dict:
    if paper_id not in PAPERS_BY_KEY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    set_user_paper_state(
        user_id,
        paper_id,
        has_read=body.isRead,
        note=body.note,
        is_starred=body.isStarred,
    )
    return {"ok": True}
