"""Pydantic schemas for API request/response. Match frontend Trail / DAGNode / Paper shapes."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


TrailSize = Literal["small", "medium", "large"]


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int
    abstract: str
    url: str
    isRead: bool
    note: str = ""
    isStarred: bool = False


class DAGNodeOut(BaseModel):
    id: str
    paper: PaperOut
    dependencies: list[str]


class TrailSummaryOut(BaseModel):
    """Lightweight trail for list view (no nodes/edges)."""
    id: str
    topic: str
    createdAt: str
    readCount: int = 0
    totalCount: int = 0


class TrailDetailOut(BaseModel):
    """Full trail with nodes (graph) for canvas. Fetched when trail is selected."""
    id: str
    topic: str
    createdAt: str
    nodes: list[DAGNodeOut]


class CreateTrailIn(BaseModel):
    """Request body for creating a new trail."""
    topic: str
    size: TrailSize = "medium"
