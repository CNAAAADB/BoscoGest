"""enable unaccent for user search

ILIKE folds case but not diacritics, so "garcia" never matched "García" —
and nobody types accents into a search box. With a mostly Spanish membership
that made the majority of surnames unfindable.

Revision ID: e3c2d4f5a6b7
Revises: d2b1c3e4f5a6
Create Date: 2026-08-25 12:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e3c2d4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'd2b1c3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS unaccent"))


def downgrade() -> None:
    # Left in place: other objects may come to depend on it, and dropping an
    # extension is not worth the risk of breaking them.
    pass
