"""paper_graph_edges: add surrogate id PK (DAG support, next_node nullable)

Revision ID: c4e8a1b2d3f5
Revises: bcd0f9bc0fb4
Create Date: 2026-03-04

Allows multiple edges from the same paper in a trail (DAG). next_node_id stays
nullable for terminal nodes / "no next yet".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c4e8a1b2d3f5"
down_revision: Union[str, Sequence[str], None] = "bcd0f9bc0fb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "paper_graph_edges",
        sa.Column("id", UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE paper_graph_edges SET id = gen_random_uuid() WHERE id IS NULL"
    )
    op.alter_column(
        "paper_graph_edges",
        "id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "paper_graph_edges_pkey",
        "paper_graph_edges",
        type_="primary",
    )
    op.create_primary_key(
        "paper_graph_edges_pkey",
        "paper_graph_edges",
        ["id"],
    )
    op.create_index(
        "ix_paper_graph_edges_paper_trail_next",
        "paper_graph_edges",
        ["paper_id", "trail_id", "next_node_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_graph_edges_paper_trail_next",
        table_name="paper_graph_edges",
    )
    op.drop_constraint(
        "paper_graph_edges_pkey",
        "paper_graph_edges",
        type_="primary",
    )
    op.drop_column("paper_graph_edges", "id")
    op.create_primary_key(
        "paper_graph_edges_pkey",
        "paper_graph_edges",
        ["paper_id", "trail_id"],
    )
