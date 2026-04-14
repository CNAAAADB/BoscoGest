"""merge_heads

Revision ID: 413a68d9065a
Revises: d4e5f6a7b8c9, e1f2a3b4c5d6
Create Date: 2026-04-05 20:00:40.452686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '413a68d9065a'
down_revision: Union[str, Sequence[str], None] = ('d4e5f6a7b8c9', 'e1f2a3b4c5d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
