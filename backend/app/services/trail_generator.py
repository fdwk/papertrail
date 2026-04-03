from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable

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
    enrich_edges_with_gpt,
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

# Scoring weights for algorithmic paper selection.
# Citation count is the main signal for "importance"; in-set in-degree is secondary glue.
_W_IN_DEGREE = 0.45
_W_CITATION = 10.0
_W_VERIFIED = 0.35
_W_DECADE_DIVERSITY = 0.12
_MAX_FAN_OUT = 3
# Verified (GPT title-matched) papers with citation_count / max(selected) at or above this
# get priority at the root / front of topological order.
_HIGH_VERIFIED_REL_CIT_FOR_ROOT = 0.18

SUGGEST_THREAD_TIMEOUT_S = 120.0


class TrailGenerationError(RuntimeError):
    """Raised when the external pipeline cannot generate enough papers."""


def _safe_year(raw_year: Any, *, default: int = 1970) -> int:
    try:
        y = int(raw_year or 0)
    except (TypeError, ValueError):
        return default
    return y if 1500 <= y <= 3000 else default


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


def _tag_source(paper: dict[str, Any], source: str) -> dict[str, Any]:
    out = dict(paper)
    out["_source"] = source
    return out


def _max_citation_among(node_ids: set[str], id_to_candidate: dict[str, dict[str, Any]]) -> int:
    m = max((int(id_to_candidate[pid].get("citation_count") or 0) for pid in node_ids), default=0)
    return max(m, 1)


def _reading_order_sort_key(
    pid: str,
    id_to_candidate: dict[str, dict[str, Any]],
    *,
    max_cit: int,
) -> tuple[int, int, int, str]:
    """Earlier in tuple → earlier in trail reading order among DAG peers (roots / ready nodes)."""
    mc = max(max_cit, 1)
    cit = int(id_to_candidate[pid].get("citation_count") or 0)
    rel = cit / mc
    is_verified = id_to_candidate[pid].get("_source") == "verified"
    high_signal_verified = is_verified and rel >= _HIGH_VERIFIED_REL_CIT_FOR_ROOT
    y = int(id_to_candidate[pid].get("year") or 9999)
    y_sort = y if y > 0 else 9999
    tier = 0 if high_signal_verified else 1
    return (tier, -cit, y_sort, pid)


