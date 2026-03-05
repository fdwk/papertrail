"""Trail repository: DB queries for trails. Returns API-shaped data."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, joinedload

from app.models import Paper, Trail, UserPaper
from app.schemas import DAGNodeOut, PaperOut, TrailDetailOut, TrailSummaryOut


def list_trails_for_user(db: Session, user_id: uuid.UUID) -> list[TrailSummaryOut]:
    """List trails for a user with read/total counts. Reads from DB."""
    trails = (
        db.query(Trail)
        .options(joinedload(Trail.edges))
        .filter(Trail.user_id == user_id)
        .order_by(Trail.date_created)
        .all()
    )
    result = []
    for trail in trails:
        paper_ids = set()
        for edge in trail.edges:
            paper_ids.add(edge.paper_id)
            if edge.next_node_id is not None:
                paper_ids.add(edge.next_node_id)
        total_count = len(paper_ids)
        if paper_ids:
            read_count = (
                db.query(UserPaper)
                .filter(
                    UserPaper.user_id == user_id,
                    UserPaper.paper_id.in_(paper_ids),
                    UserPaper.has_read.is_(True),
                )
                .count()
            )
        else:
            read_count = 0
        result.append(
            TrailSummaryOut(
                id=str(trail.id),
                topic=trail.topic,
                createdAt=trail.date_created.strftime("%Y-%m-%d"),
                readCount=read_count,
                totalCount=total_count,
            )
        )
    return result


def get_trail_detail(db: Session, trail_id: uuid.UUID, user_id: uuid.UUID) -> TrailDetailOut | None:
    """Fetch trail by id with full graph. Returns None if not found or not owned by user."""
    trail = (
        db.query(Trail)
        .options(joinedload(Trail.edges))
        .filter(Trail.id == trail_id, Trail.user_id == user_id)
        .first()
    )
    if not trail:
        return None

    # Build deps: for edge (paper_id -> next_node_id), next_node depends on paper
    deps_by_paper: dict[uuid.UUID, list[str]] = {}
    paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            paper_ids.add(edge.next_node_id)
            deps_by_paper.setdefault(edge.next_node_id, []).append(str(edge.paper_id))
    for pid in paper_ids:
        deps_by_paper.setdefault(pid, [])

    # Fetch papers and user_papers
    papers = {p.id: p for p in db.query(Paper).filter(Paper.id.in_(paper_ids)).all()}
    user_papers = {
        (up.user_id, up.paper_id): up
        for up in db.query(UserPaper).filter(
            UserPaper.user_id == user_id,
            UserPaper.paper_id.in_(paper_ids),
        ).all()
    }

    nodes = []
    for paper_id in paper_ids:
        paper = papers.get(paper_id)
        if not paper:
            continue
        up = user_papers.get((user_id, paper_id))
        authors = [a.strip() for a in (paper.author or "").split(",") if a.strip()]
        nodes.append(
            DAGNodeOut(
                id=str(paper_id),
                paper=PaperOut(
                    id=str(paper_id),
                    title=paper.title,
                    authors=authors,
                    year=paper.date.year,
                    abstract=paper.abstract or "",
                    url=paper.url or "",
                    isRead=up.has_read if up else False,
                    note=up.note or "",
                    isStarred=up.is_starred if up else False,
                ),
                dependencies=deps_by_paper.get(paper_id, []),
            )
        )

    return TrailDetailOut(
        id=str(trail.id),
        topic=trail.topic,
        createdAt=trail.date_created.strftime("%Y-%m-%d"),
        nodes=nodes,
    )
