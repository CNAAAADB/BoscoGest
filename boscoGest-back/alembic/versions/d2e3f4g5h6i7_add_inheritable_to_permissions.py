"""add_inheritable_to_permissions

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: Union[str, None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add inheritable column with default True
    op.add_column(
        'permissions',
        sa.Column('inheritable', sa.Boolean(), nullable=False, server_default='true')
    )

    # Set non-inheritable permissions
    op.execute("""
        UPDATE permissions SET inheritable = false
        WHERE (resource = 'entities' AND action IN ('create', 'update', 'delete'))
           OR (resource = 'branding')
           OR (resource = 'views')
           OR (resource = 'memberships')
           OR (resource = 'roles' AND action IN ('create', 'update', 'delete', 'assign'))
    """)


def downgrade() -> None:
    op.drop_column('permissions', 'inheritable')
