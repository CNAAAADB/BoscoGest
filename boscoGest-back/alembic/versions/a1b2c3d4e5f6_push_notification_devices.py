"""device tokens and push preference

Revision ID: a1b2c3d4e5f6
Revises: f51a9767e5c6
Create Date: 2026-09-23 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f51a9767e5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Guarda los dispositivos a los que se puede enviar una notificación push, y
    añade la preferencia que permite apagarlas por tipo de evento.

    El token es único y no el usuario: una persona puede tener el móvil y la
    tablet, y el mismo aparato puede cambiar de dueño —un móvil compartido, o
    alguien que cierra sesión y entra con otra cuenta—, en cuyo caso el
    registro se reasigna en vez de duplicarse.
    """
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=10), nullable=False),
        # NOT NULL para que coincidan con el modelo, que los declara
        # Mapped[datetime] y no Mapped[Optional[datetime]]. La comprobación de
        # deriva del CI compara ambos y no perdona la diferencia.
        sa.Column(
            'created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False
        ),
        sa.Column(
            'last_seen_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_device_token'),
    )
    op.create_index(
        op.f('ix_device_tokens_user_id'), 'device_tokens', ['user_id'], unique=False
    )

    # Por defecto activa, igual que el aviso in-app: una preferencia que nace
    # apagada no la enciende casi nadie, y la función no existiría en la
    # práctica. Se apaga por tipo de evento, o retirando el permiso al sistema.
    op.add_column(
        'notification_preferences',
        sa.Column(
            'push_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('notification_preferences', 'push_enabled')
    op.drop_index(op.f('ix_device_tokens_user_id'), table_name='device_tokens')
    op.drop_table('device_tokens')
