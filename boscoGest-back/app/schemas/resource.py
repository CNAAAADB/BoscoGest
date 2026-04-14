from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from app.models.resource_model import ResourceType


# --- Resource Category Schemas ---

class ResourceCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    entity_id: int


class ResourceCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ResourceCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    entity_id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Resource Schemas ---

class ResourceCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    resource_type: ResourceType
    url: Optional[str] = None
    tags: Optional[str] = None
    entity_id: int
    category_id: Optional[int] = None


class ResourceUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[str] = None
    category_id: Optional[int] = None


class ResourceResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    resource_type: ResourceType
    url: Optional[str] = None
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    tags: Optional[str] = None
    entity_id: int
    category_id: Optional[int] = None
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CreatorBrief(BaseModel):
    id: int
    name: str
    surname: str

    model_config = ConfigDict(from_attributes=True)


class ResourceDetails(ResourceResponse):
    entity: Optional["EntityResponse"] = None
    category: Optional[ResourceCategoryResponse] = None
    creator: Optional[CreatorBrief] = None

    model_config = ConfigDict(from_attributes=True)


# Import after class definition to avoid circular imports
from app.schemas.entity import EntityResponse

# Rebuild model to resolve forward references
ResourceDetails.model_rebuild()
