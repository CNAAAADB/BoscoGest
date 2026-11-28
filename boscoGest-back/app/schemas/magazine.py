from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class MagazineBase(BaseModel):
    title: str
    collection: Optional[str] = None
    issue_number: Optional[int] = None
    description: Optional[str] = None
    entity_id: int


class MagazineCreate(MagazineBase):
    pass


class MagazineUpdate(BaseModel):
    title: Optional[str] = None
    collection: Optional[str] = None
    issue_number: Optional[int] = None
    description: Optional[str] = None


class MagazineResponse(MagazineBase):
    permissions: Optional[dict[str, bool]] = None
    id: int
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MagazineDetails(MagazineResponse):
    entity: Optional["EntityResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import after class definition to avoid circular imports
from app.schemas.entity import EntityResponse

# Rebuild model to resolve forward references
MagazineDetails.model_rebuild()
