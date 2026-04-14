"""seed_notification_permissions

Revision ID: bba396d52438
Revises: 20a281caf5c1
Create Date: 2026-02-15 15:16:34.550174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bba396d52438'
down_revision: Union[str, Sequence[str], None] = '20a281caf5c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables referenced for data operations
permissions_table = sa.table(
    "permissions",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("inheritable", sa.Boolean),
)

role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.Integer),
    sa.column("permission_id", sa.Integer),
)

roles_table = sa.table(
    "roles",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)


def upgrade() -> None:
    """Seed notification permissions and assign them to existing roles."""
    conn = op.get_bind()

    # Clean up any partial data from a previous failed attempt
    existing = conn.execute(
        sa.select(permissions_table.c.id).where(
            permissions_table.c.resource == "notifications"
        )
    )
    old_ids = [row[0] for row in existing]
    if old_ids:
        conn.execute(
            role_permissions_table.delete().where(
                role_permissions_table.c.permission_id.in_(old_ids)
            )
        )
        conn.execute(
            permissions_table.delete().where(
                permissions_table.c.id.in_(old_ids)
            )
        )

    actions = ["create", "list", "read", "update", "delete", "assign", "manage"]

    # Create notification permissions
    new_permission_ids = []
    read_only_ids = []

    for action in actions:
        result = conn.execute(
            permissions_table.insert()
            .values(
                name=f"notifications_{action}_permission",
                resource="notifications",
                action=action,
                is_active=True,
                inheritable=True,
            )
            .returning(permissions_table.c.id)
        )
        perm_id = result.scalar()
        new_permission_ids.append(perm_id)
        if action in ("read", "list"):
            read_only_ids.append(perm_id)

    # Find existing roles
    superadmin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "superadmin")
    ).scalar()
    admin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "admin")
    ).scalar()
    socio = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "socio")
    ).scalar()

    # Assign all permissions to superadmin and admin
    for perm_id in new_permission_ids:
        if superadmin:
            conn.execute(
                role_permissions_table.insert().values(
                    role_id=superadmin, permission_id=perm_id
                )
            )
        if admin:
            conn.execute(
                role_permissions_table.insert().values(
                    role_id=admin, permission_id=perm_id
                )
            )

    # Assign read/list permissions to socio
    for perm_id in read_only_ids:
        if socio:
            conn.execute(
                role_permissions_table.insert().values(
                    role_id=socio, permission_id=perm_id
                )
            )


def downgrade() -> None:
    """Remove notification permissions."""
    conn = op.get_bind()

    # Find notification permission IDs
    result = conn.execute(
        sa.select(permissions_table.c.id).where(
            permissions_table.c.resource == "notifications"
        )
    )
    perm_ids = [row[0] for row in result]

    if perm_ids:
        # Remove role_permissions associations
        conn.execute(
            role_permissions_table.delete().where(
                role_permissions_table.c.permission_id.in_(perm_ids)
            )
        )
        # Remove permissions
        conn.execute(
            permissions_table.delete().where(
                permissions_table.c.id.in_(perm_ids)
            )
        )
