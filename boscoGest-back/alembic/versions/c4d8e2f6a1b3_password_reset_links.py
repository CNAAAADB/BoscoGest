"""password reset links

Revision ID: c4d8e2f6a1b3
Revises: b7e3c9d2a4f1
Create Date: 2026-11-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e2f6a1b3'
down_revision: Union[str, Sequence[str], None] = 'b7e3c9d2a4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    The links for a forgotten password live in the same table as the welcome
    ones; this column tells them apart. Existing rows are all welcome links.
    """
    op.add_column(
        'activation_tokens',
        sa.Column('purpose', sa.String(length=16), server_default='activation', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reset links would turn into sign-in links without a password; drop them.
    op.execute("DELETE FROM activation_tokens WHERE purpose = 'reset'")
    op.drop_column('activation_tokens', 'purpose')