def _dedupe_directed_edges(node_ids: set[str], edges: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for e in edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u not in node_ids or v not in node_ids or u == v:
            continue
        p = (u, v)
        if p in seen:
            continue
        seen.add(p)
        out.append({"from": u, "to": v})
    return out


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by openalex_id or title+year; prefer verified over supplement."""
    best_by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for candidate in candidates:
        key = (candidate.get("openalex_id") or "").strip()
        if not key:
            title = (candidate.get("title") or "").strip().lower()
            year = int(candidate.get("year") or 0)
            key = f"{title}:{year}" if title else ""
        if not key:
            continue

        existing = best_by_key.get(key)
        if existing is None:
            best_by_key[key] = candidate
            order.append(key)
            continue
        # Prefer verified (GPT-matched) over supplement-only
        ex_src = existing.get("_source")
        new_src = candidate.get("_source")
        if new_src == "verified" and ex_src != "verified":
            best_by_key[key] = candidate
        elif new_src == ex_src:
            # Keep first; could merge fields — keep higher citation_count
            if int(candidate.get("citation_count") or 0) > int(existing.get("citation_count") or 0):
                merged = dict(candidate)
                merged["_source"] = ex_src
                best_by_key[key] = merged

    return [best_by_key[k] for k in order]


def _index_by_openalex_id(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        (c.get("openalex_id") or "").strip(): c
        for c in candidates
        if (c.get("openalex_id") or "").strip()
    }


def _strip_internal_fields(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in p.items() if not str(k).startswith("_")} for p in papers]


def _collect_trail_openalex_ids(db: Session, trail: Trail) -> set[str]:
    trail_paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        trail_paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            trail_paper_ids.add(edge.next_node_id)
    existing: set[str] = set()
    if trail_paper_ids:
        for p in db.query(Paper).filter(Paper.id.in_(trail_paper_ids)).all():
            if p.openalex_id:
                existing.add(p.openalex_id.strip())
    return existing


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
    """Filter edges to enforce a DAG: drop any edge that would introduce a cycle."""
    adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    indegree: dict[str, int] = {nid: 0 for nid in node_ids}
    kept_edges: list[dict[str, str]] = []

    for edge in edges:
        from_id = str(edge.get("from") or "").strip()
        to_id = str(edge.get("to") or "").strip()
        if from_id not in node_ids or to_id not in node_ids or from_id == to_id:
            continue

        adj[from_id].add(to_id)
        indegree[to_id] += 1

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
            adj[from_id].remove(to_id)
            indegree[to_id] -= 1
            continue

        kept_edges.append({"from": from_id, "to": to_id})

    return kept_edges


def _reachable(from_id: str, to_id: str, adj: dict[str, set[str]]) -> bool:
    if from_id == to_id:
        return True
    stack = [from_id]
    seen = {from_id}
    while stack:
        n = stack.pop()
        for w in adj.get(n, ()):
            if w == to_id:
                return True
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return False


def _adjacency_from_edges(edges: list[dict[str, str]], node_ids: set[str]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u in node_ids and v in node_ids:
            adj[u].add(v)
    return adj


def _path_exists_in_edges(
    edges: list[dict[str, str]],
    node_ids: set[str],
    start: str,
    end: str,
) -> bool:
    if start == end:
        return True
    adj = _adjacency_from_edges(edges, node_ids)
    return _reachable(start, end, adj)


def _edge_maintains_dag(node_ids: set[str], edges: list[dict[str, str]], u: str, v: str) -> bool:
    """True if adding directed edge u->v would not create a cycle."""
    adj = _adjacency_from_edges(edges, node_ids)
    return not _reachable(v, u, adj)


def _ensure_single_root(
    node_ids: set[str],
    edges: list[dict[str, str]],
    id_to_candidate: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    indegree = {nid: 0 for nid in node_ids}
    for e in edges:
        vt = str(e.get("to") or "").strip()
        if vt in indegree:
            indegree[vt] += 1
    roots = [n for n in node_ids if indegree[n] == 0]
    if len(roots) <= 1:
        return edges

    max_cit = _max_citation_among(node_ids, id_to_candidate)

    def root_sort_key(pid: str) -> tuple[int, int, int, str]:
        return _reading_order_sort_key(pid, id_to_candidate, max_cit=max_cit)

    roots_sorted = sorted(roots, key=root_sort_key)
    canonical = roots_sorted[0]
    out = list(edges)
    seen_pairs = {(str(e["from"]).strip(), str(e["to"]).strip()) for e in out}
    for r in roots_sorted[1:]:
        c, rr = canonical, r
        if (c, rr) in seen_pairs:
            continue
        if not _edge_maintains_dag(node_ids, out, c, rr):
            continue
        out.append({"from": c, "to": rr})
        seen_pairs.add((c, rr))
    return _filter_edges_to_dag(node_ids, out)


def _add_learning_spine(
    node_ids: set[str],
    edges: list[dict[str, str]],
    ordered: list[str],
) -> list[dict[str, str]]:
    """Bridge **weakly disconnected** parts of the DAG along reading order.

    The old behavior added an edge for every consecutive topo pair with no directed path,
    which serialised fan-out (A→B, A→C forced B→C) and, with transitive reduction,
    collapsed the graph to a single path. Here we only add (a→b) when a and b lie in
    different undirected components—so shared hubs and parallel branches stay intact.
    """
    out = list(edges)
    seen_pairs = {(str(e["from"]).strip(), str(e["to"]).strip()) for e in out}
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        if a not in node_ids or b not in node_ids:
            continue
        if _path_exists_in_edges(out, node_ids, a, b):
            continue
        if (a, b) in seen_pairs:
            continue
        wcc = _wcc_index_map(node_ids, out)
        if wcc.get(a) == wcc.get(b):
            continue
        if not _edge_maintains_dag(node_ids, out, a, b):
            continue
        out.append({"from": a, "to": b})
        seen_pairs.add((a, b))
    return _filter_edges_to_dag(node_ids, out)


def _transitive_reduce_edges(node_ids: set[str], edges: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop edge (u→v) when another directed path u⇝v exists (standard DAG transitive reduction)."""
    pairs = [
        (str(e["from"]).strip(), str(e["to"]).strip())
        for e in edges
        if str(e.get("from") or "").strip() in node_ids and str(e.get("to") or "").strip() in node_ids
    ]
    pairs = list(dict.fromkeys(pairs))
    kept: list[tuple[str, str]] = []
    for u, v in pairs:
        adj: dict[str, set[str]] = defaultdict(set)
        for u2, v2 in pairs:
            if (u2, v2) == (u, v):
                continue
            adj[u2].add(v2)
        if _reachable(u, v, adj):
            continue
        kept.append((u, v))
    return [{"from": u, "to": v} for u, v in kept]


def _transitive_reduce_using_basis_paths(
    node_ids: set[str],
    edges: list[dict[str, str]],
    basis_edges: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Remove (u→v) only when u reaches v through **basis** edges alone, excluding that u→v.

    Prevents stripping citation shortcuts (e.g. A→C) because a **new** spine edge completed
    A→B→C; only removes edges that were already redundant in the pre-spine DAG.
    """

    def norm_pairs(el: list[dict[str, str]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for e in el:
            u = str(e.get("from") or "").strip()
            v = str(e.get("to") or "").strip()
            if u not in node_ids or v not in node_ids or u == v:
                continue
            p = (u, v)
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
        return out

    basis_pairs = norm_pairs(basis_edges)
    merged_pairs = norm_pairs(edges)
    kept: list[tuple[str, str]] = []
    for u, v in merged_pairs:
        adj: dict[str, set[str]] = defaultdict(set)
        for u2, v2 in basis_pairs:
            if u2 == u and v2 == v:
                continue
            adj[u2].add(v2)
        if _reachable(u, v, adj):
            continue
        kept.append((u, v))
    return [{"from": u, "to": v} for u, v in kept]


def _in_set_citation_in_degree(candidate_ids: set[str], candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts = {cid: 0 for cid in candidate_ids}
    for c in candidates:
        oid = (c.get("openalex_id") or "").strip()
        if not oid:
            continue
        for ref in c.get("referenced_works") or []:
            r = str(ref).strip()
            if r in counts and r != oid:
                counts[r] += 1
    return counts


def _neighbor_in_citation_graph(node: str, selected: set[str], citation_edges: list[dict[str, str]]) -> bool:
    for e in citation_edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u == node and v in selected:
            return True
        if v == node and u in selected:
            return True
    return False


def _score_and_select_papers(
    candidates: list[dict[str, Any]],
    citation_edges: list[dict[str, str]],
    *,
    max_papers: int,
    id_to_candidate: dict[str, dict[str, Any]],
) -> list[str]:
    ids = [pid for pid in id_to_candidate]
    if not ids:
        return []
    candidate_ids = set(ids)
    in_deg = _in_set_citation_in_degree(candidate_ids, candidates)
    max_in = max(in_deg.values()) if in_deg.values() else 1
    max_in = max(max_in, 1)
    max_cit = max(int(id_to_candidate[i].get("citation_count") or 0) for i in ids)
    max_cit = max(max_cit, 1)

    def base_score(pid: str) -> float:
        cit = int(id_to_candidate[pid].get("citation_count") or 0)
        verified = 1.0 if id_to_candidate[pid].get("_source") == "verified" else 0.0
        # Linear in cit/max_cit so ~100 vs ~80k citations are not washed out by log compression.
        cit_norm = cit / max_cit
        return (
            _W_IN_DEGREE * (in_deg.get(pid, 0) / max_in)
            + _W_CITATION * cit_norm
            + _W_VERIFIED * verified
        )

    def decade(pid: str) -> int:
        y = int(id_to_candidate[pid].get("year") or 0)
        return (y // 10) * 10 if y > 0 else -1

    def decade_bonus(pid: str, selected: list[str]) -> float:
        d = decade(pid)
        if d < 0:
            return 0.0
        sel_decades = {decade(s) for s in selected if decade(s) >= 0}
        return _W_DECADE_DIVERSITY if d not in sel_decades else 0.0

    def pick_key(pid: str, selected: list[str]) -> tuple[float, float, int]:
        sc = base_score(pid) + decade_bonus(pid, selected)
        y = int(id_to_candidate[pid].get("year") or 9999)
        cit = int(id_to_candidate[pid].get("citation_count") or 0)
        return (sc, -cit, y)

    verified_ids = [i for i in ids if id_to_candidate[i].get("_source") == "verified"]

    def verified_seed_key(i: str) -> tuple[int, float, tuple[float, float, int]]:
        cit_i = int(id_to_candidate[i].get("citation_count") or 0)
        rel = cit_i / max_cit
        high = rel >= _HIGH_VERIFIED_REL_CIT_FOR_ROOT
        return (0 if high else 1, -rel, pick_key(i, []))

    verified_sorted = sorted(verified_ids, key=verified_seed_key)
    take_v = min(len(verified_sorted), max_papers)
    selected: list[str] = list(verified_sorted[:take_v]) if take_v else []
    remaining = set(ids) - set(selected)

    if not selected:
        first = max(remaining, key=lambda i: pick_key(i, []))
        selected.append(first)
        remaining.remove(first)

    while len(selected) < max_papers and remaining:
        sel_set = set(selected)
        connected = [i for i in remaining if _neighbor_in_citation_graph(i, sel_set, citation_edges)]
        pool = connected if connected else list(remaining)
        best = max(pool, key=lambda i: pick_key(i, selected))
        selected.append(best)
        remaining.remove(best)

    return selected


def _undirected_components(nodes: set[str], edges: list[dict[str, str]]) -> list[set[str]]:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for e in edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u in nodes and v in nodes:
            adj[u].add(v)
            adj[v].add(u)
    seen: set[str] = set()
    comps: list[set[str]] = []
    for n in nodes:
        if n in seen:
            continue
        stack = [n]
        comp: set[str] = set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.add(x)
            stack.extend(adj[x])
        comps.append(comp)
    return comps


def _wcc_index_map(node_ids: set[str], edges: list[dict[str, str]]) -> dict[str, int]:
    """Map node → weakly-connected component id for the undirected view of `edges`."""
    comps = _undirected_components(node_ids, edges)
    return {n: i for i, c in enumerate(comps) for n in c}


def _extreme_by_year(
    comp: set[str],
    id_to_candidate: dict[str, dict[str, Any]],
    *,
    earliest: bool,
) -> str:
    def earliest_key(pid: str) -> tuple[int, int, str]:
        y = int(id_to_candidate[pid].get("year") or 0)
        cit = int(id_to_candidate[pid].get("citation_count") or 0)
        # Missing year sorts last when picking earliest
        y_sort = y if y > 0 else 9999
        return (y_sort, -cit, pid)

    def latest_key(pid: str) -> tuple[int, int, str]:
        y = int(id_to_candidate[pid].get("year") or 0)
        cit = int(id_to_candidate[pid].get("citation_count") or 0)
        # Missing year sorts first when negating for max
        y_sort = y if y > 0 else -1
        return (y_sort, cit, pid)

    if earliest:
        return min(comp, key=earliest_key)
    return max(comp, key=latest_key)


def _build_dag_backbone(
    selected_ids: list[str],
    citation_edges: list[dict[str, str]],
    id_to_candidate: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, str]], set[tuple[str, str]]]:
    """Return full backbone edges and protected pairs (root merge + glue) for fan-out exemption."""
    selected_set = set(selected_ids)
    protected: set[tuple[str, str]] = set()
    edges = [
        {"from": str(e["from"]).strip(), "to": str(e["to"]).strip()}
        for e in citation_edges
        if str(e.get("from") or "").strip() in selected_set and str(e.get("to") or "").strip() in selected_set
    ]
    edges = _transitive_reduce_edges(selected_set, edges)
    edges = _filter_edges_to_dag(selected_set, edges)

    # Indegree for roots
    indegree = {nid: 0 for nid in selected_set}
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        u, v = e["from"], e["to"]
        adj[u].add(v)
        indegree[v] += 1

    roots = sorted([n for n in selected_set if indegree[n] == 0])
    if len(roots) > 1:
        max_cit_bb = _max_citation_among(selected_set, id_to_candidate)

        def root_sort_key(pid: str) -> tuple[int, int, int, str]:
            return _reading_order_sort_key(pid, id_to_candidate, max_cit=max_cit_bb)

        roots_sorted = sorted(roots, key=root_sort_key)
        canonical = roots_sorted[0]
        edge_pairs = {(e["from"], e["to"]) for e in edges}
        for r in roots_sorted[1:]:
            p = (canonical, r)
            if p not in edge_pairs:
                edges.append({"from": canonical, "to": r})
                edge_pairs.add(p)
                protected.add(p)
        edges = _filter_edges_to_dag(selected_set, edges)

    # Connect weakly disconnected components (chronological glue)
    comps = _undirected_components(selected_set, edges)
    if len(comps) > 1:

        def comp_min_year(c: set[str]) -> int:
            ys = [int(id_to_candidate[pid].get("year") or 0) for pid in c]
            ys = [y for y in ys if y > 0]
            return min(ys) if ys else 9999

        comps_sorted = sorted(comps, key=comp_min_year)
        glue_pairs = {(e["from"], e["to"]) for e in edges}
        for i in range(len(comps_sorted) - 1):
            a, b = comps_sorted[i], comps_sorted[i + 1]
            u = _extreme_by_year(a, id_to_candidate, earliest=False)
            v = _extreme_by_year(b, id_to_candidate, earliest=True)
            if u != v and (u, v) not in glue_pairs:
                edges.append({"from": u, "to": v})
                glue_pairs.add((u, v))
                protected.add((u, v))
        edges = _filter_edges_to_dag(selected_set, edges)
        edges = _transitive_reduce_edges(selected_set, edges)

    edge_set = {(e["from"], e["to"]) for e in edges}
    protected = {p for p in protected if p in edge_set}

    return edges, protected


def _enforce_max_fan_out(
    node_ids: set[str],
    edges: list[dict[str, str]],
    id_to_candidate: dict[str, dict[str, Any]],
    *,
    max_out: int = _MAX_FAN_OUT,
    protected_pairs: set[tuple[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Cap optional outgoing edges per node; never drop protected_pairs (root merge, glue)."""
    protected = protected_pairs or set()
    by_from: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        u, v = str(e["from"]).strip(), str(e["to"]).strip()
        if u in node_ids and v in node_ids:
            by_from[u].append((u, v))

    kept: list[dict[str, str]] = []
    for u, outs in by_from.items():
        mandatory = [pair for pair in outs if pair in protected]
        extra = [pair for pair in outs if pair not in protected]
        combined = mandatory + extra
        if len(combined) <= max_out:
            for pair in combined:
                kept.append({"from": pair[0], "to": pair[1]})
            continue
        if len(mandatory) >= max_out:
            for pair in mandatory:
                kept.append({"from": pair[0], "to": pair[1]})
            continue
        slots = max_out - len(mandatory)
        extra_sorted = sorted(
            extra,
            key=lambda uv: int(id_to_candidate[uv[1]].get("citation_count") or 0),
            reverse=True,
        )
        for pair in mandatory:
            kept.append({"from": pair[0], "to": pair[1]})
        for pair in extra_sorted[:slots]:
            kept.append({"from": pair[0], "to": pair[1]})
    return kept


def _topological_order_ids(
    node_ids: set[str],
    edges: list[dict[str, str]],
    id_to_candidate: dict[str, dict[str, Any]],
) -> list[str]:
    max_cit = _max_citation_among(node_ids, id_to_candidate)

    def rk(pid: str) -> tuple[int, int, int, str]:
        return _reading_order_sort_key(pid, id_to_candidate, max_cit=max_cit)

    adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    indegree = {nid: 0 for nid in node_ids}
    for e in edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u in node_ids and v in node_ids and u != v:
            if v not in adj[u]:
                adj[u].add(v)
                indegree[v] += 1

    queue = sorted([nid for nid, d in indegree.items() if d == 0], key=rk)
    ordered: list[str] = []
    qi = 0
    while qi < len(queue):
        node = queue[qi]
        qi += 1
        ordered.append(node)
        neighbors = sorted(adj.get(node, ()), key=rk)
        for nbr in neighbors:
            indegree[nbr] -= 1
            if indegree[nbr] == 0:
                queue.append(nbr)
    # Any cycle leftovers — append stable sort
    leftover = sorted(node_ids - set(ordered), key=rk)
    return ordered + leftover


def _finalize_dag(
    selected_ids: list[str],
    backbone_edges: list[dict[str, str]],
    backbone_protected: set[tuple[str, str]],
    gpt_edges: list[dict[str, str]],
    id_to_candidate: dict[str, dict[str, Any]],
) -> tuple[list[str], list[dict[str, str]]]:
    selected_set = set(selected_ids)
    merged: list[dict[str, str]] = []
    seen_e: set[tuple[str, str]] = set()
    for e in backbone_edges + gpt_edges:
        u = str(e.get("from") or "").strip()
        v = str(e.get("to") or "").strip()
        if u not in selected_set or v not in selected_set or u == v:
            continue
        p = (u, v)
        if p in seen_e:
            continue
        seen_e.add(p)
        merged.append({"from": u, "to": v})

    merged = _dedupe_directed_edges(selected_set, merged)
    merged = _filter_edges_to_dag(selected_set, merged)
    merged = _transitive_reduce_edges(selected_set, merged)
    merged = _enforce_max_fan_out(
        selected_set,
        merged,
        id_to_candidate,
        max_out=_MAX_FAN_OUT,
        protected_pairs=backbone_protected,
    )
    merged = _filter_edges_to_dag(selected_set, merged)
    merged = _ensure_single_root(selected_set, merged, id_to_candidate)
    merged = _filter_edges_to_dag(selected_set, merged)

    ordered = _topological_order_ids(selected_set, merged, id_to_candidate)
    ordered = [pid for pid in ordered if pid in selected_set]
    pre_spine_merged = list(merged)
    merged = _add_learning_spine(selected_set, merged, ordered)
    ordered = _topological_order_ids(selected_set, merged, id_to_candidate)
    ordered = [pid for pid in ordered if pid in selected_set]
    merged = _dedupe_directed_edges(selected_set, merged)
    # Drop only shortcuts that were redundant **before** spine; keeps branches + interesting shape.
    merged = _transitive_reduce_using_basis_paths(selected_set, merged, pre_spine_merged)
    ordered = _topological_order_ids(selected_set, merged, id_to_candidate)
    ordered = [pid for pid in ordered if pid in selected_set]
    return ordered, merged


def _curate_trail_dag(
    topic: str,
    candidates: list[dict[str, Any]],
    citation_edges: list[dict[str, str]],
    *,
    max_papers: int,
    id_to_candidate: dict[str, dict[str, Any]],
) -> tuple[list[str], list[dict[str, str]]]:
    selected_ids = _score_and_select_papers(
        candidates,
        citation_edges,
        max_papers=max_papers,
        id_to_candidate=id_to_candidate,
    )
    if len(selected_ids) < 3:
        return [], []

    backbone, backbone_protected = _build_dag_backbone(selected_ids, citation_edges, id_to_candidate)
    selected_dicts = [id_to_candidate[pid] for pid in selected_ids if pid in id_to_candidate]

    gpt_edges: list[dict[str, str]] = []
    try:
        gpt_edges = enrich_edges_with_gpt(topic, selected_dicts, backbone)
    except OpenAIClientError as exc:
        logger.warning("GPT enrich_edges_with_gpt failed, using citation backbone only: %s", exc)

    return _finalize_dag(selected_ids, backbone, backbone_protected, gpt_edges, id_to_candidate)


def _fallback_ordering(
    candidates: list[dict[str, Any]],
    *,
    max_papers: int,
    citation_edges: list[dict[str, str]] | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Fallback ordering when primary curation fails."""
    id_to_candidate = _index_by_openalex_id(candidates)

    if citation_edges:
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

        if ordered_ids:
            selected = ordered_ids[:max_papers]
            edges: list[dict[str, str]] = []
            for from_id, tos in adj.items():
                for to_id in tos:
                    if from_id in selected and to_id in selected and from_id != to_id:
                        edges.append({"from": from_id, "to": to_id})
            edges = _transitive_reduce_edges(set(selected), edges)
            return selected, edges

    def sort_key(p: dict[str, Any]) -> tuple[int, int, int]:
        verified_first = 0 if p.get("_source") == "verified" else 1
        y = int(p.get("year") or 0)
        cit = int(p.get("citation_count") or 0)
        return (verified_first, y, -cit)

    ordered = sorted(candidates, key=sort_key)
    selected = [(paper.get("openalex_id") or "").strip() for paper in ordered][:max_papers]
    selected = [sid for sid in selected if sid]
    edges_fb: list[dict[str, str]] = []
    for idx in range(1, len(selected)):
        edges_fb.append({"from": selected[idx - 1], "to": selected[idx]})
    return selected, edges_fb


async def _emit(
    on_event: Callable[[dict[str, Any]], Awaitable[None]] | None,
    event: dict[str, Any],
) -> None:
    if on_event is not None:
        await on_event(event)


async def _run_trail_pipeline(
    topic: str,
    size: TrailSize,
    *,
    on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    stream_ui: bool = False,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, Any]],
    list[dict[str, str]],
]:
    """Core trail generation: gather candidates, build DAG, return selected trail."""
    config = TRAIL_SIZE_CONFIG[size]
    supplement_task = asyncio.create_task(async_search_works(topic, config["search_limit"]))

    if stream_ui:
        await _emit(
            on_event,
            {
                "type": "status",
                "stage": "suggesting",
                "message": f"Finding high-signal papers for a {size} trail...",
            },
        )
        suggest_task = asyncio.create_task(
            asyncio.wait_for(
                asyncio.to_thread(suggest_papers, topic, size),
                timeout=SUGGEST_THREAD_TIMEOUT_S,
            )
        )
        streamed_openalex_ids: set[str] = set()
        supplement: list[dict[str, Any]] = []
        supplement_fetched = False
        heartbeat_messages = [
            "Analyzing your topic and drafting candidate papers...",
            "Scanning for seminal and survey works...",
            "Scoring candidate papers for signal and relevance...",
        ]
        heartbeat_idx = 0
        while not suggest_task.done():
            if supplement_task.done() and not supplement_fetched:
                supplement_fetched = True
                try:
                    supplement = await supplement_task
                except OpenAlexError as exc:
                    logger.warning("OpenAlex supplementary search failed: %s", exc)
                    supplement = []
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Unexpected error during OpenAlex supplementary search: %s",
                        exc,
                        exc_info=True,
                    )
                    supplement = []
                else:
                    if supplement:
                        await _emit(
                            on_event,
                            {
                                "type": "status",
                                "stage": "suggesting",
                                "message": "OpenAlex is already surfacing promising papers...",
                            },
                        )
                        for paper in supplement:
                            paper_id = (paper.get("openalex_id") or "").strip()
                            if paper_id and paper_id not in streamed_openalex_ids:
                                streamed_openalex_ids.add(paper_id)
                                await _emit(
                                    on_event,
                                    {
                                        "type": "verified",
                                        "paper": _paper_preview(_tag_source(paper, "supplement"), verified=True),
                                    },
                                )
            await asyncio.sleep(0.8)
            if suggest_task.done():
                break
            await _emit(
                on_event,
                {
                    "type": "status",
                    "stage": "suggesting",
                    "message": heartbeat_messages[heartbeat_idx % len(heartbeat_messages)],
                },
            )
            heartbeat_idx += 1

        try:
            suggestions = await suggest_task
        except OpenAIClientError as exc:
            logger.warning("GPT suggest_papers failed, falling back to OpenAlex search: %s", exc)
            suggestions = []
        except asyncio.TimeoutError:
            logger.warning("GPT suggest_papers timed out after %ss", SUGGEST_THREAD_TIMEOUT_S)
            suggestions = []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error in suggest_papers: %s", exc, exc_info=True)
            suggestions = []

        for suggestion in suggestions[: config["suggest_limit"]]:
            title = (suggestion.get("title") or "").strip()
            if not title:
                continue
            await _emit(
                on_event,
                {"type": "candidate", "paper": _paper_preview(suggestion, verified=False)},
            )

        await _emit(
            on_event,
            {
                "type": "status",
                "stage": "searching",
                "message": "Verifying papers and discovering related work...",
            },
        )

        async def _lookup_with_title(title: str, authors: Any) -> tuple[str, Any]:
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
                tagged = _tag_source(result, "verified")
                verified.append(tagged)
                paper_id = (result.get("openalex_id") or "").strip()
                if paper_id and paper_id not in streamed_openalex_ids:
                    streamed_openalex_ids.add(paper_id)
                    await _emit(
                        on_event,
                        {"type": "verified", "paper": _paper_preview(tagged, verified=True)},
                    )

        if not supplement_fetched:
            supplement_fetched = True
            try:
                supplement = await supplement_task
            except OpenAlexError as exc:
                logger.warning("OpenAlex supplementary search failed: %s", exc)
                supplement = []
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Unexpected error during OpenAlex supplementary search: %s",
                    exc,
                    exc_info=True,
                )
                supplement = []

        supplement_tagged = [_tag_source(p, "supplement") for p in supplement]
        for paper in supplement_tagged:
            paper_id = (paper.get("openalex_id") or "").strip()
            if paper_id and paper_id not in streamed_openalex_ids:
                streamed_openalex_ids.add(paper_id)
                await _emit(
                    on_event,
                    {"type": "verified", "paper": _paper_preview(paper, verified=True)},
                )

    else:
        try:
            suggestions = await asyncio.wait_for(
                asyncio.to_thread(suggest_papers, topic, size),
                timeout=SUGGEST_THREAD_TIMEOUT_S,
            )
        except OpenAIClientError as exc:
            logger.warning("GPT suggest_papers failed, falling back to OpenAlex search: %s", exc)
            suggestions = []
        except asyncio.TimeoutError:
            logger.warning("GPT suggest_papers timed out after %ss", SUGGEST_THREAD_TIMEOUT_S)
            suggestions = []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error in suggest_papers: %s", exc, exc_info=True)
            suggestions = []

        title_lookups: list[tuple[dict[str, Any], str]] = []
        title_tasks: list[asyncio.Task] = []
        for suggestion in suggestions[: config["suggest_limit"]]:
            title = (suggestion.get("title") or "").strip()
            if not title:
                continue
            authors = suggestion.get("authors")
            title_lookups.append((suggestion, title))
            title_tasks.append(asyncio.create_task(async_search_by_title(title, authors)))

        results = await asyncio.gather(*title_tasks, supplement_task, return_exceptions=True)
        title_results = results[:-1]
        supplement_result = results[-1] if results else []

        verified = []
        for (_suggestion, title), result in zip(title_lookups, title_results):
            if isinstance(result, OpenAlexError):
                logger.warning("OpenAlex title search failed for '%s': %s", title, result)
                continue
            if isinstance(result, Exception):
                logger.warning("Unexpected error during OpenAlex title search for '%s': %s", title, result)
                continue
            if result:
                verified.append(_tag_source(result, "verified"))

        supplement_tagged = []
        if isinstance(supplement_result, OpenAlexError):
            logger.warning("OpenAlex supplementary search failed: %s", supplement_result)
        elif isinstance(supplement_result, Exception):
            logger.warning("Unexpected error during OpenAlex supplementary search: %s", supplement_result)
        elif isinstance(supplement_result, list):
            supplement_tagged = [_tag_source(p, "supplement") for p in supplement_result]

    candidates = _dedupe_candidates(verified + supplement_tagged)
    if len(candidates) < 3:
        raise TrailGenerationError("Not enough verified candidate papers from OpenAlex.")

    await _emit(
        on_event,
        {
            "type": "status",
            "stage": "selecting",
            "message": "Curating a coherent learning path...",
        },
    )

    raw_edges = _build_citation_edges(candidates)
    citation_edges = _filter_edges_to_dag(
        {c.get("openalex_id", "").strip() for c in candidates if (c.get("openalex_id") or "").strip()},
        raw_edges,
    )

    id_to_candidate = _index_by_openalex_id(candidates)

    selected_ids, selected_edges = _curate_trail_dag(
        topic,
        candidates,
        citation_edges,
        max_papers=config["max_papers"],
        id_to_candidate=id_to_candidate,
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

    selected_papers = _strip_internal_fields(selected_papers)

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

    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict[str, Any]) -> None:
        await queue.put(event)

    async def worker() -> None:
        try:
            *_, selected_papers, selected_edges = await _run_trail_pipeline(
                topic,
                size,
                on_event=on_event,
                stream_ui=True,
            )
            await queue.put(
                {
                    "type": "_internal_done",
                    "papers": selected_papers,
                    "edges": selected_edges,
                }
            )
        except TrailGenerationError as exc:
            await queue.put({"type": "_internal_error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Trail stream pipeline failed: %s", exc)
            await queue.put({"type": "_internal_error", "message": "Trail generation failed."})

    task = asyncio.create_task(worker())
    try:
        while True:
            event = await queue.get()
            if event.get("type") == "_internal_done":
                yield {
                    "type": "status",
                    "stage": "saving",
                    "message": "Saving your trail...",
                }
                trail = create_trail_from_generated_data(
                    db=db,
                    user_id=user_id,
                    topic=topic,
                    papers_data=event["papers"],
                    edges_data=event["edges"],
                )
                yield {"type": "complete", "trail_id": str(trail.id)}
                break
            if event.get("type") == "_internal_error":
                yield {"type": "error", "message": event.get("message", "Trail generation failed.")}
                break
            yield event
    finally:
        await task


def generate_expansion(
    db: Session,
    user_id: uuid.UUID,
    trail_id: uuid.UUID,
    source_node_id: uuid.UUID,
) -> TrailExpansionProposalOut:
    """Generate a small, ephemeral expansion proposal for a given node in a trail."""
    trail: Trail | None = db.query(Trail).filter(Trail.id == trail_id, Trail.user_id == user_id).first()
    if not trail:
        raise TrailGenerationError("Trail not found.")

    source_paper: Paper | None = db.query(Paper).filter(Paper.id == source_node_id).first()
    if not source_paper:
        raise TrailGenerationError("Source node not found in trail.")

    query = f"{trail.topic} {source_paper.title}".strip()
    if not query:
        raise TrailGenerationError("Cannot expand from an empty topic/title.")

    trail_paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        trail_paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            trail_paper_ids.add(edge.next_node_id)
    if source_node_id not in trail_paper_ids:
        raise TrailGenerationError("Source node is not part of this trail.")

    existing_openalex_ids = _collect_trail_openalex_ids(db, trail)

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
        y = int(candidate.get("year") or 0)
        display_year = y if 1500 <= y <= 3000 else 0
        paper_out = {
            "id": openalex_id,
            "title": (candidate.get("title") or "").strip(),
            "authors": list(candidate.get("authors") or []),
            "year": display_year,
            "abstract": (candidate.get("abstract") or "").strip(),
            "url": (candidate.get("url") or "").strip(),
            "isRead": False,
            "note": "",
            "isStarred": False,
        }
        node = {
            "id": openalex_id,
            "paper": paper_out,
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
    """Persist an accepted expansion into an existing trail and return updated detail."""
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

    trail_paper_ids: set[uuid.UUID] = set()
    for edge in trail.edges:
        trail_paper_ids.add(edge.paper_id)
        if edge.next_node_id is not None:
            trail_paper_ids.add(edge.next_node_id)
    if source_uuid not in trail_paper_ids:
        raise TrailGenerationError("Source node is not part of this trail.")

    existing_openalex_ids = _collect_trail_openalex_ids(db, trail)

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
            safe_year = _safe_year(raw.get("year"), default=1970)
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

        db.add(
            PaperGraphEdge(
                paper_id=source_uuid,
                trail_id=trail.id,
                next_node_id=paper.id,
            )
        )

    if not persisted_ids:
        return get_trail_detail(db, trail.id, user_id)

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
