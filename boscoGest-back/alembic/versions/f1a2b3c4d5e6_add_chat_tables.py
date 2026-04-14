"""add_chat_tables

Revision ID: f1a2b3c4d5e6
Revises: 13b6104641b8
Create Date: 2026-04-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "13b6104641b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── chat_conversations ────────────────────────────────────────────
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "type",
            sa.Enum("direct", "group", name="conversation_type"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── chat_members ──────────────────────────────────────────────────
    op.create_table(
        "chat_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer,
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("admin", "member", name="member_role"),
            default="member",
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("left_at", sa.TIMESTAMP, nullable=True),
        sa.Column("last_read_at", sa.TIMESTAMP, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    )
    op.create_index(
        "ix_chat_members_conv_user",
        "chat_members",
        ["conversation_id", "user_id"],
    )

    # ── chat_messages ─────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer,
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_messages_conv_created",
        "chat_messages",
        ["conversation_id", "created_at"],
    )

    # ── chat_join_requests ────────────────────────────────────────────
    op.create_table(
        "chat_join_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer,
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "accepted", "rejected",
                name="join_request_status",
            ),
            default="pending",
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "reviewed_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP, nullable=True),
    )

    # ── Permissions for chat resource ─────────────────────────────────
    bind = op.get_bind()

    result = bind.execute(
        sa.text("SELECT id, name FROM roles WHERE name IN ('superadmin', 'admin', 'socio')")
    )
    roles = {row[1]: row[0] for row in result}

    permission_actions = ["create", "list", "read", "update", "delete", "assign", "manage"]
    resource = "chat"

    all_perm_ids = []
    socio_perm_ids = []

    for action in permission_actions:
        perm_name = f"{resource}_{action}_permission"
        result = bind.execute(
            sa.text(
                "INSERT INTO permissions (name, resource, action, is_active) "
                "VALUES (:name, :resource, :action, true) RETURNING id"
            ),
            {"name": perm_name, "resource": resource, "action": action},
        )
        perm_id = result.fetchone()[0]
        all_perm_ids.append(perm_id)
        if action in ("list", "read", "create"):
            socio_perm_ids.append(perm_id)

    for perm_id in all_perm_ids:
        for role_name in ("superadmin", "admin"):
            if role_name in roles:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) "
                        "VALUES (:role_id, :permission_id)"
                    ),
                    {"role_id": roles[role_name], "permission_id": perm_id},
                )

    if "socio" in roles:
        for perm_id in socio_perm_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {"role_id": roles["socio"], "permission_id": perm_id},
            )


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE resource = 'chat')"
        )
    )
    bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'chat'"))

    op.drop_table("chat_join_requests")
    op.drop_index("ix_chat_messages_conv_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_members_conv_user", table_name="chat_members")
    op.drop_table("chat_members")
    op.drop_table("chat_conversations")

    op.execute("DROP TYPE IF EXISTS join_request_status")
    op.execute("DROP TYPE IF EXISTS member_role")
    op.execute("DROP TYPE IF EXISTS conversation_type")
