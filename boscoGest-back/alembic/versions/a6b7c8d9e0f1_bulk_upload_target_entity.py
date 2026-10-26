"""add bulk_upload_jobs.target_entity_id

The association is now chosen in the UI and applied to every CSV row, so the
job stores the selected entity instead of reading it from each row.

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-01 13:30:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE bulk_upload_jobs "
        "ADD COLUMN target_entity_id INTEGER "
        "REFERENCES entities(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE bulk_upload_jobs DROP COLUMN target_entity_id")
