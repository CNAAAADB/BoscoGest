from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# Lista de vistas válidas del sistema
VALID_VIEW_NAMES = [
    "dashboard",
    "member_stats",
    "users",
    "entities",
    "roles",
    "activities",
    "communications",
    "magazines",
    "resources",
    "chat",
    "shop",
    "fees",
    "payments",
    "settings",
]


class EntityViewConfigBase(BaseModel):
    """Base schema for entity view configuration."""
    view_name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    is_enabled: bool = True
    display_order: int = Field(0, ge=0)
    icon: Optional[str] = Field(None, max_length=50)


class EntityViewConfigCreate(EntityViewConfigBase):
    """Schema for creating a single view configuration."""
    entity_id: int


class EntityViewConfigUpdate(BaseModel):
    """Schema for updating view configuration. All fields optional."""
    display_name: Optional[str] = Field(None, max_length=100)
    is_enabled: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)
    icon: Optional[str] = Field(None, max_length=50)


class EntityViewConfigResponse(EntityViewConfigBase):
    """Schema for view configuration response."""
    id: int
    entity_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityViewConfigBulkUpdate(BaseModel):
    """Schema for bulk updating view configurations for an entity."""
    configs: List["ViewConfigItem"]


class ViewConfigItem(BaseModel):
    """Single view configuration item for bulk operations."""
    view_name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    is_enabled: bool = True
    display_order: int = Field(0, ge=0)
    icon: Optional[str] = Field(None, max_length=50)


class EntityViewConfigListResponse(BaseModel):
    """Schema for list of view configurations."""
    entity_id: int
    configs: List[EntityViewConfigResponse]

    model_config = ConfigDict(from_attributes=True)


# Rebuild forward references
EntityViewConfigBulkUpdate.model_rebuild()
