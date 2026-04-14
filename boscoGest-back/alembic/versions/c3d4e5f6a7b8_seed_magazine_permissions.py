"""seed_magazine_permissions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
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
    """Seed magazine permissions (create, list, read, update, delete) for all roles."""
    conn = op.get_bind()

    # Clean up any existing magazine permissions (from standalone script)
    existing = conn.execute(
        sa.select(permissions_table.c.id).where(
            permissions_table.c.resource == "magazines"
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

    # Create magazine permissions (all inheritable — manageable from parent entities)
    actions = ["create", "list", "read", "update", "delete"]
    all_perm_ids = []
    read_perm_ids = []

    for action in actions:
        result = conn.execute(
            permissions_table.insert()
            .values(
                name=f"magazines_{action}_permission",
                resource="magazines",
                action=action,
                is_active=True,
                inheritable=True,
            )
            .returning(permissions_table.c.id)
        )
        perm_id = result.scalar()
        all_perm_ids.append(perm_id)
        if action in ("list", "read"):
            read_perm_ids.append(perm_id)

    # Find roles
    superadmin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "superadmin")
    ).scalar()
    admin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "admin")
    ).scalar()
    socio = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "socio")
    ).scalar()

    # superadmin and admin get all magazine permissions
    for perm_id in all_perm_ids:
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

    # socio gets read and list only
    for perm_id in read_perm_ids:
        if socio:
            conn.execute(
                role_permissions_table.insert().values(
                    role_id=socio, permission_id=perm_id
                )
            )


def downgrade() -> None:
    """Remove magazine permissions."""
    conn = op.get_bind()

    result = conn.execute(
        sa.select(permissions_table.c.id).where(
            permissions_table.c.resource == "magazines"
        )
    )
    perm_ids = [row[0] for row in result]

    if perm_ids:
        conn.execute(
            role_permissions_table.delete().where(
                role_permissions_table.c.permission_id.in_(perm_ids)
            )
        )
        conn.execute(
            permissions_table.delete().where(
                permissions_table.c.id.in_(perm_ids)
            )
        )
