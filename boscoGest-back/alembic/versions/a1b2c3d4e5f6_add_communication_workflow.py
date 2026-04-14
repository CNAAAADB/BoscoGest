"""add_communication_workflow

Revision ID: a1b2c3d4e5f6
Revises: bba396d52438
Create Date: 2026-02-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bba396d52438'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('communications', sa.Column('status', sa.String(20), nullable=False, server_default='draft'))
    op.add_column('communications', sa.Column('published_at', sa.TIMESTAMP(), nullable=True))

    # Backfill existing data: active communications become published, inactive become archived
    op.execute("UPDATE communications SET status = 'published', published_at = updated_at WHERE is_active = true")
    op.execute("UPDATE communications SET status = 'archived' WHERE is_active = false")


def downgrade() -> None:
    op.drop_column('communications', 'published_at')
    op.drop_column('communications', 'status')
