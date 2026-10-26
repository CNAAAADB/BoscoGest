"""move periodicity from fee_assignments to fees

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-31 14:00:00.000000

Periodicity becomes a property of the fee (set at creation), not of each
assignment. The assignment's `period` is derived from the fee's periodicity
and a reference date, so it is no longer typed manually.
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add periodicity to fees (enum type already exists). Tables are empty in dev;
    # a server default keeps the NOT NULL safe even if rows exist.
    op.execute("ALTER TABLE fees ADD COLUMN periodicity fee_periodicity NOT NULL DEFAULT 'annual'")
    op.execute("ALTER TABLE fees ALTER COLUMN periodicity DROP DEFAULT")
    # Periodicity no longer lives on the assignment
    op.execute("ALTER TABLE fee_assignments DROP COLUMN periodicity")


def downgrade() -> None:
    op.execute("ALTER TABLE fee_assignments ADD COLUMN periodicity fee_periodicity NOT NULL DEFAULT 'annual'")
    op.execute("ALTER TABLE fee_assignments ALTER COLUMN periodicity DROP DEFAULT")
    op.execute("ALTER TABLE fees DROP COLUMN periodicity")
