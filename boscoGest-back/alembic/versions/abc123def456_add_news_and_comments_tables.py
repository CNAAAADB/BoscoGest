"""add_news_and_comments_tables

Revision ID: abc123def456
Revises: 6579678ddc26
Create Date: 2025-11-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = '6579678ddc26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create news table
    op.create_table('news',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_id'), 'news', ['id'], unique=False)

    # Create comments table
    op.create_table('comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('news_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['news_id'], ['news.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)

    # Create news permissions
    op.execute("""
        INSERT INTO permissions (name, resource, action, description, is_active)
        VALUES
            ('Create News', 'news', 'create', 'Permission to create news', true),
            ('Read News', 'news', 'read', 'Permission to read news', true),
            ('Edit News', 'news', 'edit', 'Permission to edit news', true),
            ('Delete News', 'news', 'delete', 'Permission to delete news', true),
            ('Manage All News', 'news', 'manage_all', 'Full access to manage all news', true)
    """)

    # Create comment permissions
    op.execute("""
        INSERT INTO permissions (name, resource, action, description, is_active)
        VALUES
            ('Create Comment', 'comment', 'create', 'Permission to create comments', true),
            ('Read Comment', 'comment', 'read', 'Permission to read comments', true),
            ('Edit Comment', 'comment', 'edit', 'Permission to edit comments', true),
            ('Delete Comment', 'comment', 'delete', 'Permission to delete comments', true),
            ('Manage All Comments', 'comment', 'manage_all', 'Full access to manage all comments', true)
    """)

    # Assign news permissions to superadmin role
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'superadmin'
        AND p.resource IN ('news', 'comment')
    """)

    # Assign news create/edit/delete permissions to admin role
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'admin'
        AND p.resource = 'news'
        AND p.action IN ('create', 'edit', 'delete', 'read')
    """)

    # Assign comment create/read/edit/delete permissions to admin and socio roles
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name IN ('admin', 'socio')
        AND p.resource = 'comment'
        AND p.action IN ('create', 'read')
    """)

    # Assign comment edit/delete to admin only
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'admin'
        AND p.resource = 'comment'
        AND p.action IN ('edit', 'delete')
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove permission assignments
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource IN ('news', 'comment')
        )
    """)

    # Remove permissions
    op.execute("DELETE FROM permissions WHERE resource IN ('news', 'comment')")

    # Drop tables
    op.drop_index(op.f('ix_comments_id'), table_name='comments')
    op.drop_table('comments')
    op.drop_index(op.f('ix_news_id'), table_name='news')
    op.drop_table('news')
