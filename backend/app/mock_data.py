"""
In-memory mock DB keyed by UUID, mirroring the schema in models.py.
Populated from the same content as frontend static-data (trails, papers, edges).
No DB connection required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

# Deterministic UUIDs so we can reference across modules
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "papertrail.mock")

def _id(s: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, s)


# ----- Users -----
MOCK_USERS: list[dict[str, Any]] = [
    {
        "id": _id("user-demo"),
        "email": "demo@papertrail.dev",
        "password_hash": "password123",  # plaintext for mock
    }
]

# ----- Papers (key = frontend paper id string, e.g. p1, rl-p1) -----
def _paper(id_key: str, title: str, author: str, year: int, abstract: str, url: str) -> dict[str, Any]:
    return {
        "id": _id(id_key),
        "key": id_key,
        "title": title,
        "author": author,
        "abstract": abstract,
        "date": datetime(year, 1, 1, tzinfo=timezone.utc),
        "url": url,
    }

MOCK_PAPERS: list[dict[str, Any]] = [
    _paper("p1", "Attention Is All You Need", "Vaswani, A.; Shazeer, N.; Parmar, N.; Uszkoreit, J.", 2017,
           "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...", "https://arxiv.org/abs/1706.03762"),
    _paper("p2", "BERT: Pre-training of Deep Bidirectional Transformers", "Devlin, J.; Chang, M.; Lee, K.; Toutanova, K.", 2018,
           "We introduce a new language representation model called BERT...", "https://arxiv.org/abs/1810.04805"),
    _paper("p3", "GPT-2: Language Models are Unsupervised Multitask Learners", "Radford, A.; Wu, J.; Child, R.; Luan, D.", 2019,
           "Natural language processing tasks...", "https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf"),
    _paper("p4", "RoBERTa: A Robustly Optimized BERT Pretraining Approach", "Liu, Y.; Ott, M.; Goyal, N.; Du, J.", 2019,
           "Language model pretraining has led to significant performance gains...", "https://arxiv.org/abs/1907.11692"),
    _paper("p5", "GPT-3: Language Models are Few-Shot Learners", "Brown, T.; Mann, B.; Ryder, N.; Subbiah, M.", 2020,
           "Recent work has demonstrated substantial gains...", "https://arxiv.org/abs/2005.14165"),
    _paper("p6", "Vision Transformer (ViT): An Image is Worth 16x16 Words", "Dosovitskiy, A.; Beyer, L.; Kolesnikov, A.", 2020,
           "While the Transformer architecture has become the de-facto standard...", "https://arxiv.org/abs/2010.11929"),
    _paper("rl-p1", "Playing Atari with Deep asdfasdf Learning", "Mnih, V.; Kavukcuoglu, K.; Silver, D.", 2013,
           "We present the first deep learning model to successfully learn control policies...", "https://arxiv.org/abs/1312.5602"),
    _paper("rl-p2", "Human-level Control through Deep Reinforcement Learning", "Mnih, V.; Kavukcuoglu, K.; Silver, D.; Rusu, A.", 2015,
           "The theory of reinforcement learning provides a normative account...", "https://www.nature.com/articles/nature14236"),
    _paper("rl-p3", "Proximal Policy Optimization Algorithms", "Schulman, J.; Wolski, F.; Dhariwal, P.", 2017,
           "We propose a new family of policy gradient methods...", "https://arxiv.org/abs/1707.06347"),
    _paper("rl-p4", "Mastering the Game of Go with Deep Neural Networks and Tree Search", "Silver, D.; Huang, A.; Maddison, C.", 2016,
           "The game of Go has long been viewed as the most challenging...", "https://www.nature.com/articles/nature16961"),
    _paper("dm-p1", "Denoising Diffusion Probabilistic Models", "Ho, J.; Jain, A.; Abbeel, P.", 2020,
           "We present high quality image synthesis results using diffusion probabilistic models...", "https://arxiv.org/abs/2006.11239"),
    _paper("dm-p2", "High-Resolution Image Synthesis with Latent Diffusion Models", "Rombach, R.; Blattmann, A.; Lorenz, D.", 2022,
           "By decomposing the image formation process...", "https://arxiv.org/abs/2112.10752"),
    _paper("dm-p3", "Classifier-Free Diffusion Guidance", "Ho, J.; Salimans, T.", 2022,
           "Classifier guidance is a recently introduced method...", "https://arxiv.org/abs/2207.12598"),
]
PAPERS_BY_KEY: dict[str, dict] = {p["key"]: p for p in MOCK_PAPERS}

# ----- Trails (id = UUID, slug = stable id for URL) -----
MOCK_TRAILS: list[dict[str, Any]] = [
    {"id": _id("trail-1"), "slug": "trail-1", "user_id": _id("user-demo"), "name": "Transformer Architecture", "date_created": datetime(2024, 12, 1, tzinfo=timezone.utc)},
    {"id": _id("trail-2"), "slug": "trail-2", "user_id": _id("user-demo"), "name": "Reinforcement Learning", "date_created": datetime(2024, 11, 15, tzinfo=timezone.utc)},
    {"id": _id("trail-3"), "slug": "trail-3", "user_id": _id("user-demo"), "name": "Diffusion Models", "date_created": datetime(2025, 1, 5, tzinfo=timezone.utc)},
]

# ----- Edges: (paper_key, trail_key, next_paper_key). Frontend node id = node id (n1, n2, ...); paper for n1 is p1.
# So edge from n1 to n2 => (p1, trail-1, p2). We store by trail and build graph from this.
# Format: list of (trail_id_uuid, from_paper_key, to_paper_key). to_paper_key can be None for leaves.
MOCK_EDGES: list[tuple[uuid.UUID, str, str | None]] = [
    (_id("trail-1"), "p1", "p2"),   # n1 -> n2
    (_id("trail-1"), "p1", "p3"),   # n1 -> n3
    (_id("trail-1"), "p2", "p4"),   # n2 -> n4
    (_id("trail-1"), "p3", "p5"),   # n3 -> p5
    (_id("trail-1"), "p2", "p6"),   # n2 -> n6
    (_id("trail-1"), "p5", "p6"),   # n5 -> n6
    (_id("trail-2"), "rl-p1", "rl-p2"),
    (_id("trail-2"), "rl-p1", "rl-p3"),
    (_id("trail-2"), "rl-p2", "rl-p4"),
    (_id("trail-2"), "rl-p3", "rl-p4"),
    (_id("trail-3"), "dm-p1", "dm-p2"),
    (_id("trail-3"), "dm-p1", "dm-p3"),
]

# ----- UserPapers: user_id, paper_key, has_read, note, is_starred -----
def _up(uid: uuid.UUID, pk: str, read: bool, note: str = "", starred: bool = False) -> dict[str, Any]:
    return {"user_id": uid, "paper_key": pk, "has_read": read, "note": note, "is_starred": starred}

MOCK_USER_PAPERS: list[dict[str, Any]] = [
    _up(_id("user-demo"), "p1", True), _up(_id("user-demo"), "p2", True), _up(_id("user-demo"), "p3", False),
    _up(_id("user-demo"), "p4", False), _up(_id("user-demo"), "p5", False), _up(_id("user-demo"), "p6", False),
    _up(_id("user-demo"), "rl-p1", True), _up(_id("user-demo"), "rl-p2", True), _up(_id("user-demo"), "rl-p3", False), _up(_id("user-demo"), "rl-p4", False),
    _up(_id("user-demo"), "dm-p1", False), _up(_id("user-demo"), "dm-p2", False), _up(_id("user-demo"), "dm-p3", False),
]

def get_trails_for_user(user_id: uuid.UUID) -> list[dict]:
    return [t for t in MOCK_TRAILS if t["user_id"] == user_id]

def get_trail(trail_id: uuid.UUID) -> dict | None:
    for t in MOCK_TRAILS:
        if t["id"] == trail_id:
            return t
    return None

def get_user_by_email(email: str) -> dict | None:
    for u in MOCK_USERS:
        if u["email"] == email:
            return u
    return None

def _find_user_paper(user_id: uuid.UUID, paper_key: str) -> dict | None:
    for up in MOCK_USER_PAPERS:
        if up["user_id"] == user_id and up["paper_key"] == paper_key:
            return up
    return None

def get_has_read(user_id: uuid.UUID, paper_key: str) -> bool:
    up = _find_user_paper(user_id, paper_key)
    return up["has_read"] if up else False

def get_note(user_id: uuid.UUID, paper_key: str) -> str:
    up = _find_user_paper(user_id, paper_key)
    return up.get("note", "") if up else ""

def get_is_starred(user_id: uuid.UUID, paper_key: str) -> bool:
    up = _find_user_paper(user_id, paper_key)
    return up.get("is_starred", False) if up else False

def set_user_paper_state(
    user_id: uuid.UUID,
    paper_key: str,
    *,
    has_read: bool | None = None,
    note: str | None = None,
    is_starred: bool | None = None,
) -> None:
    up = _find_user_paper(user_id, paper_key)
    if up:
        if has_read is not None:
            up["has_read"] = has_read
        if note is not None:
            up["note"] = note
        if is_starred is not None:
            up["is_starred"] = is_starred
    else:
        MOCK_USER_PAPERS.append({
            "user_id": user_id,
            "paper_key": paper_key,
            "has_read": has_read if has_read is not None else False,
            "note": note if note is not None else "",
            "is_starred": is_starred if is_starred is not None else False,
        })

def get_edges_for_trail(trail_id: uuid.UUID) -> list[tuple[str, str]]:
    """Returns list of (from_paper_key, to_paper_key) for the trail."""
    return [(f, t) for tid, f, t in MOCK_EDGES if tid == trail_id and t is not None]


def build_trail_graph(trail_id: uuid.UUID, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """
    Build frontend-shaped nodes for a trail: each node has id (paper_key), paper {}, dependencies [].
    """
    edges = get_edges_for_trail(trail_id)
    all_keys: set[str] = set()
    deps_by_key: dict[str, list[str]] = {}
    for from_k, to_k in edges:
        all_keys.add(from_k)
        all_keys.add(to_k)
        deps_by_key.setdefault(to_k, []).append(from_k)
    for k in all_keys:
        deps_by_key.setdefault(k, [])

    nodes = []
    for paper_key in all_keys:
        paper = PAPERS_BY_KEY.get(paper_key)
        if not paper:
            continue
        authors = [a.strip() for a in paper["author"].split(";")] if paper.get("author") else []
        year = paper["date"].year if hasattr(paper["date"], "year") else datetime.now(timezone.utc).year
        is_read = get_has_read(user_id, paper_key)
        note = get_note(user_id, paper_key)
        is_starred = get_is_starred(user_id, paper_key)
        nodes.append({
            "id": paper_key,
            "paper": {
                "id": paper_key,
                "title": paper["title"],
                "authors": authors,
                "year": year,
                "abstract": paper.get("abstract") or "",
                "url": paper.get("url") or "",
                "isRead": is_read,
                "note": note,
                "isStarred": is_starred,
            },
            "dependencies": deps_by_key.get(paper_key, []),
        })
    return nodes
