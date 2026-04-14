from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

if TYPE_CHECKING:
    from .entity import EntityResponse


class EntityBrandingBase(BaseModel):
    """Base schema for entity branding."""
    subdomain: Optional[str] = Field(None, max_length=50)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: str = Field("#1976d2", max_length=7)
    secondary_color: str = Field("#424242", max_length=7)
    accent_color: str = Field("#ff4081", max_length=7)
    display_name: Optional[str] = Field(None, max_length=100)
    tagline: Optional[str] = Field(None, max_length=200)
    custom_footer: Optional[str] = None

    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Subdomain debe ser alfanumérico con guiones, sin empezar/terminar con guión
        pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
        if not re.match(pattern, v.lower()):
            raise ValueError('Subdomain must be alphanumeric with hyphens, not starting/ending with hyphen')
        return v.lower()

    @field_validator('primary_color', 'secondary_color', 'accent_color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        # Validar formato hexadecimal de color
        pattern = r'^#[0-9A-Fa-f]{6}$'
        if not re.match(pattern, v):
            raise ValueError('Color must be in hex format (e.g., #1976d2)')
        return v.lower()


class EntityBrandingCreate(EntityBrandingBase):
    """Schema for creating entity branding."""
    entity_id: int


class EntityBrandingUpdate(BaseModel):
    """Schema for updating entity branding. All fields optional."""
    subdomain: Optional[str] = Field(None, max_length=50)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    accent_color: Optional[str] = Field(None, max_length=7)
    display_name: Optional[str] = Field(None, max_length=100)
    tagline: Optional[str] = Field(None, max_length=200)
    custom_footer: Optional[str] = None

    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
        if not re.match(pattern, v.lower()):
            raise ValueError('Subdomain must be alphanumeric with hyphens, not starting/ending with hyphen')
        return v.lower()

    @field_validator('primary_color', 'secondary_color', 'accent_color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = r'^#[0-9A-Fa-f]{6}$'
        if not re.match(pattern, v):
            raise ValueError('Color must be in hex format (e.g., #1976d2)')
        return v.lower()


class EntityBrandingResponse(EntityBrandingBase):
    """Schema for entity branding response."""
    id: int
    entity_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityBrandingWithEntity(EntityBrandingResponse):
    """Schema for entity branding with entity details."""
    entity: Optional["EntityResponse"] = None

    model_config = ConfigDict(from_attributes=True)
