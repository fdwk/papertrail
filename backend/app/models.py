from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Enum,
    ForeignKey,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base



class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    # Account plan tier used by the upgrade page and sidebar indicator.
    tier: Mapped[str] = mapped_column(String, nullable=False, default="Reader")

    trails: Mapped[list["Trail"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_papers: Mapped[list["UserPaper"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Trail(Base):
    __tablename__ = "trails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(String, nullable=False)

    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_viewed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="trails")
    edges: Mapped[list["PaperGraphEdge"]] = relationship(
        back_populates="trail",
        cascade="all, delete-orphan",
    )


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    openalex_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)

    user_links: Mapped[list["UserPaper"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    trail_edges: Mapped[list["PaperGraphEdge"]] = relationship(
        back_populates="paper",
        foreign_keys="PaperGraphEdge.paper_id",
        cascade="all, delete-orphan",
    )
    next_edges: Mapped[list["PaperGraphEdge"]] = relationship(
        back_populates="next_node",
        foreign_keys="PaperGraphEdge.next_node_id",
    )


class UserPaper(Base):
    """
    Join table between User and Paper
    """

    __tablename__ = "user_papers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )

    has_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_read: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="user_papers")
    paper: Mapped["Paper"] = relationship(back_populates="user_links")


class PaperGraphEdge(Base):
    """
    Edge in a user's trail graph. We model `nextNode` as another Paper in the same trail.
    One paper can have multiple next nodes in a trail (DAG). Surrogate id as PK so
    next_node_id can be null (terminal node / no next yet).
    """

    __tablename__ = "paper_graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
    )
    trail_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trails.id", ondelete="CASCADE"),
        nullable=False,
    )
    next_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="SET NULL"),
        nullable=True,
    )

    trail: Mapped["Trail"] = relationship(back_populates="edges")
    paper: Mapped["Paper"] = relationship(
        back_populates="trail_edges",
        foreign_keys=[paper_id],
    )
    next_node: Mapped["Paper | None"] = relationship(
        back_populates="next_edges",
        foreign_keys=[next_node_id],
    )
