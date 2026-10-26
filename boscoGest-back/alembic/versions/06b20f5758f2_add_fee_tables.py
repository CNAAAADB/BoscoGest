"""add_fee_tables

Revision ID: 06b20f5758f2
Revises: e62470d4b4ff
Create Date: 2026-04-26 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '06b20f5758f2'
down_revision: Union[str, Sequence[str], None] = 'e62470d4b4ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── fee_configs ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS fee_configs (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            amount NUMERIC(10, 2) NOT NULL,
            valid_from DATE NOT NULL,
            valid_until DATE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fee_configs_entity_id ON fee_configs (entity_id)")

    # ── fee_assignments ───────────────────────────────────────────────────────
    op.execute("CREATE TYPE fee_assignment_status AS ENUM ('pending', 'paid', 'overdue', 'cancelled')")
    op.execute("""
        CREATE TABLE IF NOT EXISTS fee_assignments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            fee_config_id INTEGER REFERENCES fee_configs(id) ON DELETE SET NULL,
            period VARCHAR(20) NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status fee_assignment_status NOT NULL DEFAULT 'pending',
            due_date DATE,
            paid_at TIMESTAMPTZ,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_fee_assignment_user_entity_period UNIQUE (user_id, entity_id, period)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fee_assignments_entity_period ON fee_assignments (entity_id, period)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fee_assignments_user ON fee_assignments (user_id)")

    # ── Permissions seed ──────────────────────────────────────────────────────
    fee_permissions = [
        ("fees:list",   "fees", "list",   True,  True),   # (name, resource, action, inheritable, is_active)
        ("fees:read",   "fees", "read",   True,  True),
        ("fees:create", "fees", "create", False, True),
        ("fees:manage", "fees", "manage", True,  True),
    ]

    for name, resource, action, inheritable, is_active in fee_permissions:
        op.execute(sa.text("""
            INSERT INTO permissions (name, resource, action, inheritable, is_active)
            VALUES (:name, :resource, :action, :inheritable, :is_active)
            ON CONFLICT (name) DO NOTHING
        """).bindparams(
            name=name, resource=resource, action=action,
            inheritable=inheritable, is_active=is_active
        ))

    # Assign all fees permissions to superadmin and admin
    for name, _, _, _, _ in fee_permissions:
        op.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name IN ('superadmin', 'admin')
              AND p.name = :name
            ON CONFLICT DO NOTHING
        """).bindparams(name=name))

    # Assign fees:list and fees:read to socio
    for name in ("fees:list", "fees:read"):
        op.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'socio'
              AND p.name = :name
            ON CONFLICT DO NOTHING
        """).bindparams(name=name))


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'fees'
        )
    """)
    op.execute("DELETE FROM permissions WHERE resource = 'fees'")
    op.execute("DROP TABLE IF EXISTS fee_assignments")
    op.execute("DROP TYPE IF EXISTS fee_assignment_status")
    op.execute("DROP TABLE IF EXISTS fee_configs")
