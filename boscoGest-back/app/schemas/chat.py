from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List


class UserBrief(BaseModel):
    id: int
    name: str
    surname: str

    model_config = ConfigDict(from_attributes=True)


# ── Conversation ──────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DirectConversationRequest(BaseModel):
    target_user_id: int


class LastMessageBrief(BaseModel):
    id: int
    content: str
    sender: Optional[UserBrief] = None
    created_at: datetime
    is_deleted: bool
    message_type: str = "text"

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    id: int
    type: str
    name: Optional[str] = None
    created_by_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    other_user: Optional[UserBrief] = None
    last_message: Optional[LastMessageBrief] = None
    unread_count: int = 0
    my_role: Optional[str] = None
    is_muted: bool = False
    is_pinned: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(BaseModel):
    id: int
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    my_role: Optional[str] = None
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── Member ────────────────────────────────────────────────────────────


class MemberResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    user: UserBrief
    role: str
    joined_at: datetime
    is_active: bool
    is_online: bool = False

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "member"):
            raise ValueError("role must be 'admin' or 'member'")
        return v


# ── Message ───────────────────────────────────────────────────────────


class ReplyBrief(BaseModel):
    id: int
    sender: Optional[UserBrief] = None
    preview: str

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str
    reply_to_id: Optional[int] = None


class FileMessageCreate(BaseModel):
    file_name: str
    file_type: str
    reply_to_id: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: Optional[int] = None
    sender: Optional[UserBrief] = None
    content: str
    message_type: str = "text"
    reply_to: Optional[ReplyBrief] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    is_deleted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Join Request ──────────────────────────────────────────────────────


class JoinRequestReview(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("accepted", "rejected"):
            raise ValueError("status must be 'accepted' or 'rejected'")
        return v


class JoinRequestResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    user: UserBrief
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── User search ───────────────────────────────────────────────────────


class UserSearchResult(BaseModel):
    id: int
    name: str
    surname: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class UserPresence(BaseModel):
    user_id: int
    is_online: bool
