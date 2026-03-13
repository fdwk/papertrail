from __future__ import annotations

import pytest

from app.services import openalex


def test_resolve_paper_url_priority_order() -> None:
    work = {
        "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
        "primary_location": {"landing_page_url": "https://publisher.org/paper"},
        "doi": "https://doi.org/10.1000/xyz",
        "id": "https://openalex.org/W123",
    }
    assert openalex.resolve_paper_url(work) == "https://example.org/paper.pdf"

    work["best_oa_location"] = {"pdf_url": None}
    assert openalex.resolve_paper_url(work) == "https://publisher.org/paper"

    work["primary_location"] = {"landing_page_url": None}
    assert openalex.resolve_paper_url(work) == "https://doi.org/10.1000/xyz"

    work["doi"] = None
    assert openalex.resolve_paper_url(work) == "https://openalex.org/W123"


def test_get_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    with pytest.raises(openalex.OpenAlexError, match="OPENALEX_API_KEY is not set"):
        openalex._get("/works", params={"search": "transformers"})


def test_search_by_title_returns_best_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(path: str, params: dict | None = None) -> dict:
        assert path == "/works"
        assert params is not None
        # We ask OpenAlex for a small page size; exact value is part of the contract.
        assert params["per_page"] == 5
        return {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "Some Different Paper",
                    "authorships": [{"author": {"display_name": "Jane Doe"}}],
                    "publication_year": 2019,
                    "cited_by_count": 10,
                },
                {
                    "id": "https://openalex.org/W2",
                    "display_name": "Attention Is All You Need",
                    "authorships": [{"author": {"display_name": "Ashish Vaswani"}}],
                    "publication_year": 2017,
                    "cited_by_count": 1000,
                    "referenced_works": ["https://openalex.org/W5"],
                },
            ]
        }

    monkeypatch.setattr(openalex, "_get", fake_get)
    candidate = openalex.search_by_title("Attention Is All You Need", "Vaswani")
    assert candidate is not None
    assert candidate["openalex_id"] == "W2"
    assert candidate["title"] == "Attention Is All You Need"
    assert candidate["referenced_works"] == ["W5"]


def test_search_by_title_returns_none_when_similarity_low(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(path: str, params: dict | None = None) -> dict:
        return {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "Random Biology Study",
                    "authorships": [],
                    "publication_year": 2020,
                    "cited_by_count": 1,
                }
            ]
        }

    monkeypatch.setattr(openalex, "_get", fake_get)
    assert openalex.search_by_title("Transformer Architecture") is None


def test_search_works_clamps_limit_and_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_get(path: str, params: dict | None = None) -> dict:
        captured["path"] = path
        captured["params"] = params
        return {
            "results": [
                {
                    "id": "https://openalex.org/W99",
                    "display_name": "A Survey of Transformers",
                    "authorships": [{"author": {"display_name": "A. Author"}}],
                    "publication_year": 2023,
                    "cited_by_count": 55,
                    "referenced_works": [],
                }
            ]
        }

    monkeypatch.setattr(openalex, "_get", fake_get)
    rows = openalex.search_works("transformer architecture", limit=99)
    assert captured["path"] == "/works"
    assert captured["params"]["per_page"] == 25
    assert rows[0]["openalex_id"] == "W99"
