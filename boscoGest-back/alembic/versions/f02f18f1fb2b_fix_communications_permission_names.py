"""fix_communications_permission_names

Revision ID: f02f18f1fb2b
Revises: xyz789abc456
Create Date: 2025-12-02 17:23:11.609604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f02f18f1fb2b'
down_revision: Union[str, Sequence[str], None] = 'xyz789abc456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix permission names to use 'Communications' instead of 'News'."""
    bind = op.get_bind()

    # Update permission names that still reference 'News'
    bind.execute(
        sa.text("""
            UPDATE permissions
            SET name = REPLACE(name, 'News', 'Communications')
            WHERE resource = 'communications' AND name LIKE '%News%'
        """)
    )


def downgrade() -> None:
    """Revert permission names back to 'News'."""
    bind = op.get_bind()

    # Revert permission names from 'Communications' back to 'News'
    bind.execute(
        sa.text("""
            UPDATE permissions
            SET name = REPLACE(name, 'Communications', 'News')
            WHERE resource = 'communications' AND name LIKE '%Communications%'
        """)
    )
