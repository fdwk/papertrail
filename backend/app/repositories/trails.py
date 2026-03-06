"""Trail repository: DB queries for trails. Returns API-shaped data."""
from __future__ import annotations

import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Paper, PaperGraphEdge, Trail, UserPaper
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

    # Fetch papers and user_papers (skip query if no papers to avoid IN () issues)
    if not paper_ids:
        return TrailDetailOut(
            id=str(trail.id),
            topic=trail.topic,
            createdAt=trail.date_created.strftime("%Y-%m-%d"),
            nodes=[],
        )
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
        year = paper.date.year if paper.date else 0
        nodes.append(
            DAGNodeOut(
                id=str(paper_id),
                paper=PaperOut(
                    id=str(paper_id),
                    title=paper.title or "",
                    authors=authors,
                    year=year,
                    abstract=paper.abstract or "",
                    url=paper.url or "",
                    isRead=up.has_read if up else False,
                    note=up.note or "" if up else "",
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


def create_trail_with_random_graph(
    db: Session, user_id: uuid.UUID, topic: str
) -> TrailSummaryOut:
    """
    Create a new trail for the user and populate it with a random DAG of 3-4 papers
    from the papers table. Edges are created to form a simple random DAG.
    """
    trail = Trail(user_id=user_id, topic=topic)
    db.add(trail)
    db.flush()

    papers = (
        db.query(Paper)
        .order_by(func.random())
        .limit(4)
        .all()
    )
    if len(papers) < 2:
        return TrailSummaryOut(
            id=str(trail.id),
            topic=trail.topic,
            createdAt=trail.date_created.strftime("%Y-%m-%d"),
            readCount=0,
            totalCount=len(papers),
        )

    # Build a simple DAG: 0 -> 1, 0 -> 2, and if 4 papers: 1 -> 3, 2 -> 3
    edges_to_create = [(papers[0].id, papers[1].id)]
    if len(papers) >= 3:
        edges_to_create.append((papers[0].id, papers[2].id))
    if len(papers) >= 4:
        edges_to_create.append((papers[1].id, papers[3].id))
        edges_to_create.append((papers[2].id, papers[3].id))

    for paper_id, next_node_id in edges_to_create:
        edge = PaperGraphEdge(
            paper_id=paper_id,
            trail_id=trail.id,
            next_node_id=next_node_id,
        )
        db.add(edge)

    # Ensure UserPaper rows exist for every paper in the trail (defaults: not read, no note, not starred).
    # Skip pairs that already exist so we don't overwrite existing user state.
    paper_ids_in_trail = {p.id for p in papers}
    existing = {
        (up.user_id, up.paper_id)
        for up in db.query(UserPaper).filter(
            UserPaper.user_id == user_id,
            UserPaper.paper_id.in_(paper_ids_in_trail),
        ).all()
    }
    for pid in paper_ids_in_trail:
        if (user_id, pid) not in existing:
            db.add(
                UserPaper(
                    user_id=user_id,
                    paper_id=pid,
                    has_read=False,
                    note=None,
                    is_starred=False,
                )
            )

    db.commit()

    read_count = (
        db.query(UserPaper)
        .filter(
            UserPaper.user_id == user_id,
            UserPaper.paper_id.in_(paper_ids_in_trail),
            UserPaper.has_read.is_(True),
        )
        .count()
    )

    return TrailSummaryOut(
        id=str(trail.id),
        topic=trail.topic,
        createdAt=trail.date_created.strftime("%Y-%m-%d"),
        readCount=read_count,
        totalCount=len(papers),
    )


def delete_trail(db: Session, trail_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """
    Delete a trail. PaperGraphEdge rows for this trail are removed by cascade (Trail.edges).
    Returns True if the trail was found and deleted.
    """
    trail = (
        db.query(Trail)
        .filter(Trail.id == trail_id, Trail.user_id == user_id)
        .first()
    )
    if not trail:
        return False
    db.delete(trail)
    db.commit()
    return True
