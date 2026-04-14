"""rename_news_to_communications

Revision ID: ghi456jkl789
Revises: def789abc123
Create Date: 2025-11-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ghi456jkl789'
down_revision: Union[str, Sequence[str], None] = 'def789abc123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename news table to communications and update related columns."""
    # Rename the table
    op.rename_table('news', 'communications')

    # Rename the foreign key column in comments table
    op.alter_column('comments', 'news_id',
                    new_column_name='communication_id',
                    existing_type=sa.Integer(),
                    existing_nullable=False)


def downgrade() -> None:
    """Revert communications table to news and update related columns."""
    # Rename the table back
    op.rename_table('communications', 'news')

    # Rename the foreign key column back in comments table
    op.alter_column('comments', 'communication_id',
                    new_column_name='news_id',
                    existing_type=sa.Integer(),
                    existing_nullable=False)
