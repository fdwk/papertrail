from __future__ import annotations

import uuid

import pytest

from app.schemas import TrailSummaryOut
from app.services import trail_generator
from app.services.openai_client import OpenAIClientError


def _candidate(openalex_id: str, year: int, refs: list[str] | None = None) -> dict:
    return {
        "openalex_id": openalex_id,
        "title": f"title-{openalex_id}",
        "authors": ["A"],
        "year": year,
        "abstract": "",
        "doi": None,
        "url": f"https://openalex.org/{openalex_id}",
        "citation_count": 10,
        "referenced_works": refs or [],
    }


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
    # Async OpenAlex helpers are used inside the pipeline; stub them here.
    async def fake_async_search_by_title(title: str, authors: str | None = None) -> dict:  # type: ignore[override]
        return c1

    async def fake_async_search_works(topic: str, limit: int = 10) -> list[dict]:  # type: ignore[override]
        return [c2, c3]

    monkeypatch.setattr(trail_generator, "async_search_by_title", fake_async_search_by_title)
    monkeypatch.setattr(trail_generator, "async_search_works", fake_async_search_works)
    monkeypatch.setattr(
        trail_generator,
        "select_and_order_papers",
        lambda topic, verified_papers, citation_edges, size="medium": {
            "selected_papers": ["W1", "W2", "W3"],
            "edges": [{"from": "W1", "to": "W2"}, {"from": "W2", "to": "W3"}],
        },
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
    out = trail_generator.generate_trail(db=object(), user_id=user_id, topic="transformers")
    assert out.topic == "transformers"
    assert len(captured["papers"]) == 3
    assert captured["edges"] == [{"from": "W1", "to": "W2"}, {"from": "W2", "to": "W3"}]


def test_generate_trail_falls_back_when_curation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(
        trail_generator,
        "select_and_order_papers",
        lambda topic, verified_papers, citation_edges, size="medium": (_ for _ in ()).throw(OpenAIClientError("boom")),
    )

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
    trail_generator.generate_trail(db=object(), user_id=uuid.uuid4(), topic="topic")
    # Chronological fallback should start from oldest year.
    assert [p["openalex_id"] for p in captured["papers"]] == ["W1", "W2", "W3"]
    assert captured["edges"] == [{"from": "W1", "to": "W2"}, {"from": "W2", "to": "W3"}]


def test_generate_trail_raises_when_candidates_too_few(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trail_generator, "suggest_papers", lambda topic, size="medium": [])

    async def fake_async_search_works(topic: str, limit: int = 10) -> list[dict]:  # type: ignore[override]
        return [_candidate("W1", 2019)]

    monkeypatch.setattr(trail_generator, "async_search_works", fake_async_search_works)

    with pytest.raises(trail_generator.TrailGenerationError, match="Not enough verified candidate papers"):
        trail_generator.generate_trail(db=object(), user_id=uuid.uuid4(), topic="topic")
