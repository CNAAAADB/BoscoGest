"""add membership_requests table and membership_request_status enum

Revision ID: e1f2a3b4c5d6
Revises: a7b8c9d0e1f2
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create membership_requests table
    op.create_table(
        "membership_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "rejected",
                name="membership_request_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_membership_requests_entity_status",
        "membership_requests",
        ["entity_id", "status"],
    )
    op.create_index(
        "ix_membership_requests_user",
        "membership_requests",
        ["user_id"],
    )

    # Add memberships:review permission to the seeder permissions
    # (only if not already present — idempotent)
    op.execute(
        """
        INSERT INTO permissions (name, resource, action, description, inheritable, is_active)
        SELECT 'memberships_review_permission', 'memberships', 'review',
               'Revisar y gestionar solicitudes de alta en la entidad',
               FALSE, TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM permissions WHERE resource = 'memberships' AND action = 'review'
        );
        """
    )

    # Grant memberships:review to admin and superadmin roles
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name IN ('superadmin', 'admin')
          AND p.resource = 'memberships'
          AND p.action = 'review'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          );
        """
    )


def downgrade() -> None:
    op.drop_index("ix_membership_requests_user", table_name="membership_requests")
    op.drop_index(
        "ix_membership_requests_entity_status", table_name="membership_requests"
    )
    op.drop_table("membership_requests")
    op.execute("DROP TYPE IF EXISTS membership_request_status;")

    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'memberships' AND action = 'review'
        );
        """
    )
    op.execute(
        "DELETE FROM permissions WHERE resource = 'memberships' AND action = 'review';"
    )
