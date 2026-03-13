from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.schemas import TrailSize


DEFAULT_MODEL = "gpt-4o-mini"
SIZE_CONSTRAINTS: dict[TrailSize, dict[str, int]] = {
    "small": {"suggest_min": 6, "suggest_max": 8, "min_papers": 4, "max_papers": 6},
    "medium": {"suggest_min": 10, "suggest_max": 15, "min_papers": 6, "max_papers": 10},
    "large": {"suggest_min": 16, "suggest_max": 20, "min_papers": 10, "max_papers": 14},
}


class OpenAIClientError(RuntimeError):
    """Raised when OpenAI calls fail or return invalid JSON."""


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def _model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def _audit_dir() -> Path | None:
    """Return audit directory if auditing is enabled, else None.

    Controlled by OPENAI_AUDIT_DIR. If unset or empty, auditing is disabled.
    """
    raw = os.getenv("OPENAI_AUDIT_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def _write_audit_entry(name: str, payload: dict[str, Any], raw_response: str) -> None:
    """Best-effort append-only JSONL audit of GPT calls.

    Never raises; failures are silently ignored so product behavior is unchanged.
    """
    directory = _audit_dir()
    if directory is None:
        return

    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.jsonl"
        entry = {
            "ts": time.time(),
            "name": name,
            "model": _model(),
            "payload": payload,
            "raw_response": raw_response,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False))
            f.write("\n")
    except Exception:
        # Best-effort logging only.
        return


def _parse_json_response(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError("Model did not return valid JSON.") from exc


def suggest_papers(topic: str, size: TrailSize = "medium") -> list[dict[str, Any]]:
    topic_clean = topic.strip()
    constraints = SIZE_CONSTRAINTS[size]
    client = _client()
    completion = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an academic research assistant. "
                    f"Given a research topic, suggest {constraints['suggest_min']}-{constraints['suggest_max']} papers that are essential reading. "
                    "Include seminal papers, key advances, and influential surveys. "
                    "Return JSON with shape: "
                    '{"papers":[{"title":"...","authors":"...","year":2017}]}.'
                ),
            },
            {"role": "user", "content": f"Topic: {topic_clean}\nTrail size: {size}"},
        ],
    )
    content = completion.choices[0].message.content or "{}"

    # Best-effort local audit.
    _write_audit_entry(
        "suggest_papers",
        payload={"topic": topic_clean, "size": size},
        raw_response=content,
    )

    data = _parse_json_response(content)
    papers = data.get("papers")
    if not isinstance(papers, list):
        raise OpenAIClientError("suggest_papers response missing 'papers' list.")
    normalized: list[dict[str, Any]] = []
    for item in papers:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        authors = str(item.get("authors") or "").strip()
        year_raw = item.get("year")
        try:
            year = int(year_raw) if year_raw is not None else 0
        except (TypeError, ValueError):
            year = 0
        normalized.append({"title": title, "authors": authors, "year": year})
    return normalized[: constraints["suggest_max"]]


def select_and_order_papers(
    topic: str,
    verified_papers: list[dict[str, Any]],
    citation_edges: list[dict[str, str]],
    size: TrailSize = "medium",
) -> dict[str, Any]:
    constraints = SIZE_CONSTRAINTS[size]
    client = _client()
    slim_papers = []
    for p in verified_papers:
        slim_papers.append(
            {
                "openalex_id": p.get("openalex_id"),
                "title": p.get("title"),
                "authors": (p.get("authors") or [])[:3],  # first 3 authors max
                "year": p.get("year"),
                "citation_count": p.get("citation_count"),
                # optional: very short abstract snippet
                "summary": (p.get("abstract") or "")[:280],
            }
        )
    payload = {
        "topic": topic,
        "papers": slim_papers,
        "citation_edges": citation_edges,
        "constraints": {
            "size": size,
            "min_papers": constraints["min_papers"],
            "max_papers": constraints["max_papers"],
            "must_return_dag": True,
        },
    }
    completion = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are constructing a reading trail of academic papers. "
                    f"Select the best {constraints['min_papers']}-{constraints['max_papers']} papers that are most influential and relevant to the topic. "
                    "Organize them as a DAG ordering representing a logical learning progression. "
                    "Edges point from prerequisite paper to dependent paper. "
                    "Use only paper IDs from the input and do not invent new ones. "
                    "All edge endpoints must appear in selected_papers. "
                    "Occasionally include papers that synthesize 2+ prerequisite works. "
                    "Prefer a trail depth of at least 3 levels when possible. "
                    "No more than 2 root paper nodes with no prerequsities. "
                    "Return ONLY JSON with format "
                    '{"selected_papers":["W..."],"edges":[{"from":"W...","to":"W..."}]}.'
                )
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
    )
    content = completion.choices[0].message.content or "{}"

    # Best-effort local audit.
    _write_audit_entry(
        "select_and_order_papers",
        payload=payload,
        raw_response=content,
    )

    data = _parse_json_response(content)

    selected = data.get("selected_papers")
    edges = data.get("edges")
    if not isinstance(selected, list):
        selected = []
    if not isinstance(edges, list):
        edges = []

    selected_ids = [str(x) for x in selected if str(x).strip()]
    normalized_edges: list[dict[str, str]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        from_id = str(edge.get("from") or "").strip()
        to_id = str(edge.get("to") or "").strip()
        if from_id and to_id and from_id != to_id:
            normalized_edges.append({"from": from_id, "to": to_id})

    return {"selected_papers": selected_ids, "edges": normalized_edges}
