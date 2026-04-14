from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import EntityResponse

class ActivityBase(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    date: datetime
    capacity: int
    price: float
    allow_waitlist: bool
    entity_id: int

class ActivityCreate(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    date: datetime
    capacity: int
    price: float
    allow_waitlist: bool
    entity_id: int

class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    date: Optional[datetime] = None
    capacity: Optional[int] = None
    price: Optional[float] = None
    allow_waitlist: Optional[bool] = None
    image_url: Optional[str]

class ActivityResponse(ActivityBase):
    id: int
    created_at: datetime
    image_url: Optional[str]
    entity: Optional["EntityResponse"] = None

    model_config = ConfigDict(from_attributes=True)
