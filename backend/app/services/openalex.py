from __future__ import annotations

import asyncio
import os
import re
from difflib import SequenceMatcher
from typing import Any

import httpx

import logging

logger = logging.getLogger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org"
DEFAULT_TIMEOUT_SECONDS = 15.0
_ASYNC_CONCURRENCY_LIMIT = 5


class OpenAlexError(RuntimeError):
    """Raised when OpenAlex API calls fail."""


_async_semaphore: asyncio.Semaphore | None = None


def _get_async_semaphore() -> asyncio.Semaphore:
    global _async_semaphore
    if _async_semaphore is None:
        _async_semaphore = asyncio.Semaphore(_ASYNC_CONCURRENCY_LIMIT)
    return _async_semaphore


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


def _build_params(params: dict[str, Any] | None) -> dict[str, Any]:
    query = dict(params or {})
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        raise OpenAlexError("OPENALEX_API_KEY is not set.")
    query["api_key"] = api_key
    return query


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = _build_params(params)
    try:
        with _client() as client:
            response = client.get(f"{OPENALEX_BASE_URL}{path}", params=query)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc
    return response.json()


async def _async_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Async variant of _get so multiple OpenAlex calls can be awaited concurrently."""
    query = _build_params(params)
    try:
        async with _get_async_semaphore():
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{OPENALEX_BASE_URL}{path}", params=query)
                response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc
    return response.json()


def _author_hint_tokens(authors_hint: str | None) -> list[str]:
    """Split GPT-style author hints into surname-like tokens for fuzzy matching."""
    if not authors_hint:
        return []
    raw = re.split(r"[,;/]", authors_hint.lower())
    tokens: list[str] = []
    for part in raw:
        for word in part.split():
            w = re.sub(r"[^a-z\-]", "", word)
            if len(w) >= 2:
                tokens.append(w)
    return tokens


def _author_match_bonus(authors_hint: str | None, work: dict[str, Any]) -> float:
    tokens = _author_hint_tokens(authors_hint)
    if not tokens:
        return 0.0
    candidate_authors = " ".join(_extract_authors(work)).lower()
    bonus = 0.0
    for tok in tokens:
        if tok in candidate_authors:
            bonus += 0.05
    return min(bonus, 0.15)


def _strong_title_match(query_norm: str, candidate_title: str) -> bool:
    """True when GPT title clearly refers to this OpenAlex title (substring or key tokens)."""
    if not query_norm or not candidate_title:
        return False
    if query_norm in candidate_title or candidate_title in query_norm:
        return True
    q_words = [w for w in re.split(r"\W+", query_norm) if len(w) >= 4]
    if len(q_words) >= 2 and sum(1 for w in q_words if w in candidate_title) >= min(2, len(q_words)):
        return True
    return False


_TITLE_SEARCH_PER_PAGE = 10


def _pick_best_work(
    results: list[dict[str, Any]],
    query: str,
    authors_hint: str | None,
) -> tuple[dict[str, Any] | None, float]:
    best_work: dict[str, Any] | None = None
    best_score = 0.0
    query_norm = query.lower().strip()

    for work in results:
        candidate_title = (work.get("display_name") or "").lower()
        title_score = SequenceMatcher(None, query_norm, candidate_title).ratio()
        bonus = _author_match_bonus(authors_hint, work)
        overlap = 0.12 if _strong_title_match(query_norm, candidate_title) else 0.0
        score = title_score + bonus + overlap
        if score > best_score:
            best_score = score
            best_work = work

    if best_work is None:
        return None, best_score

    best_title = (best_work.get("display_name") or "").lower()
    if _strong_title_match(query_norm, best_title) and best_score >= 0.38:
        return best_work, best_score
    if best_score < 0.6:
        return None, best_score
    return best_work, best_score


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
            "per_page": _TITLE_SEARCH_PER_PAGE,
        },
    )
    results = data.get("results") or []
    if not results:
        return None

    best_work, _score = _pick_best_work(results, query, authors_hint)
    if best_work is None:
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
            "per_page": _TITLE_SEARCH_PER_PAGE,
        },
    )
    results = data.get("results") or []
    if not results:
        return None

    best_work, _score = _pick_best_work(results, query, authors_hint)
    if best_work is None:
        return None
    return _work_to_candidate(best_work)


async def async_search_works(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Async variant of search_works for concurrent use in trail generation."""
    if not query.strip():
        return []

    data = await _async_get(
        "/works",
        params={
            "search.semantic": query,
            "sort": "cited_by_count:desc",
            "per_page": max(1, min(limit, 25)),
        },
    )
    return [_work_to_candidate(work) for work in (data.get("results") or [])]
