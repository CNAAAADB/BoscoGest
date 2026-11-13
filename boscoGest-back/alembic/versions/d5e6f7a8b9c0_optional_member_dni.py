"""Allow member records without DNI.

Revision ID: d5e6f7a8b9c0
Revises: c4d8e2f6a1b3
Create Date: 2026-11-13

An administrative member record may not have a login identifier yet.
Email and phone are already nullable; DNI is the last NOT NULL field.
Multiple NULL DNI values are allowed by PostgreSQL's unique constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d8e2f6a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users", "dni",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    # A downgrade cannot restore NOT NULL while incomplete members exist:
    # abort with an explicit error instead of inventing identification data.
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT COUNT(*) FROM users WHERE dni IS NULL")).scalar():
        raise RuntimeError(
            "Cannot restore users.dni NOT NULL while member records have no DNI"
        )
    op.alter_column(
        "users", "dni",
        existing_type=sa.String(length=20),
        existing_nullable=True,
        nullable=False,
    )
