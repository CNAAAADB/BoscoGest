"""add bulk_upload_jobs.target_role_id

The role is now chosen in the UI (conditioned on the selected association) and
assigned to every user created from the CSV, so the job stores the selected
role instead of reading a role_id column from each row.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-06-04 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE bulk_upload_jobs "
        "ADD COLUMN target_role_id INTEGER "
        "REFERENCES roles(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE bulk_upload_jobs DROP COLUMN target_role_id")
