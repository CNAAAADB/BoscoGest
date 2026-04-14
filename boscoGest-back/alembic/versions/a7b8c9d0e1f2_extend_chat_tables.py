"""extend chat tables: message type, reply, files, mute, pin

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Create message_type enum
    bind.execute(
        sa.text(
            "DO $$ BEGIN "
            "  CREATE TYPE message_type AS ENUM ('text', 'system', 'file'); "
            "EXCEPTION WHEN duplicate_object THEN null; "
            "END $$;"
        )
    )

    # Add columns to chat_messages
    bind.execute(
        sa.text(
            "ALTER TABLE chat_messages "
            "  ADD COLUMN IF NOT EXISTS message_type message_type NOT NULL DEFAULT 'text', "
            "  ADD COLUMN IF NOT EXISTS reply_to_id INTEGER REFERENCES chat_messages(id) ON DELETE SET NULL, "
            "  ADD COLUMN IF NOT EXISTS reply_preview TEXT, "
            "  ADD COLUMN IF NOT EXISTS file_url TEXT, "
            "  ADD COLUMN IF NOT EXISTS file_name TEXT, "
            "  ADD COLUMN IF NOT EXISTS file_type TEXT;"
        )
    )

    # Add columns to chat_members
    bind.execute(
        sa.text(
            "ALTER TABLE chat_members "
            "  ADD COLUMN IF NOT EXISTS is_muted BOOLEAN NOT NULL DEFAULT FALSE, "
            "  ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;"
        )
    )


def downgrade():
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "ALTER TABLE chat_members "
            "  DROP COLUMN IF EXISTS is_muted, "
            "  DROP COLUMN IF EXISTS is_pinned;"
        )
    )

    bind.execute(
        sa.text(
            "ALTER TABLE chat_messages "
            "  DROP COLUMN IF EXISTS message_type, "
            "  DROP COLUMN IF EXISTS reply_to_id, "
            "  DROP COLUMN IF EXISTS reply_preview, "
            "  DROP COLUMN IF EXISTS file_url, "
            "  DROP COLUMN IF EXISTS file_name, "
            "  DROP COLUMN IF EXISTS file_type;"
        )
    )

    bind.execute(sa.text("DROP TYPE IF EXISTS message_type;"))
