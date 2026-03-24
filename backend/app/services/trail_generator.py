from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.trails import (
    create_trail_from_generated_data,
    get_trail_detail,
)
from app.schemas import (
    TrailExpansionConfirmIn,
    TrailExpansionProposalOut,
    TrailSize,
    TrailSummaryOut,
)
from app.models import Paper, Trail, UserPaper, PaperGraphEdge
from app.services.openai_client import (
    OpenAIClientError,
    select_and_order_papers,
    suggest_papers,
)
from app.services import openalex
from app.services.openalex import (
    OpenAlexError,
    async_search_by_title,
    async_search_works,
)


logger = logging.getLogger(__name__)
TRAIL_SIZE_CONFIG: dict[TrailSize, dict[str, int]] = {
    "small": {"suggest_limit": 8, "search_limit": 10, "max_papers": 6},
    "medium": {"suggest_limit": 15, "search_limit": 20, "max_papers": 10},
    "large": {"suggest_limit": 20, "search_limit": 20, "max_papers": 14},
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
        if not key:
            title = (candidate.get("title") or "").strip().lower()
            year = int(candidate.get("year") or 0)
            key = f"{title}:{year}" if title else ""
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


def _filter_edges_to_dag(
    node_ids: set[str],
    edges: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Filter edges to enforce a DAG: drop any edge that would introduce a cycle.

    Uses an incremental Kahn-style process to keep only acyclic edges.
    """
    adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    indegree: dict[str, int] = {nid: 0 for nid in node_ids}
    kept_edges: list[dict[str, str]] = []

    for edge in edges:
        from_id = str(edge.get("from") or "").strip()
        to_id = str(edge.get("to") or "").strip()
        if from_id not in node_ids or to_id not in node_ids or from_id == to_id:
            continue

        # Tentatively add edge.
        adj[from_id].add(to_id)
        indegree[to_id] += 1

        # Check for cycle via reachability from `to_id` back to `from_id`.
        stack = [to_id]
        visited: set[str] = set()
        introduces_cycle = False
        while stack:
            node = stack.pop()
            if node == from_id:
                introduces_cycle = True
                break
            if node in visited:
                continue
            visited.add(node)
            stack.extend(adj.get(node, ()))

        if introduces_cycle:
            # Revert this edge.
            adj[from_id].remove(to_id)
            indegree[to_id] -= 1
            continue

        kept_edges.append({"from": from_id, "to": to_id})

    return kept_edges


def _fallback_ordering(
    candidates: list[dict[str, Any]],
    *,
    max_papers: int,
    citation_edges: list[dict[str, str]] | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Fallback ordering when GPT selection fails.

    Prefer using citation_edges to build a DAG and topologically sort it.
    If no usable edges exist, fall back to a simple chronological chain.
    """
    id_to_candidate = {
        (c.get("openalex_id") or "").strip(): c
        for c in candidates
        if (c.get("openalex_id") or "").strip()
    }

    # Use graph-based ordering if we have edges.
    if citation_edges:
        # Build adjacency and indegree.
        adj: dict[str, set[str]] = {pid: set() for pid in id_to_candidate}
        indegree: dict[str, int] = {pid: 0 for pid in id_to_candidate}
        for edge in citation_edges:
            from_id = str(edge.get("from") or "").strip()
            to_id = str(edge.get("to") or "").strip()
            if from_id not in id_to_candidate or to_id not in id_to_candidate or from_id == to_id:
                continue
            if to_id not in adj[from_id]:
                adj[from_id].add(to_id)
                indegree[to_id] += 1

        # Kahn topological sort.
        queue: list[str] = [nid for nid, deg in indegree.items() if deg == 0]
        ordered_ids: list[str] = []
        idx = 0
        while idx < len(queue):
            node = queue[idx]
            idx += 1
            ordered_ids.append(node)
            for nbr in adj.get(node, ()):
                indegree[nbr] -= 1
                if indegree[nbr] == 0:
                    queue.append(nbr)

        # If we covered at least one node, use that topological order.
        if ordered_ids:
            selected = ordered_ids[:max_papers]
            edges: list[dict[str, str]] = []
            for from_id, tos in adj.items():
                for to_id in tos:
                    if from_id in selected and to_id in selected and from_id != to_id:
                        edges.append({"from": from_id, "to": to_id})
            return selected, edges

    # Chronological chain fallback.
    ordered = sorted(
        candidates,
        key=lambda p: (int(p.get("year") or 0), -(int(p.get("citation_count") or 0))),
    )
    selected = [(paper.get("openalex_id") or "").strip() for paper in ordered][:max_papers]
    selected = [sid for sid in selected if sid]
    edges: list[dict[str, str]] = []
    for idx in range(1, len(selected)):
        edges.append({"from": selected[idx - 1], "to": selected[idx]})
    return selected, edges


async def _run_trail_pipeline(
    topic: str,
    size: TrailSize,
) -> tuple[
    list[dict[str, Any]],  # candidates
    list[dict[str, str]],  # citation_edges
    list[dict[str, Any]],  # selected_papers
    list[dict[str, str]],  # selected_edges
]:
    """Core trail generation pipeline shared by async and streaming flows."""
    config = TRAIL_SIZE_CONFIG[size]

    # Launch OpenAlex supplemental search and GPT suggestions concurrently.
    supplement_task = asyncio.create_task(async_search_works(topic, config["search_limit"]))

    try:
        suggestions = await asyncio.to_thread(suggest_papers, topic, size)
    except OpenAIClientError as exc:
        logger.warning("GPT suggest_papers failed, falling back to OpenAlex search: %s", exc)
        suggestions = []

    # Verify GPT suggestions via OpenAlex title lookup concurrently.
    title_tasks: list[asyncio.Task] = []
    for suggestion in suggestions[: config["suggest_limit"]]:
        title = (suggestion.get("title") or "").strip()
        if not title:
            continue
        authors = suggestion.get("authors")
        title_tasks.append(asyncio.create_task(async_search_by_title(title, authors)))

    # Await title lookups and supplemental search together.
    results = await asyncio.gather(*title_tasks, supplement_task, return_exceptions=True)
    title_results = results[:-1]
    supplement_result = results[-1] if results else []

    verified: list[dict[str, Any]] = []
    for suggestion, result in zip(suggestions[: config["suggest_limit"]], title_results):
        title = (suggestion.get("title") or "").strip()
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

    raw_edges = _build_citation_edges(candidates)
    citation_edges = _filter_edges_to_dag(
        {c.get("openalex_id", "").strip() for c in candidates if (c.get("openalex_id") or "").strip()},
        raw_edges,
    )

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
        logger.warning("GPT select_and_order failed, falling back to ordering: %s", exc)
        selected_ids, selected_edges = _fallback_ordering(
            candidates,
            max_papers=config["max_papers"],
            citation_edges=citation_edges,
        )
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        selected_ids, selected_edges = _fallback_ordering(
            candidates,
            max_papers=config["max_papers"],
            citation_edges=citation_edges,
        )
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        raise TrailGenerationError("Unable to select enough papers for a trail.")

    return candidates, citation_edges, selected_papers, selected_edges


async def generate_trail_async(
    db: Session,
    user_id: uuid.UUID,
    topic: str,
    size: TrailSize = "medium",
) -> TrailSummaryOut:
    topic = topic.strip()
    if not topic:
        raise TrailGenerationError("Topic cannot be empty.")
    _, _, selected_papers, selected_edges = await _run_trail_pipeline(topic, size)

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
    supplement_task = asyncio.create_task(async_search_works(topic, config["search_limit"]))
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
        result = await async_search_by_title(title, authors)
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

    if not supplement:
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

    raw_edges = _build_citation_edges(candidates)
    citation_edges = _filter_edges_to_dag(
        {c.get("openalex_id", "").strip() for c in candidates if (c.get("openalex_id") or "").strip()},
        raw_edges,
    )

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
        logger.warning("GPT select_and_order failed, falling back to ordering: %s", exc)
        selected_ids, selected_edges = _fallback_ordering(
            candidates,
            max_papers=config["max_papers"],
            citation_edges=citation_edges,
        )
        selected_papers = [id_to_candidate[sid] for sid in selected_ids if sid in id_to_candidate]

    if len(selected_papers) < 3:
        selected_ids, selected_edges = _fallback_ordering(
            candidates,
            max_papers=config["max_papers"],
            citation_edges=citation_edges,
        )
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


def generate_expansion(
    db: Session,
    user_id: uuid.UUID,
    trail_id: uuid.UUID,
    source_node_id: uuid.UUID,
) -> TrailExpansionProposalOut:
    """Generate a small, ephemeral expansion proposal for a given node in a trail.

    This does NOT persist anything to the database. It uses OpenAlex to find a
    handful of related works given the trail topic + source paper title, and
    returns them as DAGNodeOut-shaped data with edges from the source node.
    """
    trail: Trail | None = db.query(Trail).filter(Trail.id == trail_id, Trail.user_id == user_id).first()
    if not trail:
        raise TrailGenerationError("Trail not found.")

    source_paper: Paper | None = db.query(Paper).filter(Paper.id == source_node_id).first()
    if not source_paper:
        raise TrailGenerationError("Source node not found in trail.")

    # Use a simple query combining topic + source title to find related works.
    query = f"{trail.topic} {source_paper.title}".strip()
    if not query:
        raise TrailGenerationError("Cannot expand from an empty topic/title.")

    # Collect OpenAlex IDs of papers already in this trail so we can skip them.
    trail_paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        trail_paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            trail_paper_ids.add(edge.next_node_id)
    existing_openalex_ids: set[str] = set()
    if trail_paper_ids:
        for p in db.query(Paper).filter(Paper.id.in_(trail_paper_ids)).all():
            if p.openalex_id:
                existing_openalex_ids.add(p.openalex_id.strip())

    # Keep this expansion lightweight: a small number of candidates only.
    try:
        candidates = openalex.search_works(query, limit=10)
    except OpenAlexError as exc:  # type: ignore[unreachable]
        logger.warning("OpenAlex search for expansion failed: %s", exc)
        candidates = []

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    for candidate in candidates:
        if len(nodes) >= 4:
            break
        openalex_id = (candidate.get("openalex_id") or "").strip()
        if not openalex_id:
            continue
        if openalex_id in existing_openalex_ids:
            continue
        year = int(candidate.get("year") or 0)
        safe_year = year if 1500 <= year <= 3000 else 0
        paper_out = {
            "id": openalex_id,
            "title": (candidate.get("title") or "").strip(),
            "authors": list(candidate.get("authors") or []),
            "year": safe_year,
            "abstract": (candidate.get("abstract") or "").strip(),
            "url": (candidate.get("url") or "").strip(),
            "isRead": False,
            "note": "",
            "isStarred": False,
        }
        node = {
            "id": openalex_id,
            "paper": paper_out,
            # For now, model each expansion node as depending directly on the source node.
            "dependencies": [str(source_node_id)],
        }
        nodes.append(node)
        edges.append({"source": str(source_node_id), "target": openalex_id})

    return TrailExpansionProposalOut(nodes=nodes, edges=edges)


def apply_expansion(
    db: Session,
    user_id: uuid.UUID,
    trail_id: uuid.UUID,
    payload: TrailExpansionConfirmIn,
):
    """Persist an accepted expansion into an existing trail and return updated detail.

    This recomputes the same OpenAlex search used in generate_expansion and then
    filters to only the acceptedNodeIds. New Paper rows and PaperGraphEdge rows
    are created as needed, along with UserPaper join rows for the current user.
    """
    trail: Trail | None = db.query(Trail).filter(Trail.id == trail_id, Trail.user_id == user_id).first()
    if not trail:
        raise TrailGenerationError("Trail not found.")

    try:
        source_uuid = uuid.UUID(payload.sourceNodeId)
    except ValueError as exc:
        raise TrailGenerationError("Invalid source node id.") from exc

    source_paper: Paper | None = db.query(Paper).filter(Paper.id == source_uuid).first()
    if not source_paper:
        raise TrailGenerationError("Source node not found in trail.")

    query = f"{trail.topic} {source_paper.title}".strip()
    if not query:
        raise TrailGenerationError("Cannot expand from an empty topic/title.")

    # Collect papers already in this trail so we don't re-add them (which could create cycles).
    trail_paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        trail_paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            trail_paper_ids.add(edge.next_node_id)
    existing_openalex_ids: set[str] = set()
    if trail_paper_ids:
        for p in db.query(Paper).filter(Paper.id.in_(trail_paper_ids)).all():
            if p.openalex_id:
                existing_openalex_ids.add(p.openalex_id.strip())

    try:
        candidates = openalex.search_works(query, limit=12)
    except OpenAlexError as exc:  # type: ignore[unreachable]
        logger.warning("OpenAlex search for expansion (confirm) failed: %s", exc)
        candidates = []

    by_openalex_id: dict[str, dict[str, Any]] = {}
    for cand in candidates:
        oid = (cand.get("openalex_id") or "").strip()
        if oid:
            by_openalex_id[oid] = cand

    accepted_ids: list[str] = [
        (nid or "").strip() for nid in payload.acceptedNodeIds if (nid or "").strip()
    ]
    if not accepted_ids:
        return get_trail_detail(db, trail.id, user_id)

    persisted_ids: list[uuid.UUID] = []
    for external_id in accepted_ids:
        if external_id in existing_openalex_ids:
            continue
        raw = by_openalex_id.get(external_id)
        if not raw:
            continue

        openalex_id = (raw.get("openalex_id") or "").strip() or None
        doi = (raw.get("doi") or "").strip() or None
        title = (raw.get("title") or "").strip()
        if not title:
            continue

        paper: Paper | None = None
        if openalex_id:
            paper = db.query(Paper).filter(Paper.openalex_id == openalex_id).first()
        if paper is None and doi:
            paper = db.query(Paper).filter(Paper.doi == doi).first()
        if paper is None:
            year = int(raw.get("year") or 0)
            safe_year = year if 1500 <= year <= 3000 else 1970
            paper = Paper(
                title=title,
                author=", ".join(raw.get("authors") or []),
                abstract=(raw.get("abstract") or "").strip() or None,
                doi=doi,
                openalex_id=openalex_id,
                date=datetime(safe_year, 1, 1),
                url=(raw.get("url") or "").strip() or None,
            )
            db.add(paper)
            db.flush()
        else:
            paper.title = title or paper.title
            if raw.get("authors"):
                paper.author = ", ".join(raw.get("authors"))
            if raw.get("abstract"):
                paper.abstract = (raw.get("abstract") or "").strip()
            if openalex_id and not paper.openalex_id:
                paper.openalex_id = openalex_id
            if doi and not paper.doi:
                paper.doi = doi
            if raw.get("url"):
                paper.url = (raw.get("url") or "").strip()

        persisted_ids.append(paper.id)

        # Create an edge from the source node into this new paper within this trail.
        db.add(
            PaperGraphEdge(
                paper_id=source_uuid,
                trail_id=trail.id,
                next_node_id=paper.id,
            )
        )

    if not persisted_ids:
        # Nothing new was persisted; return existing detail.
        return get_trail_detail(db, trail.id, user_id)

    # Ensure UserPaper rows exist for every newly added paper for this user.
    existing = {
        (up.user_id, up.paper_id)
        for up in db.query(UserPaper).filter(
            UserPaper.user_id == user_id,
            UserPaper.paper_id.in_(persisted_ids),
        ).all()
    }
    for pid in persisted_ids:
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

    trail.last_modified = datetime.utcnow()
    db.commit()

    return get_trail_detail(db, trail.id, user_id)
