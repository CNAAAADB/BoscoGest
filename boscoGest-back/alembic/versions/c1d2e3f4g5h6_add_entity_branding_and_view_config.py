"""add_entity_branding_and_view_config

Revision ID: c1d2e3f4g5h6
Revises: b0fa532b8859
Create Date: 2026-02-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, Sequence[str], None] = 'b0fa532b8859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Crear tabla entity_brandings
    op.create_table(
        'entity_brandings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('subdomain', sa.String(length=50), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('primary_color', sa.String(length=7), nullable=False, server_default='#1976d2'),
        sa.Column('secondary_color', sa.String(length=7), nullable=False, server_default='#424242'),
        sa.Column('accent_color', sa.String(length=7), nullable=False, server_default='#ff4081'),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('tagline', sa.String(length=200), nullable=True),
        sa.Column('custom_footer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entity_brandings_entity_id'), 'entity_brandings', ['entity_id'], unique=True)
    op.create_index(op.f('ix_entity_brandings_subdomain'), 'entity_brandings', ['subdomain'], unique=True)

    # Crear tabla entity_view_configs
    op.create_table(
        'entity_view_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('view_name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_id', 'view_name', name='uq_entity_view')
    )
    op.create_index(op.f('ix_entity_view_configs_entity_id'), 'entity_view_configs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_entity_view_configs_view_name'), 'entity_view_configs', ['view_name'], unique=False)

    # Añadir permisos para branding y view_config
    op.execute("""
        INSERT INTO permissions (name, resource, action, description, is_active)
        VALUES
            ('branding:read', 'branding', 'read', 'Ver configuración de branding', true),
            ('branding:update', 'branding', 'update', 'Modificar configuración de branding', true),
            ('views:read', 'views', 'read', 'Ver configuración de vistas', true),
            ('views:update', 'views', 'update', 'Modificar configuración de vistas', true)
        ON CONFLICT (name) DO NOTHING;
    """)

    # Asignar permisos al rol superadmin
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'superadmin'
        AND p.name IN ('branding:read', 'branding:update', 'views:read', 'views:update')
        ON CONFLICT DO NOTHING;
    """)

    # Asignar permisos al rol admin
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'admin'
        AND p.name IN ('branding:read', 'branding:update', 'views:read', 'views:update')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar permisos de role_permissions
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE name IN ('branding:read', 'branding:update', 'views:read', 'views:update')
        );
    """)

    # Eliminar permisos
    op.execute("""
        DELETE FROM permissions
        WHERE name IN ('branding:read', 'branding:update', 'views:read', 'views:update');
    """)

    # Eliminar tablas
    op.drop_index(op.f('ix_entity_view_configs_view_name'), table_name='entity_view_configs')
    op.drop_index(op.f('ix_entity_view_configs_entity_id'), table_name='entity_view_configs')
    op.drop_table('entity_view_configs')

    op.drop_index(op.f('ix_entity_brandings_subdomain'), table_name='entity_brandings')
    op.drop_index(op.f('ix_entity_brandings_entity_id'), table_name='entity_brandings')
    op.drop_table('entity_brandings')
