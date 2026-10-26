"""add_bulk_upload_jobs

Revision ID: e62470d4b4ff
Revises: 05e2e0adb44f
Create Date: 2026-04-26 09:32:53.795818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e62470d4b4ff'
down_revision: Union[str, Sequence[str], None] = '05e2e0adb44f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS bulk_upload_jobs (
            id SERIAL PRIMARY KEY,
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            csv_filename VARCHAR(255) NOT NULL,
            csv_content BYTEA NOT NULL,
            total_rows INTEGER,
            processed_rows INTEGER NOT NULL DEFAULT 0,
            successful INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            errors JSONB,
            created_users JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_created_by_id ON bulk_upload_jobs (created_by_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_status ON bulk_upload_jobs (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_created_at ON bulk_upload_jobs (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bulk_upload_jobs")
