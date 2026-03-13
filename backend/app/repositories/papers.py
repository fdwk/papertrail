"""Paper repository: DB updates for user paper state."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Paper, PaperGraphEdge, Trail, UserPaper


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


def list_user_papers_with_state(
    db: Session,
    user_id: uuid.UUID,
) -> list[tuple[UserPaper, Paper, list[Trail]]]:
    """
    Return all UserPaper rows for a user with their Paper and associated Trails.
    """
    # Base query: user-specific paper state joined to paper metadata
    base = (
        db.query(UserPaper, Paper)
        .join(Paper, UserPaper.paper_id == Paper.id)
        .filter(UserPaper.user_id == user_id)
    )

    rows = base.all()
    if not rows:
        return []

    # Collect paper ids to look up trail context
    paper_ids = [paper.id for _, paper in rows]

    trail_rows = (
        db.query(PaperGraphEdge.paper_id, Trail)
        .join(Trail, PaperGraphEdge.trail_id == Trail.id)
        .filter(PaperGraphEdge.paper_id.in_(paper_ids))
        .all()
    )

    trails_by_paper: dict[uuid.UUID, list[Trail]] = {}
    for pid, trail in trail_rows:
        trails_by_paper.setdefault(pid, []).append(trail)

    result: list[tuple[UserPaper, Paper, list[Trail]]] = []
    for up, paper in rows:
        result.append((up, paper, trails_by_paper.get(paper.id, [])))

    return result
