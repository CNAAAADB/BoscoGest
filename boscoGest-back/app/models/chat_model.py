from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(
        Enum("direct", "group", name="conversation_type"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])
    members: Mapped[list["ChatMember"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    join_requests: Mapped[list["ChatJoinRequest"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMember(Base):
    __tablename__ = "chat_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        Enum("admin", "member", name="member_role"),
        default="member",
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    left_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    last_read_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    conversation: Mapped["ChatConversation"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="joined")

    __table_args__ = (
        Index("ix_chat_members_conv_user", "conversation_id", "user_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        Enum("text", "system", "file", name="message_type"),
        default="text",
        nullable=False,
    )
    reply_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True
    )
    reply_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    conversation: Mapped["ChatConversation"] = relationship(back_populates="messages")
    sender: Mapped[Optional["User"]] = relationship(
        foreign_keys=[sender_id], lazy="joined"
    )
    reply_to: Mapped[Optional["ChatMessage"]] = relationship(
        "ChatMessage",
        foreign_keys="[ChatMessage.reply_to_id]",
        remote_side="[ChatMessage.id]",
        lazy="select",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),
    )


class ChatJoinRequest(Base):
    __tablename__ = "chat_join_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "rejected", name="join_request_status"),
        default="pending",
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    conversation: Mapped["ChatConversation"] = relationship(back_populates="join_requests")
    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="joined")
    reviewed_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[reviewed_by_id]
    )
