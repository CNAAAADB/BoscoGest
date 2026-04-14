"""Add views:read and branding:read permissions to socio role

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Get socio role id
    socio = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'socio'")
    ).fetchone()
    if not socio:
        return

    socio_id = socio[0]

    # Permissions to add to socio
    perms_to_add = ['views:read', 'branding:read']

    for perm_name in perms_to_add:
        resource, action = perm_name.split(':')
        perm = conn.execute(
            sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action}
        ).fetchone()

        if not perm:
            continue

        # Check if already assigned
        existing = conn.execute(
            sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
            ),
            {"rid": socio_id, "pid": perm[0]}
        ).fetchone()

        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
                ),
                {"rid": socio_id, "pid": perm[0]}
            )


def downgrade() -> None:
    conn = op.get_bind()

    socio = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'socio'")
    ).fetchone()
    if not socio:
        return

    socio_id = socio[0]

    for perm_name in ['views:read', 'branding:read']:
        resource, action = perm_name.split(':')
        perm = conn.execute(
            sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action}
        ).fetchone()
        if perm:
            conn.execute(
                sa.text(
                    "DELETE FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
                ),
                {"rid": socio_id, "pid": perm[0]}
            )
