"""users: nullable password_hash for Google-only accounts

Revision ID: e8f2a1b0c3d4
Revises: 7b2c4d8e9f01
Create Date: 2026-04-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e8f2a1b0c3d4"
down_revision: Union[str, Sequence[str], None] = "7b2c4d8e9f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(),
        nullable=False,
    )
