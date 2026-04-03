from __future__ import annotations

import asyncio
import uuid

import pytest

from app.schemas import TrailSummaryOut
from app.services import trail_generator


def _candidate(
    openalex_id: str,
    year: int,
    refs: list[str] | None = None,
    *,
    citation_count: int = 10,
    source: str | None = None,
) -> dict:
    c: dict = {
        "openalex_id": openalex_id,
        "title": f"title-{openalex_id}",
        "authors": ["A"],
        "year": year,
        "abstract": "",
        "doi": None,
        "url": f"https://openalex.org/{openalex_id}",
        "citation_count": citation_count,
        "referenced_works": refs or [],
    }
    if source:
        c["_source"] = source
    return c


def test_score_and_select_papers_reserves_slots_for_verified() -> None:
    """GPT-resolved papers should not lose all seats to higher-scoring supplement-only papers."""
    hub = _candidate("WH", 2016, refs=[], citation_count=50000)
    leaves = [
        _candidate(f"W{i}", 2018, refs=["WH"], citation_count=8000) for i in range(2, 8)
    ]
    verified = _candidate("WV", 2017, refs=[], citation_count=1, source="verified")
    candidates = [verified, hub, *leaves]
    id_to_candidate = {c["openalex_id"]: c for c in candidates}
    edges = trail_generator._build_citation_edges(candidates)
    selected = trail_generator._score_and_select_papers(
        candidates,
        edges,
        max_papers=4,
        id_to_candidate=id_to_candidate,
    )
    assert "WV" in selected


def test_transitive_reduce_edges_removes_redundant_shortcut() -> None:
    nodes = {"A", "B", "C"}
    edges = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "A", "to": "C"},
    ]
    out = trail_generator._transitive_reduce_edges(nodes, edges)
    assert {(e["from"], e["to"]) for e in out} == {("A", "B"), ("B", "C")}


def test_transitive_reduce_full_drops_shortcut_when_two_hop_path_exists() -> None:
    """Same as citation + spine triangle: keep only cover edges."""
    nodes = {"A", "B", "C"}
    merged = [
        {"from": "A", "to": "B"},
        {"from": "A", "to": "C"},
        {"from": "B", "to": "C"},
        {"from": "A", "to": "C"},
    ]
    out = trail_generator._dedupe_directed_edges(nodes, merged)
    out = trail_generator._transitive_reduce_edges(nodes, out)
    assert {(e["from"], e["to"]) for e in out} == {("A", "B"), ("B", "C")}


def test_topological_order_prioritizes_high_citation_verified_roots() -> None:
    nodes = {"Wv", "Ws"}
    id_to_candidate = {
        "Wv": {"year": 2017, "citation_count": 50000, "_source": "verified"},
        "Ws": {"year": 2020, "citation_count": 100, "_source": "supplement"},
    }
    ordered = trail_generator._topological_order_ids(nodes, [], id_to_candidate)
    assert ordered[0] == "Wv"


def test_learning_spine_does_not_serialise_fan_out_branches() -> None:
    """Same weakly connected component (via A): do not add B→C just for reading order."""
    nodes = {"A", "B", "C"}
    edges = [{"from": "A", "to": "B"}, {"from": "A", "to": "C"}]
    ordered = ["A", "B", "C"]
    out = trail_generator._add_learning_spine(nodes, edges, ordered)
    assert {(e["from"], e["to"]) for e in out} == {("A", "B"), ("A", "C")}


def test_learning_spine_bridges_weakly_disconnected_components() -> None:
    nodes = {"A", "B", "C"}
    edges = [{"from": "A", "to": "B"}]
    ordered = ["A", "B", "C"]
    out = trail_generator._add_learning_spine(nodes, edges, ordered)
    assert ("B", "C") in {(e["from"], e["to"]) for e in out}


def test_transitive_reduce_basis_preserves_branches_after_spine_chain() -> None:
    nodes = {"A", "B", "C"}
    basis = [
        {"from": "A", "to": "B"},
        {"from": "A", "to": "C"},
    ]
    merged = [*basis, {"from": "B", "to": "C"}]
    out = trail_generator._transitive_reduce_using_basis_paths(nodes, merged, basis)
    pairs = {(e["from"], e["to"]) for e in out}
    assert ("A", "C") in pairs
    assert ("A", "B") in pairs
    assert ("B", "C") in pairs


def test_transitive_reduce_basis_still_drops_redundant_edge_in_basis() -> None:
    nodes = {"A", "B", "C"}
    basis = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "A", "to": "C"},
    ]
    out = trail_generator._transitive_reduce_using_basis_paths(nodes, basis, basis)
    assert {(e["from"], e["to"]) for e in out} == {("A", "B"), ("B", "C")}


def test_build_citation_edges_reverses_reference_direction() -> None:
    # W2 references W1, so reading edge should be W1 -> W2.
    edges = trail_generator._build_citation_edges(
        [
            _candidate("W1", 2017),
            _candidate("W2", 2018, refs=["W1"]),
        ]
    )
    assert edges == [{"from": "W1", "to": "W2"}]


