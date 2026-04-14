from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload

from app.models.chat_model import (
    ChatConversation,
    ChatJoinRequest,
    ChatMember,
    ChatMessage,
)
from app.models.user_model import User


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Conversations ─────────────────────────────────────────────────

    def get_conversation(self, conversation_id: int) -> Optional[ChatConversation]:
        stmt = (
            select(ChatConversation)
            .options(joinedload(ChatConversation.members).joinedload(ChatMember.user))
            .where(ChatConversation.id == conversation_id, ChatConversation.is_active == True)
        )
        return self.db.execute(stmt).scalars().first()

    def get_user_conversations(self, user_id: int) -> List[ChatConversation]:
        """Return all active conversations where user is an active member."""
        stmt = (
            select(ChatConversation)
            .join(
                ChatMember,
                (ChatMember.conversation_id == ChatConversation.id)
                & (ChatMember.user_id == user_id)
                & (ChatMember.is_active == True),
            )
            .where(ChatConversation.is_active == True)
            .order_by(ChatConversation.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def find_direct_conversation(
        self, user_id_a: int, user_id_b: int
    ) -> Optional[ChatConversation]:
        """Find existing active direct conversation between two users."""
        sub_a = (
            select(ChatMember.conversation_id)
            .where(
                ChatMember.user_id == user_id_a,
                ChatMember.is_active == True,
            )
            .scalar_subquery()
        )
        sub_b = (
            select(ChatMember.conversation_id)
            .where(
                ChatMember.user_id == user_id_b,
                ChatMember.is_active == True,
            )
            .scalar_subquery()
        )
        stmt = select(ChatConversation).where(
            ChatConversation.type == "direct",
            ChatConversation.is_active == True,
            ChatConversation.id.in_(sub_a),
            ChatConversation.id.in_(sub_b),
        )
        return self.db.execute(stmt).scalars().first()

    def create_conversation(
        self,
        type: str,
        created_by_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ChatConversation:
        conv = ChatConversation(
            type=type,
            created_by_id=created_by_id,
            name=name,
            description=description,
        )
        self.db.add(conv)
        self.db.flush()
        self.db.refresh(conv)
        return conv

    def update_conversation(
        self,
        conversation: ChatConversation,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ChatConversation:
        if name is not None:
            conversation.name = name
        if description is not None:
            conversation.description = description
        self.db.flush()
        return conversation

    def update_conversation_avatar(
        self, conversation: ChatConversation, avatar_url: str
    ) -> ChatConversation:
        conversation.avatar_url = avatar_url
        self.db.flush()
        return conversation

    def deactivate_conversation(self, conversation: ChatConversation) -> None:
        conversation.is_active = False
        self.db.flush()

    def touch_updated_at(self, conversation_id: int) -> None:
        self.db.execute(
            update(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )

    # ── Members ───────────────────────────────────────────────────────

    def get_member(
        self, conversation_id: int, user_id: int
    ) -> Optional[ChatMember]:
        stmt = select(ChatMember).where(
            ChatMember.conversation_id == conversation_id,
            ChatMember.user_id == user_id,
            ChatMember.is_active == True,
        )
        return self.db.execute(stmt).scalars().first()

    def get_members(self, conversation_id: int) -> List[ChatMember]:
        stmt = (
            select(ChatMember)
            .options(joinedload(ChatMember.user))
            .where(
                ChatMember.conversation_id == conversation_id,
                ChatMember.is_active == True,
            )
            .order_by(ChatMember.joined_at)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def count_active_members(self, conversation_id: int) -> int:
        stmt = select(func.count()).select_from(ChatMember).where(
            ChatMember.conversation_id == conversation_id,
            ChatMember.is_active == True,
        )
        return self.db.execute(stmt).scalar() or 0

    def add_member(
        self, conversation_id: int, user_id: int, role: str = "member"
    ) -> ChatMember:
        member = ChatMember(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.flush()
        self.db.refresh(member)
        return member

    def remove_member(self, member: ChatMember) -> None:
        member.is_active = False
        member.left_at = datetime.utcnow()
        self.db.flush()

    def update_member_role(self, member: ChatMember, role: str) -> ChatMember:
        member.role = role
        self.db.flush()
        return member

    def update_member_muted(self, member: ChatMember, is_muted: bool) -> ChatMember:
        member.is_muted = is_muted
        self.db.flush()
        return member

    def update_member_pinned(self, member: ChatMember, is_pinned: bool) -> ChatMember:
        member.is_pinned = is_pinned
        self.db.flush()
        return member

    def update_last_read(self, conversation_id: int, user_id: int) -> None:
        self.db.execute(
            update(ChatMember)
            .where(
                ChatMember.conversation_id == conversation_id,
                ChatMember.user_id == user_id,
                ChatMember.is_active == True,
            )
            .values(last_read_at=datetime.utcnow())
        )

    def count_unread(self, conversation_id: int, user_id: int) -> int:
        """Count messages after user's last_read_at."""
        member = self.get_member(conversation_id, user_id)
        if not member:
            return 0
        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.is_deleted == False,
        )
        if member.last_read_at:
            stmt = stmt.where(ChatMessage.created_at > member.last_read_at)
        return self.db.execute(stmt).scalar() or 0

    def get_oldest_admin(self, conversation_id: int, exclude_user_id: int) -> Optional[ChatMember]:
        """Get the oldest member (by join date) that could be promoted to admin."""
        stmt = (
            select(ChatMember)
            .where(
                ChatMember.conversation_id == conversation_id,
                ChatMember.is_active == True,
                ChatMember.user_id != exclude_user_id,
            )
            .order_by(ChatMember.joined_at)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    # ── Messages ──────────────────────────────────────────────────────

    def get_message(self, message_id: int) -> Optional[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.sender),
                joinedload(ChatMessage.reply_to).joinedload(ChatMessage.sender),
            )
            .where(ChatMessage.id == message_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_messages(
        self,
        conversation_id: int,
        before_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """Cursor-based pagination: returns `limit` messages before `before_id`."""
        stmt = (
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.sender),
                joinedload(ChatMessage.reply_to).joinedload(ChatMessage.sender),
            )
            .where(ChatMessage.conversation_id == conversation_id)
        )
        if before_id is not None:
            stmt = stmt.where(ChatMessage.id < before_id)
        stmt = stmt.order_by(ChatMessage.id.desc()).limit(limit)
        messages = list(self.db.execute(stmt).scalars().unique().all())
        return list(reversed(messages))

    def search_messages(
        self, conversation_id: int, query: str, limit: int = 50
    ) -> List[ChatMessage]:
        """Full-text search within a conversation (ILIKE)."""
        pattern = f"%{query}%"
        stmt = (
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.sender),
                joinedload(ChatMessage.reply_to).joinedload(ChatMessage.sender),
            )
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.is_deleted == False,
                ChatMessage.message_type != "system",
                ChatMessage.content.ilike(pattern),
            )
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        messages = list(self.db.execute(stmt).scalars().unique().all())
        return list(reversed(messages))

    def save_message(
        self,
        conversation_id: int,
        sender_id: Optional[int],
        content: str,
        message_type: str = "text",
        reply_to_id: Optional[int] = None,
        reply_preview: Optional[str] = None,
        file_url: Optional[str] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id,
            reply_preview=reply_preview,
            file_url=file_url,
            file_name=file_name,
            file_type=file_type,
        )
        self.db.add(msg)
        self.db.flush()
        self.db.refresh(msg)
        return msg

    def soft_delete_message(self, message: ChatMessage) -> None:
        message.is_deleted = True
        message.content = ""
        self.db.flush()

    # ── Join Requests ─────────────────────────────────────────────────

    def get_join_request(self, request_id: int) -> Optional[ChatJoinRequest]:
        return self.db.execute(
            select(ChatJoinRequest)
            .options(joinedload(ChatJoinRequest.user))
            .where(ChatJoinRequest.id == request_id)
        ).scalars().first()

    def get_pending_request_for_user(
        self, conversation_id: int, user_id: int
    ) -> Optional[ChatJoinRequest]:
        return self.db.execute(
            select(ChatJoinRequest).where(
                ChatJoinRequest.conversation_id == conversation_id,
                ChatJoinRequest.user_id == user_id,
                ChatJoinRequest.status == "pending",
            )
        ).scalars().first()

    def get_pending_requests(self, conversation_id: int) -> List[ChatJoinRequest]:
        stmt = (
            select(ChatJoinRequest)
            .options(joinedload(ChatJoinRequest.user))
            .where(
                ChatJoinRequest.conversation_id == conversation_id,
                ChatJoinRequest.status == "pending",
            )
            .order_by(ChatJoinRequest.requested_at)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def create_join_request(
        self, conversation_id: int, user_id: int
    ) -> ChatJoinRequest:
        req = ChatJoinRequest(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self.db.add(req)
        self.db.flush()
        self.db.refresh(req)
        return req

    def review_join_request(
        self,
        request: ChatJoinRequest,
        status: str,
        reviewer_id: int,
    ) -> ChatJoinRequest:
        request.status = status
        request.reviewed_by_id = reviewer_id
        request.reviewed_at = datetime.utcnow()
        self.db.flush()
        return request

    # ── User search ───────────────────────────────────────────────────

    def search_users(self, query: str, exclude_user_id: int) -> List[User]:
        pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(
                User.is_active == True,
                User.id != exclude_user_id,
                (
                    User.name.ilike(pattern)
                    | User.surname.ilike(pattern)
                    | User.email.ilike(pattern)
                ),
            )
            .order_by(User.name, User.surname)
            .limit(20)
        )
        return list(self.db.execute(stmt).scalars().all())
