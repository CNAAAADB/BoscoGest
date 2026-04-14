"""add_resources_and_resource_categories

Revision ID: 1409b0fe2f7b
Revises: d2e3f4g5h6i7
Create Date: 2026-02-14 09:18:50.900366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1409b0fe2f7b'
down_revision: Union[str, None] = 'd2e3f4g5h6i7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum outside of table to control creation
resourcetype_enum = postgresql.ENUM('link', 'document', 'image', 'video', name='resourcetype', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    # Create resource_categories table
    op.create_table(
        'resource_categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
    )

    # Create resourcetype enum only if it doesn't exist
    op.execute("DO $$ BEGIN CREATE TYPE resourcetype AS ENUM ('link', 'document', 'image', 'video'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")

    # Create resources table
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_type', resourcetype_enum, nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('resource_categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resources')
    op.drop_table('resource_categories')
    op.execute("DROP TYPE IF EXISTS resourcetype")
