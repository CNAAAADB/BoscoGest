"""add users:read_sensitive permission

DNI, IBAN, home address and date of birth used to be returned to anyone holding
users:read, despite REQ-USR-01 marking DNI and IBAN as private. They now require
this permission, so it has to exist before the new checks start denying access.

Revision ID: c1a0b2d3e4f5
Revises: b7c8d9e0f1a2
Create Date: 2026-08-25 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1a0b2d3e4f5'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Not inheritable: holding it over a parent entity must not expose the
    # personal data of every member in every entity underneath.
    op.execute(sa.text("""
        INSERT INTO permissions (name, resource, action, description, inheritable, is_active)
        VALUES ('users:read_sensitive', 'users', 'read_sensitive',
                'Read sensitive personal data (DNI, IBAN, address, date of birth)',
                FALSE, TRUE)
        ON CONFLICT (name) DO NOTHING
    """))
    # Granted to the roles that already had unrestricted access, so existing
    # administrators see no change in behaviour.
    op.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name IN ('superadmin', 'admin') AND p.name = 'users:read_sensitive'
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    op.execute(sa.text("""
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE name = 'users:read_sensitive')
    """))
    op.execute(sa.text("DELETE FROM permissions WHERE name = 'users:read_sensitive'"))
