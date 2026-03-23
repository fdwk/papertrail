"""users: add account tier

Revision ID: 6a1b2c3d4e5f
Revises: d6e7f8a9b0c1
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "tier",
            sa.String(),
            nullable=False,
            server_default="Reader",
        ),
    )
    # Remove the server default once existing rows are backfilled.
    op.alter_column("users", "tier", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "tier")

