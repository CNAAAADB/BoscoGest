from datetime import datetime
from pydantic import BaseModel, Field


class ActivityRegistrationCreate(BaseModel):
    guest_count: int = Field(default=0, ge=0, le=2147483646, strict=True)


class ActivityRegistrationBase(BaseModel):
    activity_id: int
    user_id: int

class ActivityRegistrationOut(BaseModel):
    id: int
    status: str
    user_id: int
    activity_id: int
    guest_count: int
    registered_at: datetime

    class Config:
        orm_mode = True