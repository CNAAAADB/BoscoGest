"""activity end date

Revision ID: b7e3c9d2a4f1
Revises: a1b2c3d4e5f6
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e3c9d2a4f1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Añade cuándo termina una actividad, para las que duran varias horas o
    varios días. Nullable: las actividades existentes no tienen fin y siguen
    funcionando igual, y una reunión puntual no lo necesita.
    """
    op.add_column('activities', sa.Column('end_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('activities', 'end_date')
