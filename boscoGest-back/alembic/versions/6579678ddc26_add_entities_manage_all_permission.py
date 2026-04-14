"""add_entities_manage_all_permission

Revision ID: 6579678ddc26
Revises: 53f48033ff06
Create Date: 2025-11-01 17:44:12.495804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6579678ddc26'
down_revision: Union[str, Sequence[str], None] = '53f48033ff06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create connection
    connection = op.get_bind()

    # Insert the new permission
    result = connection.execute(
        sa.text("""
            INSERT INTO permissions (name, resource, action, description, is_active)
            VALUES ('entities_manage_all_permission', 'entities', 'manage_all',
                    'Permission to manage all entities regardless of membership', TRUE)
            RETURNING id
        """)
    )
    permission_id = result.fetchone()[0]

    # Get superadmin role ID
    result = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'superadmin'")
    )
    superadmin_role_id = result.fetchone()[0]

    # Associate the permission with superadmin role
    connection.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (:role_id, :permission_id)
        """),
        {"role_id": superadmin_role_id, "permission_id": permission_id}
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Create connection
    connection = op.get_bind()

    # Remove association from role_permissions
    connection.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE resource = 'entities' AND action = 'manage_all'
            )
        """)
    )

    # Delete the permission
    connection.execute(
        sa.text("""
            DELETE FROM permissions
            WHERE resource = 'entities' AND action = 'manage_all'
        """)
    )
