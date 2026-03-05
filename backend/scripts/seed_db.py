"""
Seed the database with data from seed_data.json.

Data is synced from frontend/web-app-main/lib/static-data.ts — when you update
that file, re-export to this JSON (or copy the structure) and re-run the seed.

Usage (from repo root, with DATABASE_URL set for local Postgres):
  cd backend && python -m scripts.seed_db

Or with env:
  cd backend && set DATABASE_URL=postgresql://postgres:postgres@localhost:5433/mydb && python -m scripts.seed_db
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Run from backend directory so app is importable
if __name__ == "__main__":
    import sys
    backend = Path(__file__).resolve().parent.parent
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

from app.database import SessionLocal
from app.mock_data import _id as mock_id
from app.models import User, Trail, Paper, UserPaper, PaperGraphEdge

SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "papertrail-seed")


def stable_uuid(s: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, s)


def load_seed_data() -> list[dict]:
    path = Path(__file__).resolve().parent / "seed_data.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed(session=None):
    data = load_seed_data()

    # Demo user: matches mock_data so login (demo@papertrail.dev / password123) works.
    demo_user_id = mock_id("user-demo")
    user = session.get(User, demo_user_id)
    if not user:
        user = User(
            id=demo_user_id,
            email="demo@papertrail.dev",
            password_hash="password123",  # plaintext; mock auth compares directly
            date_created=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()

    # Collect all papers and node_id -> paper_id mapping
    paper_id_to_uuid: dict[str, uuid.UUID] = {}
    node_id_to_paper_uuid: dict[str, uuid.UUID] = {}
    papers_to_create: list[tuple[str, dict]] = []  # (paper_id, paper_data)

    for trail_data in data:
        for node in trail_data["nodes"]:
            pid = node["paper"]["id"]
            if pid not in paper_id_to_uuid:
                paper_id_to_uuid[pid] = stable_uuid(pid)
                papers_to_create.append((pid, node["paper"]))
            node_id_to_paper_uuid[node["id"]] = paper_id_to_uuid[pid]

    # Create papers and user_papers
    for paper_id, p in papers_to_create:
        pid_uuid = paper_id_to_uuid[paper_id]
        existing = session.get(Paper, pid_uuid)
        pub_date = datetime(p["year"], 1, 1, tzinfo=timezone.utc)
        author = ", ".join(p["authors"]) if p.get("authors") else None
        if existing is None:
            paper = Paper(
                id=pid_uuid,
                title=p["title"],
                author=author,
                abstract=p.get("abstract") or None,
                doi=None,
                date=pub_date,
                url=p.get("url"),
            )
            session.add(paper)
            session.flush()
            up = UserPaper(
                user_id=user.id,
                paper_id=pid_uuid,
                has_read=p.get("isRead", False),
                note=p.get("note") or None,
                is_starred=p.get("isStarred", False),
                last_read=datetime.now(timezone.utc) if p.get("isRead") else None,
            )
            session.add(up)

    session.flush()

    # Create trails and edges
    for trail_data in data:
        trail_uuid = stable_uuid(trail_data["id"])
        if session.get(Trail, trail_uuid) is not None:
            continue
        created = datetime.fromisoformat(trail_data["createdAt"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        trail = Trail(
            id=trail_uuid,
            user_id=user.id,
            topic=trail_data["topic"],
            date_created=created,
        )
        session.add(trail)
        session.flush()

        for node in trail_data["nodes"]:
            node_paper_uuid = node_id_to_paper_uuid[node["id"]]
            for dep_node_id in node.get("dependencies", []):
                dep_paper_uuid = node_id_to_paper_uuid[dep_node_id]
                edge = PaperGraphEdge(
                    paper_id=dep_paper_uuid,
                    trail_id=trail.id,
                    next_node_id=node_paper_uuid,
                )
                session.add(edge)

    session.commit()
    print(
        "Seed completed: 1 user (demo@papertrail.dev / password123),",
        len(paper_id_to_uuid),
        "papers,",
        len(data),
        "trails.",
    )


def main():
    if not os.getenv("DATABASE_URL"):
        print("Set DATABASE_URL (e.g. postgresql://postgres:postgres@localhost:5433/mydb)")
        raise SystemExit(1)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
