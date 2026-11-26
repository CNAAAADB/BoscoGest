"""Unify the statistics view switch at the Superentity root.

Revision ID: b0a4d2026113
Revises: b0a4d2026112

An already enabled level-2+ statistics view is preserved as an enabled root
switch; other per-entity switches stop controlling the feature.
"""
from alembic import op
import sqlalchemy as sa

revision = "b0a4d2026113"
down_revision = "b0a4d2026112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO entity_view_configs
          (entity_id, view_name, display_name, is_enabled, display_order,
           icon, created_at, updated_at)
        SELECT e.id, 'member_stats', 'Estadísticas de socios', false, 2,
               'insights', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM entities AS e
        WHERE e.level = 1
          AND NOT EXISTS (
              SELECT 1 FROM entity_view_configs AS v
              WHERE v.entity_id = e.id AND v.view_name = 'member_stats'
          )
    """))
    op.execute(sa.text("""
        UPDATE entity_view_configs
        SET is_enabled = true, updated_at = CURRENT_TIMESTAMP
        WHERE view_name = 'member_stats'
          AND entity_id IN (SELECT id FROM entities WHERE level = 1)
          AND EXISTS (
              SELECT 1 FROM entity_view_configs AS child_view
              JOIN entities AS child_entity
                ON child_entity.id = child_view.entity_id
              WHERE child_entity.level >= 2
                AND child_view.view_name = 'member_stats'
                AND child_view.is_enabled = true
          )
    """))


def downgrade() -> None:
    # Do not undo user choices or erase the global setting after a deployment.
    pass
