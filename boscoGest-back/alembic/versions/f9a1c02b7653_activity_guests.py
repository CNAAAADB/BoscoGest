"""Count non-member guests in activity registrations."""
from alembic import op
import sqlalchemy as sa

revision = "f9a1c02b7653"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("allow_guests", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("activity_registrations", sa.Column("guest_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("activity_registrations", "guest_count")
    op.drop_column("activities", "allow_guests")
