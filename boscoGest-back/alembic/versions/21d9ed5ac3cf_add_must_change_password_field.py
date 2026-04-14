"""add_must_change_password_field

Revision ID: 21d9ed5ac3cf
Revises: f02f18f1fb2b
Create Date: 2025-12-02 17:46:51.541143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21d9ed5ac3cf'
down_revision: Union[str, Sequence[str], None] = 'f02f18f1fb2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add must_change_password field to users table
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='true'))

    # Fix communications index name (cleanup from previous migration)
    op.drop_index(op.f('ix_news_id'), table_name='communications')
    op.create_index(op.f('ix_communications_id'), 'communications', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove must_change_password field from users table
    op.drop_column('users', 'must_change_password')

    # Revert communications index name
    op.drop_index(op.f('ix_communications_id'), table_name='communications')
    op.create_index(op.f('ix_news_id'), 'communications', ['id'], unique=False)
