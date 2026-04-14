"""alter_magazines_make_collection_issue_nullable

Revision ID: b0fa532b8859
Revises: f1a02d92a91e
Create Date: 2025-12-03 19:14:20.422282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0fa532b8859'
down_revision: Union[str, Sequence[str], None] = 'f1a02d92a91e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make collection column nullable
    op.alter_column('magazines', 'collection',
                    existing_type=sa.String(length=100),
                    nullable=True)

    # Make issue_number column nullable
    op.alter_column('magazines', 'issue_number',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Make collection column NOT NULL
    op.alter_column('magazines', 'collection',
                    existing_type=sa.String(length=100),
                    nullable=False)

    # Make issue_number column NOT NULL
    op.alter_column('magazines', 'issue_number',
                    existing_type=sa.Integer(),
                    nullable=False)
