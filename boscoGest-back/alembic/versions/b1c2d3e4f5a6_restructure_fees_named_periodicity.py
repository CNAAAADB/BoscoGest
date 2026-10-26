"""restructure fees: named fees per entity + periodicity on assignments

Revision ID: b1c2d3e4f5a6
Revises: 06b20f5758f2
Create Date: 2026-05-31 12:00:00.000000

Two-level model:
- fees: a named fee belonging to a single entity (an entity can have several).
- fee_configs: amount versions (history) of a fee (valid_from/valid_until).
- fee_assignments: now reference a fee and carry a periodicity.

NOTE: this drops the previous fee_configs/fee_assignments (incompatible schema).
Existing rows are discarded by design (dev data).
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '06b20f5758f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Drop old tables (incompatible) ────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS fee_assignments")
    op.execute("DROP TABLE IF EXISTS fee_configs")

    # ── fees (named fee per entity) ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE fees (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_fees_entity_id ON fees (entity_id)")

    # ── fee_configs (amount versions / history of a fee) ──────────────────────
    op.execute("""
        CREATE TABLE fee_configs (
            id SERIAL PRIMARY KEY,
            fee_id INTEGER NOT NULL REFERENCES fees(id) ON DELETE CASCADE,
            amount NUMERIC(10, 2) NOT NULL,
            valid_from DATE NOT NULL,
            valid_until DATE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_fee_configs_fee_id ON fee_configs (fee_id)")

    # ── fee_assignments (now reference a fee + periodicity) ───────────────────
    op.execute("CREATE TYPE fee_periodicity AS ENUM ('weekly', 'monthly', 'quarterly', 'four_monthly', 'biannual', 'annual')")
    op.execute("""
        CREATE TABLE fee_assignments (
            id SERIAL PRIMARY KEY,
            fee_id INTEGER NOT NULL REFERENCES fees(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            fee_config_id INTEGER REFERENCES fee_configs(id) ON DELETE SET NULL,
            periodicity fee_periodicity NOT NULL,
            period VARCHAR(20) NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status fee_assignment_status NOT NULL DEFAULT 'pending',
            due_date DATE,
            paid_at TIMESTAMPTZ,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_fee_assignment_user_fee_period UNIQUE (user_id, fee_id, period)
        )
    """)
    op.execute("CREATE INDEX ix_fee_assignments_fee_id ON fee_assignments (fee_id)")
    op.execute("CREATE INDEX ix_fee_assignments_entity_period ON fee_assignments (entity_id, period)")
    op.execute("CREATE INDEX ix_fee_assignments_user ON fee_assignments (user_id)")


def downgrade() -> None:
    # Recreate the previous (entity-based) schema, empty.
    op.execute("DROP TABLE IF EXISTS fee_assignments")
    op.execute("DROP TYPE IF EXISTS fee_periodicity")
    op.execute("DROP TABLE IF EXISTS fee_configs")
    op.execute("DROP TABLE IF EXISTS fees")

    op.execute("""
        CREATE TABLE fee_configs (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            amount NUMERIC(10, 2) NOT NULL,
            valid_from DATE NOT NULL,
            valid_until DATE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_fee_configs_entity_id ON fee_configs (entity_id)")
    op.execute("""
        CREATE TABLE fee_assignments (
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
    op.execute("CREATE INDEX ix_fee_assignments_entity_period ON fee_assignments (entity_id, period)")
    op.execute("CREATE INDEX ix_fee_assignments_user ON fee_assignments (user_id)")
