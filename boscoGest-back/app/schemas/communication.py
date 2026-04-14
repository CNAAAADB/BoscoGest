from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


class CommunicationStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


VALID_TRANSITIONS = {
    "draft": ["review", "published"],
    "review": ["published", "draft"],
    "published": ["archived"],
    "archived": [],
}


class UserBasicInfo(BaseModel):
    id: int
    name: str
    surname: str
    email: str

    class Config:
        from_attributes = True

class CommunicationBase(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    entity_id: int

class CommunicationCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    entity_id: int
    status: Optional[str] = "draft"

class CommunicationUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None

class CommunicationResponse(CommunicationBase):
    id: int
    created_by_id: int
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    entity_name: Optional[str] = None

    class Config:
        from_attributes = True


class StatusTransitionRequest(BaseModel):
    target_status: CommunicationStatus

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class CommentUpdate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
    communication_id: int
    user_id: int
    user: UserBasicInfo
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CommunicationWithCommentsResponse(CommunicationResponse):
    comments: List[CommentResponse] = []

    class Config:
        from_attributes = True
