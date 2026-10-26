"""make users.email and users.phone nullable; add unique index on phone

Email or phone is now sufficient to identify/contact a user (login works with
either). At least one of the two is enforced at the application layer.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-01 13:00:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # email and phone become nullable
    op.execute("ALTER TABLE users ALTER COLUMN email DROP NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN phone DROP NOT NULL")
    # Resolve any duplicate phones (e.g. seed placeholders like '600000000')
    # before adding the unique index: keep the lowest-id row, null the rest.
    op.execute(
        """
        UPDATE users u SET phone = NULL
        WHERE phone IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM users u2
              WHERE u2.phone = u.phone AND u2.id < u.id
          )
        """
    )
    # phone must be unique to identify a user at login (multiple NULLs allowed)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_phone")
    # NOTE: reverting NOT NULL may fail if there are rows with NULL email/phone
    op.execute("ALTER TABLE users ALTER COLUMN phone SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN email SET NOT NULL")
