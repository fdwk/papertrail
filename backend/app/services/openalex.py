from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Any

import httpx


OPENALEX_BASE_URL = "https://api.openalex.org"
DEFAULT_TIMEOUT_SECONDS = 15.0


class OpenAlexError(RuntimeError):
    """Raised when OpenAlex API calls fail."""


def _normalize_openalex_id(work_id: str | None) -> str:
    if not work_id:
        return ""
    if work_id.startswith("https://openalex.org/"):
        return work_id.rsplit("/", 1)[-1]
    return work_id


def _extract_authors(work: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = (author.get("display_name") or "").strip()
        if name:
            names.append(name)
    return names


def _extract_abstract(work: dict[str, Any]) -> str:
    inverted = work.get("abstract_inverted_index") or {}
    if not inverted:
        return ""
    max_pos = -1
    for positions in inverted.values():
        for pos in positions:
            if pos > max_pos:
                max_pos = pos
    if max_pos < 0:
        return ""
    words = [""] * (max_pos + 1)
    for token, positions in inverted.items():
        for pos in positions:
            if 0 <= pos < len(words):
                words[pos] = token
    return " ".join(w for w in words if w).strip()


def resolve_paper_url(work: dict[str, Any]) -> str:
    best_oa = (work.get("best_oa_location") or {}).get("pdf_url")
    if best_oa:
        return best_oa

    landing = (work.get("primary_location") or {}).get("landing_page_url")
    if landing:
        return landing

    doi = work.get("doi")
    if doi:
        return doi

    work_id = work.get("id")
    if work_id:
        return work_id
    return ""


def _client() -> httpx.Client:
    return httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = dict(params or {})
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        raise OpenAlexError("OPENALEX_API_KEY is not set.")
    query["api_key"] = api_key
    try:
        with _client() as client:
            response = client.get(f"{OPENALEX_BASE_URL}{path}", params=query)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc
    return response.json()


async def _async_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Async variant of _get so multiple OpenAlex calls can be awaited concurrently."""
    query = dict(params or {})
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        raise OpenAlexError("OPENALEX_API_KEY is not set.")
    query["api_key"] = api_key
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{OPENALEX_BASE_URL}{path}", params=query)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc
    return response.json()


def _work_to_candidate(work: dict[str, Any]) -> dict[str, Any]:
    return {
        "openalex_id": _normalize_openalex_id(work.get("id")),
        "title": (work.get("display_name") or "").strip(),
        "authors": _extract_authors(work),
        "year": int(work.get("publication_year") or 0),
        "abstract": _extract_abstract(work),
        "doi": (work.get("doi") or "").strip() or None,
        "url": resolve_paper_url(work),
        "citation_count": int(work.get("cited_by_count") or 0),
        "referenced_works": [
            _normalize_openalex_id(x)
            for x in (work.get("referenced_works") or [])
            if _normalize_openalex_id(x)
        ],
    }


def search_by_title(title: str, authors_hint: str | None = None) -> dict[str, Any] | None:
    query = title.strip()
    if not query:
        return None

    data = _get(
        "/works",
        params={
            "search": query,
            "per_page": 5,
        },
    )
    results = data.get("results") or []
    if not results:
        return None

    best_work: dict[str, Any] | None = None
    best_score = 0.0
    query_norm = query.lower()
    author_norm = (authors_hint or "").lower()

    for work in results:
        candidate_title = (work.get("display_name") or "").lower()
        title_score = SequenceMatcher(None, query_norm, candidate_title).ratio()
        bonus = 0.0
        if author_norm:
            candidate_authors = " ".join(_extract_authors(work)).lower()
            if author_norm and author_norm in candidate_authors:
                bonus = 0.1
        score = title_score + bonus
        if score > best_score:
            best_score = score
            best_work = work

    if best_work is None or best_score < 0.6:
        return None
    return _work_to_candidate(best_work)


def search_works(query: str, limit: int = 10) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    data = _get(
        "/works",
        params={
            "search.semantic": query,
            "sort": "cited_by_count:desc",
            "per_page": max(1, min(limit, 25)),
        },
    )
    return [_work_to_candidate(work) for work in (data.get("results") or [])]


async def async_search_by_title(title: str, authors_hint: str | None = None) -> dict[str, Any] | None:
    """Async variant of search_by_title for concurrent use in trail generation."""
    query = title.strip()
    if not query:
        return None

    data = await _async_get(
        "/works",
        params={
            "search": query,
            "per_page": 5,
        },
    )
    results = data.get("results") or []
    if not results:
        return None

    best_work: dict[str, Any] | None = None
    best_score = 0.0
    query_norm = query.lower()
    author_norm = (authors_hint or "").lower()

    for work in results:
        candidate_title = (work.get("display_name") or "").lower()
        title_score = SequenceMatcher(None, query_norm, candidate_title).ratio()
        bonus = 0.0
        if author_norm:
            candidate_authors = " ".join(_extract_authors(work)).lower()
            if author_norm and author_norm in candidate_authors:
                bonus = 0.1
        score = title_score + bonus
        if score > best_score:
            best_score = score
            best_work = work

    if best_work is None or best_score < 0.6:
        return None
    return _work_to_candidate(best_work)


async def async_search_works(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Async variant of search_works for concurrent use in trail generation."""
    if not query.strip():
        return []

    data = await _async_get(
        "/works",
        params={
            "search": query,
            "sort": "cited_by_count:desc",
            "per_page": max(1, min(limit, 25)),
        },
    )
    return [_work_to_candidate(work) for work in (data.get("results") or [])]
