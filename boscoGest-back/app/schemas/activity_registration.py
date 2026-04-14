from datetime import datetime
from pydantic import BaseModel

class ActivityRegistrationBase(BaseModel):
    activity_id: int
    user_id: int

class ActivityRegistrationOut(BaseModel):
    id: int
    status: str
    user_id: int
    activity_id: int
    registered_at: datetime

    class Config:
        orm_mode = True