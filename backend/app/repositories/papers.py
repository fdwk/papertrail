"""Paper repository: DB updates for user paper state."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Paper, UserPaper


def update_user_paper_state(
    db: Session,
    user_id: uuid.UUID,
    paper_id: uuid.UUID,
    *,
    has_read: bool | None = None,
    note: str | None = None,
    is_starred: bool | None = None,
) -> bool:
    """Update or create UserPaper. Returns False if paper not found."""
    if db.get(Paper, paper_id) is None:
        return False
    up = db.get(UserPaper, (user_id, paper_id))
    if up is None:
        up = UserPaper(
            user_id=user_id,
            paper_id=paper_id,
            has_read=False,
            note=None,
            is_starred=False,
        )
        db.add(up)
    if has_read is not None:
        up.has_read = has_read
        up.last_read = datetime.now(timezone.utc) if has_read else None
    if note is not None:
        up.note = note
    if is_starred is not None:
        up.is_starred = is_starred
    db.commit()
    return True
