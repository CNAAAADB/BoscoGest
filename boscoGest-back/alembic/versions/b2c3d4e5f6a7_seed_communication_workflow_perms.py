"""seed_communication_workflow_permissions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-15 18:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
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
    """Seed communications:publish and communications:review permissions."""
    conn = op.get_bind()

    # Clean up any partial data from a previous failed attempt
    existing = conn.execute(
        sa.select(permissions_table.c.id).where(
            sa.and_(
                permissions_table.c.resource == "communications",
                permissions_table.c.action.in_(["publish", "review"]),
            )
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

    actions = ["publish", "review"]
    new_permission_ids = []

    for action in actions:
        result = conn.execute(
            permissions_table.insert()
            .values(
                name=f"communications_{action}_permission",
                resource="communications",
                action=action,
                is_active=True,
                inheritable=True,
            )
            .returning(permissions_table.c.id)
        )
        perm_id = result.scalar()
        new_permission_ids.append(perm_id)

    # Find existing roles
    superadmin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "superadmin")
    ).scalar()
    admin = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "admin")
    ).scalar()

    # Assign publish and review permissions to superadmin and admin only
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


def downgrade() -> None:
    """Remove communications publish/review permissions."""
    conn = op.get_bind()

    result = conn.execute(
        sa.select(permissions_table.c.id).where(
            sa.and_(
                permissions_table.c.resource == "communications",
                permissions_table.c.action.in_(["publish", "review"]),
            )
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
