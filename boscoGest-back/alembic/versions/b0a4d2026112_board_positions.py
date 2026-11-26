"""Entity-scoped appointments for the national/federal/local governing boards.

Revision ID: b0a4d2026112
Revises: f9a1c02b7653
"""
from alembic import op
import sqlalchemy as sa

revision = "b0a4d2026112"
down_revision = "f9a1c02b7653"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "board_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_code", sa.String(length=30), nullable=False),
        sa.Column("custom_title", sa.String(length=80), nullable=True),
        sa.Column("normalized_title", sa.String(length=100), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "entity_id", "normalized_title",
                            name="uq_board_position_per_entity"),
    )
    op.create_index("ix_board_positions_user_id", "board_positions", ["user_id"])
    op.create_index("ix_board_positions_entity_id", "board_positions", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_board_positions_entity_id", table_name="board_positions")
    op.drop_index("ix_board_positions_user_id", table_name="board_positions")
    op.drop_table("board_positions")
