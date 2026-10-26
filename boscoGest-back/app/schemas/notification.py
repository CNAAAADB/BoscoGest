from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


class ActorBrief(BaseModel):
    id: int
    name: str
    surname: str

    model_config = ConfigDict(from_attributes=True)


class EntityBrief(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    recipient_id: int
    actor_id: Optional[int] = None
    actor: Optional[ActorBrief] = None
    event_type: str
    resource_type: str
    resource_id: Optional[int] = None
    entity_id: int
    entity: Optional[EntityBrief] = None
    title: str
    body: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    count: int


class NotificationPreferenceItem(BaseModel):
    event_type: str
    in_app_enabled: bool = True
    email_enabled: bool = False
    push_enabled: bool = True


class NotificationPreferenceResponse(BaseModel):
    event_type: str
    in_app_enabled: bool
    email_enabled: bool
    push_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesUpdate(BaseModel):
    preferences: List[NotificationPreferenceItem]


class DeviceRegistration(BaseModel):
    """Alta de un dispositivo para recibir push."""

    token: str = Field(min_length=1, max_length=4096)
    # Solo las dos plataformas que la aplicación publica. La web no recibe push.
    platform: Literal["ios", "android"]


class DeviceResponse(BaseModel):
    id: int
    platform: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
