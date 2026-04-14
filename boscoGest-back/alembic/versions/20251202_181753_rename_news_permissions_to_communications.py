"""rename_news_permissions_to_communications

Revision ID: xyz789abc456
Revises: 13b6104641b8
Create Date: 2025-12-02 18:17:53

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'xyz789abc456'
down_revision: Union[str, Sequence[str], None] = '13b6104641b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename news permissions to communications permissions."""
    bind = op.get_bind()

    # Check if there are any 'news' permissions to rename
    result = bind.execute(
        sa.text("SELECT COUNT(*) FROM permissions WHERE resource = 'news'")
    )
    count = result.fetchone()[0]

    if count > 0:
        # Update permission names from 'news' to 'communications'
        bind.execute(
            sa.text("""
                UPDATE permissions
                SET
                    resource = 'communications',
                    name = REPLACE(name, 'news', 'communications'),
                    description = REPLACE(COALESCE(description, ''), 'news', 'communications')
                WHERE resource = 'news'
            """)
        )
        print(f"Renamed {count} news permissions to communications")
    else:
        print("No news permissions found to rename")


def downgrade() -> None:
    """Revert communications permissions back to news permissions (only those we renamed)."""
    bind = op.get_bind()

    # Only rename back if there are 'communications' permissions that look like they were renamed from 'news'
    # This prevents accidentally renaming permissions that were created directly as 'communications'
    result = bind.execute(
        sa.text("""
            SELECT COUNT(*) FROM permissions
            WHERE resource = 'communications'
            AND (
                action IN ('create', 'read', 'edit', 'delete', 'manage_all')
                OR name LIKE '%communications%'
            )
        """)
    )
    count = result.fetchone()[0]

    if count > 0:
        # Update permission names from 'communications' back to 'news'
        bind.execute(
            sa.text("""
                UPDATE permissions
                SET
                    resource = 'news',
                    name = REPLACE(name, 'communications', 'news'),
                    description = REPLACE(COALESCE(description, ''), 'communications', 'news')
                WHERE resource = 'communications'
                AND (
                    action IN ('create', 'read', 'edit', 'delete', 'manage_all')
                    OR name LIKE '%communications%'
                )
            """)
        )
        print(f"Reverted {count} communications permissions back to news")
    else:
        print("No communications permissions found to revert")
