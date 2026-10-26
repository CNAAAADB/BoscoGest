"""drop fees.due_days (due date now derived from periodicity = end of period)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-01 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE fees DROP COLUMN due_days")


def downgrade() -> None:
    op.execute("ALTER TABLE fees ADD COLUMN due_days INTEGER NOT NULL DEFAULT 30")
