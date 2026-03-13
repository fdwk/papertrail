from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.trails import create_trail_from_generated_data
from app.schemas import TrailSize, TrailSummaryOut
from app.services.openai_client import (
    OpenAIClientError,
    select_and_order_papers,
    suggest_papers,
)
from app.services import openalex
from app.services.openalex import OpenAlexError


logger = logging.getLogger(__name__)
TRAIL_SIZE_CONFIG: dict[TrailSize, dict[str, int]] = {
    "small": {"suggest_limit": 8, "search_limit": 6, "max_papers": 6},
    "medium": {"suggest_limit": 15, "search_limit": 10, "max_papers": 10},
    "large": {"suggest_limit": 20, "search_limit": 14, "max_papers": 14},
}


class TrailGenerationError(RuntimeError):
    """Raised when the external pipeline cannot generate enough papers."""


def _paper_preview(paper: dict[str, Any], *, verified: bool | None = None) -> dict[str, Any]:
    preview = {
        "openalex_id": (paper.get("openalex_id") or "").strip() or None,
        "title": (paper.get("title") or "").strip(),
        "authors": list(paper.get("authors") or []),
        "year": int(paper.get("year") or 0) or None,
    }
    if verified is not None:
        preview["verified"] = verified
    return preview


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (candidate.get("openalex_id") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _build_citation_edges(candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidate_ids = {
        (candidate.get("openalex_id") or "").strip()
        for candidate in candidates
        if (candidate.get("openalex_id") or "").strip()
    }
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for candidate in candidates:
        from_id = (candidate.get("openalex_id") or "").strip()
        if not from_id:
            continue
        for ref in candidate.get("referenced_works") or []:
            to_id = str(ref).strip()
            # referenced_works means from_id cites to_id. For reading order we want
            # prerequisite -> dependent, so reverse it: to_id -> from_id.
            if to_id not in candidate_ids or to_id == from_id:
                continue
            pair = (to_id, from_id)
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({"from": to_id, "to": from_id})
    return edges


def _fallback_ordering(
    candidates: list[dict[str, Any]],
    *,
    max_papers: int,
) -> tuple[list[str], list[dict[str, str]]]:
    ordered = sorted(candidates, key=lambda p: (int(p.get("year") or 0), -(int(p.get("citation_count") or 0))))
    selected = [(paper.get("openalex_id") or "").strip() for paper in ordered][:max_papers]
    selected = [sid for sid in selected if sid]
    edges: list[dict[str, str]] = []
    for idx in range(1, len(selected)):
        edges.append({"from": selected[idx - 1], "to": selected[idx]})
    return selected, edges


# Backwards-compatible sync search helpers so tests can monkeypatch these
def search_by_title(title: str, authors_hint: str | None = None) -> dict[str, Any] | None:
    return openalex.search_by_title(title, authors_hint)


def search_works(topic: str, limit: int = 10) -> list[dict[str, Any]]:
    return openalex.search_works(topic, limit=limit)


async def generate_trail_async(
    db: Session,
    user_id: uuid.UUID,
    topic: str,
    size: TrailSize = "medium",
) -> TrailSummaryOut:
    topic = topic.strip()
    if not topic:
        raise TrailGenerationError("Topic cannot be empty.")
    config = TRAIL_SIZE_CONFIG[size]

    # Start supplementary OpenAlex search immediately so it overlaps with OpenAI suggestion latency.
    topic_task = asyncio.create_task(asyncio.to_thread(search_works, topic, config["search_limit"]))

    try:
        suggestions = await asyncio.to_thread(suggest_papers, topic, size)
    except OpenAIClientError as exc:
        logger.warning("GPT suggest_papers failed, falling back to OpenAlex search: %s", exc)
        suggestions = []

    # Fire OpenAlex title lookups concurrently (running sync helpers in a thread pool).
    title_author_pairs: list[tuple[str, Any]] = []
    title_tasks: list[asyncio.Task] = []
    for suggestion in suggestions[: config["suggest_limit"]]:
        title = (suggestion.get("title") or "").strip()
        if not title:
            continue
        title_author_pairs.append((title, suggestion.get("authors")))
        title_tasks.append(asyncio.to_thread(search_by_title, title, suggestion.get("authors")))

    results = await asyncio.gather(*title_tasks, topic_task, return_exceptions=True)

    title_results = results[:-1]
    supplement_result = results[-1] if results else []

    verified: list[dict[str, Any]] = []
    for (title, _authors), result in zip(title_author_pairs, title_results):
        if isinstance(result, OpenAlexError):
            logger.warning("OpenAlex title search failed for '%s': %s", title, result)
            continue
        if isinstance(result, Exception):
            logger.warning("Unexpected error during OpenAlex title search for '%s': %s", title, result)
            continue
        if result:
            verified.append(result)

    supplement: list[dict[str, Any]] = []
    if isinstance(supplement_result, OpenAlexError):
        logger.warning("OpenAlex supplementary search failed: %s", supplement_result)
    elif isinstance(supplement_result, Exception):
        logger.warning("Unexpected error during OpenAlex supplementary search: %s", supplement_result)
    elif isinstance(supplement_result, list):
        supplement = supplement_result

    candidates = _dedupe_candidates(verified + supplement)
    if len(candidates) < 3:
        raise TrailGenerationError("Not enough verified candidate papers from OpenAlex.")

    citation_edges = _build_citation_edges(candidates)

    id_to_candidate = {
        (candidate.get("openalex_id") or "").strip(): candidate for candidate in candidates
        if (candidate.get("openalex_id") or "").strip()
    }

    try:
        curated = select_and_order_papers(topic, candidates, citation_edges, size)
        selected_ids = curated.get("selected_papers") or []
        selected_ids = [str(x).strip() for x in selected_ids if str(x).strip()]
        selected_ids = selected_ids[: config["max_papers"]]
        selected_set = set(selected_ids)
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

        selected_edges: list[dict[str, str]] = []
        for edge in curated.get("edges") or []:
            from_id = str(edge.get("from") or "").strip()
            to_id = str(edge.get("to") or "").strip()
            if from_id in selected_set and to_id in selected_set and from_id != to_id:
                selected_edges.append({"from": from_id, "to": to_id})
    except OpenAIClientError as exc:
        logger.warning("GPT select_and_order failed, falling back to chronological ordering: %s", exc)
        selected_ids, selected_edges = _fallback_ordering(candidates, max_papers=config["max_papers"])
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        selected_ids, selected_edges = _fallback_ordering(candidates, max_papers=config["max_papers"])
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        raise TrailGenerationError("Unable to select enough papers for a trail.")

    return create_trail_from_generated_data(
        db=db,
        user_id=user_id,
        topic=topic,
        papers_data=selected_papers,
        edges_data=selected_edges,
    )


async def generate_trail_stream(
    db: Session,
    user_id: uuid.UUID,
    topic: str,
    size: TrailSize = "medium",
):
    """Yield generation progress events and finish with complete/error."""
    topic = topic.strip()
    if not topic:
        yield {"type": "error", "message": "Topic cannot be empty."}
        return
    config = TRAIL_SIZE_CONFIG[size]

    yield {
        "type": "status",
        "stage": "suggesting",
        "message": f"Finding high-signal papers for a {size} trail...",
    }

    # Start supplementary OpenAlex search immediately so it overlaps with OpenAI suggestion latency.
    supplement_task = asyncio.create_task(asyncio.to_thread(search_works, topic, config["search_limit"]))
    suggest_task = asyncio.create_task(asyncio.to_thread(suggest_papers, topic, size))
    streamed_openalex_ids: set[str] = set()
    supplement: list[dict[str, Any]] = []

    heartbeat_messages = [
        "Analyzing your topic and drafting candidate papers...",
        "Scanning for seminal and survey works...",
        "Scoring candidate papers for signal and relevance...",
    ]
    heartbeat_idx = 0
    while not suggest_task.done():
        if supplement_task.done() and not supplement:
            try:
                supplement = await supplement_task
            except OpenAlexError as exc:
                logger.warning("OpenAlex supplementary search failed: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unexpected error during OpenAlex supplementary search: %s", exc)
            else:
                if supplement:
                    yield {
                        "type": "status",
                        "stage": "suggesting",
                        "message": "OpenAlex is already surfacing promising papers...",
                    }
                    for paper in supplement:
                        paper_id = (paper.get("openalex_id") or "").strip()
                        if paper_id and paper_id not in streamed_openalex_ids:
                            streamed_openalex_ids.add(paper_id)
                            yield {
                                "type": "verified",
                                "paper": _paper_preview(paper, verified=True),
                            }
        await asyncio.sleep(0.8)
        if suggest_task.done():
            break
        yield {
            "type": "status",
            "stage": "suggesting",
            "message": heartbeat_messages[heartbeat_idx % len(heartbeat_messages)],
        }
        heartbeat_idx += 1

    try:
        suggestions = await suggest_task
    except OpenAIClientError as exc:
        logger.warning("GPT suggest_papers failed, falling back to OpenAlex search: %s", exc)
        suggestions = []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error in suggest_papers: %s", exc)
        suggestions = []

    for suggestion in suggestions[: config["suggest_limit"]]:
        title = (suggestion.get("title") or "").strip()
        if not title:
            continue
        yield {
            "type": "candidate",
            "paper": _paper_preview(suggestion, verified=False),
        }

    yield {
        "type": "status",
        "stage": "searching",
        "message": "Verifying papers and discovering related work...",
    }

    async def _lookup_with_title(title: str, authors: Any):
        result = await asyncio.to_thread(search_by_title, title, authors)
        return title, result

    title_tasks: list[asyncio.Task] = []
    for suggestion in suggestions[: config["suggest_limit"]]:
        title = (suggestion.get("title") or "").strip()
        if not title:
            continue
        authors = suggestion.get("authors")
        title_tasks.append(asyncio.create_task(_lookup_with_title(title, authors)))

    verified: list[dict[str, Any]] = []

    for task in asyncio.as_completed(title_tasks):
        try:
            title, result = await task
        except OpenAlexError as exc:
            logger.warning("OpenAlex title search failed: %s", exc)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error during OpenAlex title search: %s", exc)
            continue
        if result:
            verified.append(result)
            paper_id = (result.get("openalex_id") or "").strip()
            if paper_id and paper_id not in streamed_openalex_ids:
                streamed_openalex_ids.add(paper_id)
                yield {
                    "type": "verified",
                    "paper": _paper_preview(result, verified=True),
                }

    if not supplement and supplement_task.done():
        try:
            supplement = await supplement_task
        except OpenAlexError as exc:
            logger.warning("OpenAlex supplementary search failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error during OpenAlex supplementary search: %s", exc)
    elif not supplement:
        try:
            supplement = await supplement_task
        except OpenAlexError as exc:
            logger.warning("OpenAlex supplementary search failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error during OpenAlex supplementary search: %s", exc)

    for paper in supplement:
        paper_id = (paper.get("openalex_id") or "").strip()
        if paper_id and paper_id not in streamed_openalex_ids:
            streamed_openalex_ids.add(paper_id)
            yield {
                "type": "verified",
                "paper": _paper_preview(paper, verified=True),
            }

    candidates = _dedupe_candidates(verified + supplement)
    if len(candidates) < 3:
        yield {"type": "error", "message": "Not enough verified candidate papers from OpenAlex."}
        return

    yield {
        "type": "status",
        "stage": "selecting",
        "message": "Curating a coherent learning path...",
    }

    citation_edges = _build_citation_edges(candidates)

    id_to_candidate = {
        (candidate.get("openalex_id") or "").strip(): candidate for candidate in candidates
        if (candidate.get("openalex_id") or "").strip()
    }

    try:
        curated = select_and_order_papers(topic, candidates, citation_edges, size)
        selected_ids = curated.get("selected_papers") or []
        selected_ids = [str(x).strip() for x in selected_ids if str(x).strip()]
        selected_ids = selected_ids[: config["max_papers"]]
        selected_set = set(selected_ids)
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

        selected_edges: list[dict[str, str]] = []
        for edge in curated.get("edges") or []:
            from_id = str(edge.get("from") or "").strip()
            to_id = str(edge.get("to") or "").strip()
            if from_id in selected_set and to_id in selected_set and from_id != to_id:
                selected_edges.append({"from": from_id, "to": to_id})
    except OpenAIClientError as exc:
        logger.warning("GPT select_and_order failed, falling back to chronological ordering: %s", exc)
        selected_ids, selected_edges = _fallback_ordering(candidates, max_papers=config["max_papers"])
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        selected_ids, selected_edges = _fallback_ordering(candidates, max_papers=config["max_papers"])
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        yield {"type": "error", "message": "Unable to select enough papers for a trail."}
        return

    yield {
        "type": "status",
        "stage": "saving",
        "message": "Saving your trail...",
    }

    trail = create_trail_from_generated_data(
        db=db,
        user_id=user_id,
        topic=topic,
        papers_data=selected_papers,
        edges_data=selected_edges,
    )
    yield {"type": "complete", "trail_id": str(trail.id)}


def generate_trail(
    db: Session,
    user_id: uuid.UUID,
    topic: str,
    size: TrailSize = "medium",
) -> TrailSummaryOut:
    """Synchronous wrapper to preserve existing callsites (e.g. tests)."""
    return asyncio.run(generate_trail_async(db, user_id, topic, size))
