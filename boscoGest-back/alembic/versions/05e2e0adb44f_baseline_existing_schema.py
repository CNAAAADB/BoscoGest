"""baseline: full core schema

Creates every core table of BoscoGest from an empty database. Previously this
revision was an empty stub, which meant `alembic upgrade head` against a clean
database produced no schema at all — the tables only ever existed because the
test-suite called `Base.metadata.create_all()`. Reconstructed by reflecting the
schema as of this revision, so the migrations that follow still apply on top
unchanged.

Revision ID: 05e2e0adb44f
Revises:
Create Date: 2026-04-26 09:32:45.964785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '05e2e0adb44f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the core schema."""
    op.create_table('entities',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('level', sa.INTEGER(), nullable=False),
    sa.Column('parent_id', sa.INTEGER(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['entities.id'], name='entities_parent_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='entities_pkey')
    )
    op.create_index('ix_entities_name', 'entities', ['name'], unique=True)
    op.create_table('groups',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.PrimaryKeyConstraint('id', name='groups_pkey')
    )
    op.create_index('ix_groups_name', 'groups', ['name'], unique=True)
    op.create_table('permissions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('resource', sa.VARCHAR(length=100), nullable=False),
    sa.Column('action', sa.VARCHAR(length=50), nullable=False),
    sa.Column('conditions', postgresql.JSON(), nullable=True),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('inheritable', sa.BOOLEAN(), nullable=False),
    sa.PrimaryKeyConstraint('id', name='permissions_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)
    op.create_table('revoked_tokens',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('jti', sa.VARCHAR(length=255), nullable=False),
    sa.Column('revoked_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id', name='revoked_tokens_pkey')
    )
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'], unique=True)
    op.create_table('roles',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.PrimaryKeyConstraint('id', name='roles_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('email', sa.VARCHAR(length=100), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('must_change_password', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('surname', sa.VARCHAR(length=100), nullable=False),
    sa.Column('phone', sa.VARCHAR(length=20), nullable=False),
    sa.Column('address', sa.TEXT(), nullable=True),
    sa.Column('birthdate', sa.DATE(), nullable=False),
    sa.Column('dni', sa.VARCHAR(length=20), nullable=False),
    sa.Column('photo', sa.TEXT(), nullable=True),
    sa.Column('iban', sa.VARCHAR(length=34), nullable=True),
    sa.Column('size', sa.VARCHAR(length=10), nullable=True),
    sa.Column('hobbies', sa.TEXT(), nullable=True),
    sa.Column('job_position', sa.VARCHAR(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id', name='users_pkey'),
    sa.UniqueConstraint('dni', name='users_dni_key', postgresql_nulls_not_distinct=False)
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table('activities',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=False),
    sa.Column('image_url', sa.VARCHAR(), nullable=True),
    sa.Column('date', postgresql.TIMESTAMP(), nullable=False),
    sa.Column('capacity', sa.INTEGER(), nullable=False),
    sa.Column('price', sa.DOUBLE_PRECISION(precision=53), nullable=True),
    sa.Column('allow_waitlist', sa.BOOLEAN(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=True),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('created_by_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='activities_created_by_id_fkey'),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='activities_entity_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='activities_pkey')
    )
    op.create_index('ix_activities_id', 'activities', ['id'], unique=False)
    op.create_table('audit_logs',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('action', sa.VARCHAR(length=50), nullable=False),
    sa.Column('resource_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('resource_id', sa.INTEGER(), nullable=True),
    sa.Column('details', postgresql.JSON(), nullable=True),
    sa.Column('ip_address', sa.VARCHAR(length=45), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='audit_logs_user_id_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name='audit_logs_pkey')
    )
    op.create_table('chat_conversations',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('type', postgresql.ENUM('direct', 'group', name='conversation_type'), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=True),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('avatar_url', sa.VARCHAR(length=500), nullable=True),
    sa.Column('created_by_id', sa.INTEGER(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='chat_conversations_created_by_id_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name='chat_conversations_pkey')
    )
    op.create_table('communications',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('image_url', sa.VARCHAR(), nullable=True),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('created_by_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('status', sa.VARCHAR(length=20), nullable=False),
    sa.Column('published_at', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='communications_created_by_id_fkey'),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='communications_entity_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='communications_pkey')
    )
    op.create_index('ix_communications_id', 'communications', ['id'], unique=False)
    op.create_table('entity_brandings',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('subdomain', sa.VARCHAR(length=50), nullable=True),
    sa.Column('logo_url', sa.VARCHAR(length=500), nullable=True),
    sa.Column('primary_color', sa.VARCHAR(length=7), nullable=False),
    sa.Column('secondary_color', sa.VARCHAR(length=7), nullable=False),
    sa.Column('accent_color', sa.VARCHAR(length=7), nullable=False),
    sa.Column('display_name', sa.VARCHAR(length=100), nullable=True),
    sa.Column('tagline', sa.VARCHAR(length=200), nullable=True),
    sa.Column('custom_footer', sa.TEXT(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='entity_brandings_entity_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='entity_brandings_pkey'),
    sa.UniqueConstraint('subdomain', name='entity_brandings_subdomain_key', postgresql_nulls_not_distinct=False)
    )
    op.create_index('ix_entity_brandings_entity_id', 'entity_brandings', ['entity_id'], unique=True)
    op.create_table('entity_roles',
    sa.Column('entity_id', sa.INTEGER(), nullable=True),
    sa.Column('role_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='entity_roles_entity_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='entity_roles_role_id_fkey', ondelete='CASCADE')
    )
    op.create_table('entity_view_configs',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('view_name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('display_name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('is_enabled', sa.BOOLEAN(), nullable=False),
    sa.Column('display_order', sa.INTEGER(), nullable=False),
    sa.Column('icon', sa.VARCHAR(length=50), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='entity_view_configs_entity_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='entity_view_configs_pkey'),
    sa.UniqueConstraint('entity_id', 'view_name', name='uq_entity_view', postgresql_nulls_not_distinct=False)
    )
    op.create_index('ix_entity_view_configs_entity_id', 'entity_view_configs', ['entity_id'], unique=False)
    op.create_index('ix_entity_view_configs_view_name', 'entity_view_configs', ['view_name'], unique=False)
    op.create_table('group_roles',
    sa.Column('group_id', sa.INTEGER(), nullable=True),
    sa.Column('role_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name='group_roles_group_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='group_roles_role_id_fkey', ondelete='CASCADE')
    )
    op.create_table('magazines',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=200), nullable=False),
    sa.Column('collection', sa.VARCHAR(length=100), nullable=True),
    sa.Column('issue_number', sa.INTEGER(), nullable=True),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('file_path', sa.VARCHAR(length=500), nullable=False),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='magazines_entity_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='magazines_pkey')
    )
    op.create_table('memberships',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('role_id', sa.INTEGER(), nullable=False),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='memberships_entity_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='memberships_role_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='memberships_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='memberships_pkey'),
    sa.UniqueConstraint('user_id', 'entity_id', name='uq_user_entity', postgresql_nulls_not_distinct=False)
    )
    op.create_table('notification_preferences',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('in_app_enabled', sa.BOOLEAN(), nullable=False),
    sa.Column('email_enabled', sa.BOOLEAN(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='notification_preferences_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='notification_preferences_pkey'),
    sa.UniqueConstraint('user_id', 'event_type', name='uq_user_event_pref', postgresql_nulls_not_distinct=False)
    )
    op.create_table('notifications',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('recipient_id', sa.INTEGER(), nullable=False),
    sa.Column('actor_id', sa.INTEGER(), nullable=True),
    sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('resource_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('resource_id', sa.INTEGER(), nullable=True),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), nullable=False),
    sa.Column('body', sa.TEXT(), nullable=True),
    sa.Column('data', postgresql.JSON(), nullable=True),
    sa.Column('is_read', sa.BOOLEAN(), nullable=False),
    sa.Column('read_at', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name='notifications_actor_id_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='notifications_entity_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], name='notifications_recipient_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='notifications_pkey')
    )
    op.create_index('ix_notifications_recipient_unread', 'notifications', ['recipient_id', 'is_read', 'created_at'], unique=False)
    op.create_table('resource_categories',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('description', sa.VARCHAR(length=500), nullable=True),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='resource_categories_entity_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='resource_categories_pkey')
    )
    op.create_table('role_permissions',
    sa.Column('role_id', sa.INTEGER(), nullable=True),
    sa.Column('permission_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name='role_permissions_permission_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='role_permissions_role_id_fkey', ondelete='CASCADE')
    )
    op.create_table('user_groups',
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('group_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name='user_groups_group_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_groups_user_id_fkey', ondelete='CASCADE')
    )
    op.create_table('user_permissions',
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('permission_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name='user_permissions_permission_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_permissions_user_id_fkey', ondelete='CASCADE')
    )
    op.create_table('activity_registrations',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('activity_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('status', sa.VARCHAR(length=20), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=True),
    sa.Column('registered_at', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='activity_registrations_activity_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='activity_registrations_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='activity_registrations_pkey')
    )
    op.create_index('ix_activity_registrations_id', 'activity_registrations', ['id'], unique=False)
    op.create_table('chat_join_requests',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('conversation_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'accepted', 'rejected', name='join_request_status'), nullable=False),
    sa.Column('requested_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('reviewed_by_id', sa.INTEGER(), nullable=True),
    sa.Column('reviewed_at', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], name='chat_join_requests_conversation_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], name='chat_join_requests_reviewed_by_id_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='chat_join_requests_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='chat_join_requests_pkey')
    )
    op.create_table('chat_members',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('conversation_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('role', postgresql.ENUM('admin', 'member', name='member_role'), nullable=False),
    sa.Column('joined_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('left_at', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('last_read_at', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('is_muted', sa.BOOLEAN(), nullable=False),
    sa.Column('is_pinned', sa.BOOLEAN(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], name='chat_members_conversation_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='chat_members_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='chat_members_pkey')
    )
    op.create_index('ix_chat_members_conv_user', 'chat_members', ['conversation_id', 'user_id'], unique=False)
    op.create_table('chat_messages',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('conversation_id', sa.INTEGER(), nullable=False),
    sa.Column('sender_id', sa.INTEGER(), nullable=True),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('message_type', postgresql.ENUM('text', 'system', 'file', name='message_type'), nullable=False),
    sa.Column('reply_to_id', sa.INTEGER(), nullable=True),
    sa.Column('reply_preview', sa.TEXT(), nullable=True),
    sa.Column('file_url', sa.TEXT(), nullable=True),
    sa.Column('file_name', sa.TEXT(), nullable=True),
    sa.Column('file_type', sa.TEXT(), nullable=True),
    sa.Column('is_deleted', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], name='chat_messages_conversation_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reply_to_id'], ['chat_messages.id'], name='chat_messages_reply_to_id_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], name='chat_messages_sender_id_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name='chat_messages_pkey')
    )
    op.create_index('ix_chat_messages_conv_created', 'chat_messages', ['conversation_id', 'created_at'], unique=False)
    op.create_table('comments',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('communication_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['communication_id'], ['communications.id'], name='comments_communication_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='comments_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='comments_pkey')
    )
    op.create_index('ix_comments_id', 'comments', ['id'], unique=False)
    op.create_table('resources',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=200), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('resource_type', postgresql.ENUM('link', 'document', 'image', 'video', name='resourcetype'), nullable=False),
    sa.Column('url', sa.VARCHAR(length=2048), nullable=True),
    sa.Column('file_path', sa.VARCHAR(length=500), nullable=True),
    sa.Column('original_filename', sa.VARCHAR(length=255), nullable=True),
    sa.Column('tags', sa.TEXT(), nullable=True),
    sa.Column('entity_id', sa.INTEGER(), nullable=False),
    sa.Column('category_id', sa.INTEGER(), nullable=True),
    sa.Column('created_by', sa.INTEGER(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['category_id'], ['resource_categories.id'], name='resources_category_id_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='resources_created_by_fkey'),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='resources_entity_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='resources_pkey')
    )


def downgrade() -> None:
    """Drop the core schema."""
    op.drop_table('resources')
    op.drop_table('comments')
    op.drop_table('chat_messages')
    op.drop_table('chat_members')
    op.drop_table('chat_join_requests')
    op.drop_table('activity_registrations')
    op.drop_table('user_permissions')
    op.drop_table('user_groups')
    op.drop_table('role_permissions')
    op.drop_table('resource_categories')
    op.drop_table('notifications')
    op.drop_table('notification_preferences')
    op.drop_table('memberships')
    op.drop_table('magazines')
    op.drop_table('group_roles')
    op.drop_table('entity_view_configs')
    op.drop_table('entity_roles')
    op.drop_table('entity_brandings')
    op.drop_table('communications')
    op.drop_table('chat_conversations')
    op.drop_table('audit_logs')
    op.drop_table('activities')
    op.drop_table('users')
    op.drop_table('roles')
    op.drop_table('revoked_tokens')
    op.drop_table('permissions')
    op.drop_table('groups')
    op.drop_table('entities')
    op.execute('DROP TYPE IF EXISTS conversation_type')
    op.execute('DROP TYPE IF EXISTS join_request_status')
    op.execute('DROP TYPE IF EXISTS member_role')
    op.execute('DROP TYPE IF EXISTS message_type')
    op.execute('DROP TYPE IF EXISTS resourcetype')