def test_generate_trail_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    c1 = _candidate("W1", 2017)
    c2 = _candidate("W2", 2018, refs=["W1"])
    c3 = _candidate("W3", 2019, refs=["W2"])

    monkeypatch.setattr(
        trail_generator,
        "suggest_papers",
        lambda topic, size="medium": [{"title": "p1", "authors": "a", "year": 2017}],
    )

    async def fake_async_search_by_title(title: str, authors: str | None = None) -> dict:  # type: ignore[override]
        return c1

    async def fake_async_search_works(topic: str, limit: int = 10) -> list[dict]:  # type: ignore[override]
        return [c2, c3]

    monkeypatch.setattr(trail_generator, "async_search_by_title", fake_async_search_by_title)
    monkeypatch.setattr(trail_generator, "async_search_works", fake_async_search_works)
    monkeypatch.setattr(
        trail_generator,
        "enrich_edges_with_gpt",
        lambda topic, papers, edges: [],
    )

    captured: dict = {}

    def fake_create(db, user_id, topic, papers_data, edges_data):  # noqa: ANN001, ANN202
        captured["topic"] = topic
        captured["papers"] = papers_data
        captured["edges"] = edges_data
        return TrailSummaryOut(
            id=str(uuid.uuid4()),
            topic=topic,
            createdAt="2026-03-12",
            readCount=0,
            totalCount=len(papers_data),
        )

    monkeypatch.setattr(trail_generator, "create_trail_from_generated_data", fake_create)
    out = asyncio.run(
        trail_generator.generate_trail_async(db=object(), user_id=user_id, topic="transformers")
    )
    assert out.topic == "transformers"
    assert len(captured["papers"]) == 3
    ids = [p["openalex_id"] for p in captured["papers"]]
    assert set(ids) == {"W1", "W2", "W3"}
    assert len(captured["edges"]) >= 2


def test_generate_trail_falls_back_when_curation_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = [_candidate("W2", 2019), _candidate("W1", 2017), _candidate("W3", 2020)]
    monkeypatch.setattr(
        trail_generator,
        "suggest_papers",
        lambda topic, size="medium": [{"title": "x", "authors": "", "year": 0}],
    )

    async def fake_async_search_by_title(title: str, authors: str | None = None) -> dict:  # type: ignore[override]
        return candidates[0]

    async def fake_async_search_works(topic: str, limit: int = 10) -> list[dict]:  # type: ignore[override]
        return candidates[1:]

    monkeypatch.setattr(trail_generator, "async_search_by_title", fake_async_search_by_title)
    monkeypatch.setattr(trail_generator, "async_search_works", fake_async_search_works)
    monkeypatch.setattr(trail_generator, "_curate_trail_dag", lambda *a, **k: ([], []))

    captured: dict = {}

    def fake_create(db, user_id, topic, papers_data, edges_data):  # noqa: ANN001, ANN202
        captured["papers"] = papers_data
        captured["edges"] = edges_data
        return TrailSummaryOut(
            id=str(uuid.uuid4()),
            topic=topic,
            createdAt="2026-03-12",
            readCount=0,
            totalCount=len(papers_data),
        )

    monkeypatch.setattr(trail_generator, "create_trail_from_generated_data", fake_create)
    asyncio.run(trail_generator.generate_trail_async(db=object(), user_id=uuid.uuid4(), topic="topic"))
    # Fallback prefers GPT-verified papers first, then year.
    assert [p["openalex_id"] for p in captured["papers"]] == ["W2", "W1", "W3"]
    assert captured["edges"] == [{"from": "W2", "to": "W1"}, {"from": "W1", "to": "W3"}]


def test_generate_trail_raises_when_candidates_too_few(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trail_generator, "suggest_papers", lambda topic, size="medium": [])

    async def fake_async_search_works(topic: str, limit: int = 10) -> list[dict]:  # type: ignore[override]
        return [_candidate("W1", 2019)]

    monkeypatch.setattr(trail_generator, "async_search_works", fake_async_search_works)

    with pytest.raises(trail_generator.TrailGenerationError, match="Not enough verified candidate papers"):
        asyncio.run(trail_generator.generate_trail_async(db=object(), user_id=uuid.uuid4(), topic="topic"))


def _id_to_cand(*pairs: tuple[str, int]) -> dict:
    return {
        oid: {"year": y, "citation_count": 100 - i * 10, "_source": "supplement"}
        for i, (oid, y) in enumerate(pairs)
    }


def test_enforce_max_fan_out_keeps_all_protected() -> None:
    node_ids = {"H", "a", "b", "c", "d"}
    id_to_candidate = _id_to_cand(("H", 2010), ("a", 2011), ("b", 2012), ("c", 2013), ("d", 2014))
    edges = [{"from": "H", "to": x} for x in ("a", "b", "c", "d")]
    protected = {("H", "a"), ("H", "b"), ("H", "c"), ("H", "d")}
    out = trail_generator._enforce_max_fan_out(
        node_ids,
        edges,
        id_to_candidate,
        max_out=3,
        protected_pairs=protected,
    )
    assert len(out) == 4
    assert {(e["from"], e["to"]) for e in out} == protected


def test_finalize_dag_yields_single_root_and_spine() -> None:
    """No citation edges: repair roots + learning spine produce one entry and a connected path."""
    selected = ["W1", "W2", "W3", "W4"]
    id_to_candidate = _id_to_cand(("W1", 2017), ("W2", 2018), ("W3", 2019), ("W4", 2020))
    ordered, merged = trail_generator._finalize_dag(selected, [], set(), [], id_to_candidate)
    assert set(ordered) == set(selected)
    indeg = {n: 0 for n in selected}
    for e in merged:
        indeg[e["to"]] += 1
    roots = [n for n in selected if indeg[n] == 0]
    assert len(roots) == 1
    # Spine: consecutive papers in topo order should be linked (path or direct spine edge)
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        assert trail_generator._path_exists_in_edges(merged, set(selected), a, b)
