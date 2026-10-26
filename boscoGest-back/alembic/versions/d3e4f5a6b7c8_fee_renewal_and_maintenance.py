"""fee renewal policy + maintenance runs + fees:maintenance permission

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-31 16:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Renewal / due-date / reminder policy on fees
    op.execute("ALTER TABLE fees ADD COLUMN auto_renew BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE fees ADD COLUMN due_days INTEGER NOT NULL DEFAULT 30")
    op.execute("ALTER TABLE fees ADD COLUMN reminder_days INTEGER NOT NULL DEFAULT 7")
    op.execute("ALTER TABLE fee_assignments ADD COLUMN reminder_sent BOOLEAN NOT NULL DEFAULT FALSE")

    # Maintenance run log
    op.execute("CREATE TYPE fee_maintenance_status AS ENUM ('success', 'error')")
    op.execute("CREATE TYPE fee_maintenance_trigger AS ENUM ('scheduled', 'manual')")
    op.execute("""
        CREATE TABLE fee_maintenance_runs (
            id SERIAL PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMPTZ,
            status fee_maintenance_status NOT NULL DEFAULT 'success',
            trigger fee_maintenance_trigger NOT NULL DEFAULT 'scheduled',
            triggered_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            overdue_count INTEGER NOT NULL DEFAULT 0,
            reminded_count INTEGER NOT NULL DEFAULT 0,
            renewed_count INTEGER NOT NULL DEFAULT 0,
            details JSON,
            error TEXT
        )
    """)

    # Permission for the maintenance/monitoring view (non-inheritable, global)
    op.execute(sa.text("""
        INSERT INTO permissions (name, resource, action, inheritable, is_active)
        VALUES ('fees:maintenance', 'fees', 'maintenance', FALSE, TRUE)
        ON CONFLICT (name) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'superadmin' AND p.name = 'fees:maintenance'
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE name = 'fees:maintenance')
    """)
    op.execute("DELETE FROM permissions WHERE name = 'fees:maintenance'")
    op.execute("DROP TABLE IF EXISTS fee_maintenance_runs")
    op.execute("DROP TYPE IF EXISTS fee_maintenance_trigger")
    op.execute("DROP TYPE IF EXISTS fee_maintenance_status")
    op.execute("ALTER TABLE fee_assignments DROP COLUMN reminder_sent")
    op.execute("ALTER TABLE fees DROP COLUMN reminder_days")
    op.execute("ALTER TABLE fees DROP COLUMN due_days")
    op.execute("ALTER TABLE fees DROP COLUMN auto_renew")
