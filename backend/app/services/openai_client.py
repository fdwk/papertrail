from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from app.schemas import TrailSize


DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
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
    return OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)


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


def enrich_edges_with_gpt(
    topic: str,
    papers: list[dict[str, Any]],
    citation_edges: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Suggest 0-5 conceptual prerequisite edges not captured by citation data.

    Returns only new edges; invalid or duplicate pairs are dropped.
    """
    client = _client()
    slim_papers = []
    for p in papers:
        slim_papers.append(
            {
                "openalex_id": p.get("openalex_id"),
                "title": p.get("title"),
                "authors": (p.get("authors") or [])[:3],
                "year": p.get("year"),
                "citation_count": p.get("citation_count"),
                "summary": (p.get("abstract") or "")[:500],
            }
        )
    payload = {
        "topic": topic,
        "papers": slim_papers,
        "citation_edges": citation_edges,
        "instructions": (
            "Suggest 0-5 additional prerequisite edges where one paper is genuinely needed "
            "to understand another, but the relationship is NOT already implied by citation_edges. "
            "Edges point from prerequisite to dependent. Use only openalex_id values from papers."
        ),
    }
    completion = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You help build reading trails. Given papers and known citation-based edges, "
                    "suggest only conceptual prerequisite edges missing from citation_edges. "
                    'Return JSON: {"new_edges":[{"from":"W...","to":"W..."}]} with at most 5 edges.'
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
    )
    content = completion.choices[0].message.content or "{}"

    _write_audit_entry(
        "enrich_edges_with_gpt",
        payload=payload,
        raw_response=content,
    )

    data = _parse_json_response(content)
    raw = data.get("new_edges")
    if not isinstance(raw, list):
        return []

    allowed = {
        str(p.get("openalex_id") or "").strip()
        for p in papers
        if str(p.get("openalex_id") or "").strip()
    }
    citation_pairs = {
        (str(e.get("from") or "").strip(), str(e.get("to") or "").strip())
        for e in citation_edges
        if str(e.get("from") or "").strip() and str(e.get("to") or "").strip()
    }

    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for edge in raw:
        if not isinstance(edge, dict):
            continue
        from_id = str(edge.get("from") or "").strip()
        to_id = str(edge.get("to") or "").strip()
        if not from_id or not to_id or from_id == to_id:
            continue
        if from_id not in allowed or to_id not in allowed:
            continue
        pair = (from_id, to_id)
        if pair in seen or pair in citation_pairs:
            continue
        seen.add(pair)
        out.append({"from": from_id, "to": to_id})
        if len(out) >= 5:
            break
    return out
