from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import EntityResponse


END_BEFORE_START = "La actividad tiene que terminar después de empezar"


# The columns have no time zone and hold UTC. Both ways across the API that has
# to be said out loud: what comes in with an offset is converted to UTC rather
# than left to the database session's zone, and what goes out carries the
# offset. Without it the browser read "16:00" as local time, so an activity
# entered for 17:00 in Spain showed at 16:00 — 15:00 in summer — and moved back
# again every time it was edited and saved.
def to_utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def as_utc(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def check_end_after_start(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Shared by the create schema and by the update, which has to compare
    against whatever the activity already stores."""
    start, end = to_utc_naive(start), to_utc_naive(end)
    if start is None or end is None:
        return
    if end <= start:
        raise ValueError(END_BEFORE_START)

class ActivityBase(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    date: datetime
    end_date: Optional[datetime] = None
    capacity: int
    price: float
    allow_waitlist: bool
    entity_id: int

class ActivityCreate(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    date: datetime
    end_date: Optional[datetime] = None
    capacity: int
    price: float
    allow_waitlist: bool
    entity_id: int

    _utc = field_validator("date", "end_date")(to_utc_naive)

    @model_validator(mode="after")
    def _end_after_start(self):
        check_end_after_start(self.date, self.end_date)
        return self

class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    capacity: Optional[int] = None
    price: Optional[float] = None
    allow_waitlist: Optional[bool] = None
    image_url: Optional[str]

    _utc = field_validator("date", "end_date")(to_utc_naive)

class ActivityResponse(ActivityBase):
    id: int
    created_at: datetime
    created_by_id: int
    image_url: Optional[str]
    entity: Optional["EntityResponse"] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date", "end_date", "created_at")
    def _as_utc(self, value: Optional[datetime]) -> Optional[str]:
        return as_utc(value)
