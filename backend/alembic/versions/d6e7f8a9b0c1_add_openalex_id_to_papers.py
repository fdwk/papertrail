"""add openalex_id to papers

Revision ID: d6e7f8a9b0c1
Revises: c4e8a1b2d3f5
Create Date: 2026-03-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c4e8a1b2d3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("openalex_id", sa.String(), nullable=True))
    op.create_unique_constraint("uq_papers_openalex_id", "papers", ["openalex_id"])


def downgrade() -> None:
    op.drop_constraint("uq_papers_openalex_id", "papers", type_="unique")
    op.drop_column("papers", "openalex_id")
