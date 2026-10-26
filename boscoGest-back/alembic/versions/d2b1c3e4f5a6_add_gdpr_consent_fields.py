"""add GDPR consent fields to users

Records acceptance of the data-processing clause on first login. The version is
stored alongside the timestamp because a bare boolean cannot tell who agreed to
which text, leaving no way to re-request consent when the clause changes.

Revision ID: d2b1c3e4f5a6
Revises: c1a0b2d3e4f5
Create Date: 2026-08-25 12:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd2b1c3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'c1a0b2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('consent_accepted_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('users', sa.Column('consent_version', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'consent_version')
    op.drop_column('users', 'consent_accepted_at')
