from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.models import Paper, Trail, UserPaper, PaperGraphEdge
from app.schemas import TrailDetailOut
from app.services import trail_generator


class DummyQuery:
    def __init__(self, model: type, store: dict[type, Any]) -> None:
        self._model = model
        self._store = store

    def filter(self, *args: Any, **kwargs: Any) -> "DummyQuery":  # noqa: ANN401
        # Filtering is not simulated in detail; we just return the same query object.
        return self

    def first(self) -> Any:  # noqa: ANN401
        value = self._store.get(self._model)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def all(self) -> list[Any]:  # noqa: ANN401
        value = self._store.get(self._model)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class DummySession:
    def __init__(self, store: dict[type, Any]) -> None:
        self._store = store
        self.added: list[Any] = []
        self.committed = False

    def query(self, model: type) -> DummyQuery:
        return DummyQuery(model, self._store)

    def add(self, obj: Any) -> None:  # noqa: ANN401
        self.added.append(obj)

    def flush(self) -> None:
        # No-op for tests; SQLAlchemy would assign primary keys here.
        return None

    def commit(self) -> None:
        self.committed = True


def _openalex_candidate(work_id: str, year: int) -> dict[str, Any]:
    return {
        "openalex_id": work_id,
        "title": f"Title {work_id}",
        "authors": ["Author A"],
        "year": year,
        "abstract": "abstract",
        "doi": None,
        "url": f"https://openalex.org/{work_id}",
        "citation_count": 10,
        "referenced_works": [],
    }


def test_generate_expansion_returns_ephemeral_nodes_and_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    trail_id = uuid.uuid4()
    source_id = uuid.uuid4()

    trail = Trail(id=trail_id, user_id=user_id, topic="Transformers")  # type: ignore[arg-type]
    source_paper = Paper(id=source_id, title="Attention Is All You Need")  # type: ignore[arg-type]

    store: dict[type, Any] = {
        Trail: trail,
        Paper: source_paper,
    }
    db = DummySession(store)

    candidates = [
        _openalex_candidate("W1", 2017),
        _openalex_candidate("W2", 2019),
        _openalex_candidate("W3", 2020),
    ]

    def fake_search_works(query: str, limit: int = 10) -> list[dict[str, Any]]:
        assert "Transformers" in query
        assert "Attention Is All You Need" in query
        assert limit == 6
        return candidates

    monkeypatch.setattr(trail_generator.openalex, "search_works", fake_search_works)

    proposal = trail_generator.generate_expansion(
        db=db,
        user_id=user_id,
        trail_id=trail_id,
        source_node_id=source_id,
    )

    # We should get up to 4 nodes; our fake returns 3.
    assert len(proposal.nodes) == 3
    # Each node should depend on the source node.
    for node in proposal.nodes:
        assert node.dependencies == [str(source_id)]
        assert node.paper.isRead is False
        assert node.paper.isStarred is False
    # Edges should all originate from the source into the candidate ids.
    assert {edge.source for edge in proposal.edges} == {str(source_id)}
    assert {edge.target for edge in proposal.edges} == {"W1", "W2", "W3"}
    # No database writes are performed by generate_expansion.
    assert db.added == []
    assert db.committed is False


def test_generate_expansion_raises_when_trail_missing() -> None:
    user_id = uuid.uuid4()
    trail_id = uuid.uuid4()
    source_id = uuid.uuid4()
    # Empty store: no Trail / Paper rows.
    db = DummySession(store={})

    with pytest.raises(trail_generator.TrailGenerationError, match="Trail not found"):
        trail_generator.generate_expansion(
            db=db,
            user_id=user_id,
            trail_id=trail_id,
            source_node_id=source_id,
        )


def test_apply_expansion_creates_papers_edges_and_returns_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    trail_id = uuid.uuid4()
    source_id = uuid.uuid4()

    trail = Trail(id=trail_id, user_id=user_id, topic="Transformers")  # type: ignore[arg-type]
    source_paper = Paper(id=source_id, title="Attention Is All You Need")  # type: ignore[arg-type]

    store: dict[type, Any] = {
        Trail: trail,
        Paper: source_paper,
        UserPaper: [],
    }
    db = DummySession(store)

    # Expansion candidates from OpenAlex.
    candidates = [
        {
            **_openalex_candidate("W1", 2017),
            "abstract": "First",
        },
        {
            **_openalex_candidate("W2", 2019),
            "abstract": "Second",
        },
    ]

    def fake_search_works(query: str, limit: int = 10) -> list[dict[str, Any]]:
        return candidates

    monkeypatch.setattr(trail_generator.openalex, "search_works", fake_search_works)

    # Stub get_trail_detail so we can assert it was called and control the return value.
    expected_detail = TrailDetailOut(
        id=str(trail_id),
        topic="Transformers",
        createdAt="2026-03-13",
        nodes=[],
    )
    captured_get_detail: dict[str, Any] = {}

    def fake_get_trail_detail(db_arg, trail_uuid, user_uuid):  # noqa: ANN001, ANN202
        captured_get_detail["db"] = db_arg
        captured_get_detail["trail_id"] = trail_uuid
        captured_get_detail["user_id"] = user_uuid
        return expected_detail

    monkeypatch.setattr(trail_generator, "get_trail_detail", fake_get_trail_detail)

    payload = trail_generator.TrailExpansionConfirmIn(  # type: ignore[attr-defined]
        sourceNodeId=str(source_id),
        acceptedNodeIds=["W1", "W2"],
    )

    detail = trail_generator.apply_expansion(
        db=db,
        user_id=user_id,
        trail_id=trail_id,
        payload=payload,
    )

    # We should get back the stubbed TrailDetailOut.
    assert detail is expected_detail
    assert captured_get_detail["trail_id"] == trail_id
    assert captured_get_detail["user_id"] == user_id

    # Two PaperGraphEdge objects and two UserPaper links should be queued.
    added_edges = [obj for obj in db.added if isinstance(obj, PaperGraphEdge)]
    added_user_papers = [obj for obj in db.added if isinstance(obj, UserPaper)]

    assert len(added_edges) == 2
    assert len(added_user_papers) == 2

    # All edges should be from the source node into the new papers.
    assert {edge.paper_id for edge in added_edges} == {source_id}
    assert db.committed is True

