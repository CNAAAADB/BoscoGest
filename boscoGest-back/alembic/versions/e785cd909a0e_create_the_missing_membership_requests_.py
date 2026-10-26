"""create the missing membership_requests table

Revision ID: e785cd909a0e
Revises: 5d5f6ae82361
Create Date: 2026-08-26 08:58:20.743365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e785cd909a0e'
down_revision: Union[str, Sequence[str], None] = '5d5f6ae82361'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    The model for this table existed but was never imported in
    app/models/__init__.py, so it never reached Base.metadata: create_all did
    not build it for the test-suite, autogenerate could not see it, and no
    migration ever created it. Any database built from migrations was missing
    it entirely, which made self-registration fail with a 500 — the endpoint
    that creates the request could not find the table.
    """
    # Databases predating the migrations were built with create_all while the
    # model was still registered, so they already have the table. Skip rather
    # than fail on those: the point is to reach the same shape either way.
    bind = op.get_bind()
    if sa.inspect(bind).has_table('membership_requests'):
        return

    # The enum can outlive a rolled-back attempt, so create it separately and
    # only if missing, then let create_table reuse it.
    status_enum = postgresql.ENUM(
        'pending', 'accepted', 'rejected',
        name='membership_request_status',
        create_type=False,
    )
    status_enum.create(bind, checkfirst=True)

    op.create_table('membership_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('status', status_enum, nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_membership_requests_entity_status', 'membership_requests', ['entity_id', 'status'], unique=False)
    op.create_index('ix_membership_requests_user', 'membership_requests', ['user_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    if not sa.inspect(op.get_bind()).has_table('membership_requests'):
        return
    op.drop_index('ix_membership_requests_user', table_name='membership_requests')
    op.drop_index('ix_membership_requests_entity_status', table_name='membership_requests')
    op.drop_table('membership_requests')
    postgresql.ENUM(name='membership_request_status').drop(
        op.get_bind(), checkfirst=True
    )
