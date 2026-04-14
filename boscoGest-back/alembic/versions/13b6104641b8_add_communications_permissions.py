"""add_communications_permissions

Revision ID: 13b6104641b8
Revises: ghi456jkl789
Create Date: 2025-11-16 18:52:13.456072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13b6104641b8'
down_revision: Union[str, Sequence[str], None] = 'ghi456jkl789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add communications permissions to all roles."""
    bind = op.get_bind()

    # Get role IDs
    result = bind.execute(sa.text("SELECT id, name FROM roles WHERE name IN ('superadmin', 'admin', 'socio')"))
    roles = {row[1]: row[0] for row in result}

    # Define communications permissions
    permission_actions = ["create", "list", "read", "update", "delete", "assign", "manage", "edit"]
    resource = "communications"

    created_permissions = []
    read_only_permissions = []

    # Create permissions
    for action in permission_actions:
        permission_name = f"{resource}_{action}_permission"

        # Insert permission
        result = bind.execute(
            sa.text("""
                INSERT INTO permissions (name, resource, action, is_active)
                VALUES (:name, :resource, :action, true)
                RETURNING id
            """),
            {"name": permission_name, "resource": resource, "action": action}
        )
        permission_id = result.fetchone()[0]
        created_permissions.append(permission_id)

        # Track read-only permissions for socio role
        if action in ["read", "list"]:
            read_only_permissions.append(permission_id)

    # Associate all permissions to superadmin and admin roles
    for permission_id in created_permissions:
        if 'superadmin' in roles:
            bind.execute(
                sa.text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                """),
                {"role_id": roles['superadmin'], "permission_id": permission_id}
            )
        if 'admin' in roles:
            bind.execute(
                sa.text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                """),
                {"role_id": roles['admin'], "permission_id": permission_id}
            )

    # Associate read-only permissions to socio role
    if 'socio' in roles:
        for permission_id in read_only_permissions:
            bind.execute(
                sa.text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                """),
                {"role_id": roles['socio'], "permission_id": permission_id}
            )


def downgrade() -> None:
    """Remove communications permissions."""
    bind = op.get_bind()

    # Delete role-permission associations for communications
    bind.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE resource = 'communications'
            )
        """)
    )

    # Delete communications permissions
    bind.execute(
        sa.text("DELETE FROM permissions WHERE resource = 'communications'")
    )
