from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.user import UserResponse
from app.schemas.entity import EntityResponse


class MembershipBase(BaseModel):
    user_id: int
    role_id: int
    entity_id: int
    is_active: bool = True


class MembershipCreate(BaseModel):
    user_id: int
    role_id: int
    entity_id: int
    is_active: bool = True


class MembershipUpdate(BaseModel):
    role_id: Optional[int] = None


class MembershipResponse(MembershipBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Role with permissions but without memberships to avoid circular reference
class RoleWithPermissions(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: List["PermissionResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @model_validator(mode='before')
    @classmethod
    def extract_permissions(cls, data: Any) -> Any:
        # If data is a SQLAlchemy model, extract permissions
        if hasattr(data, 'permissions') and hasattr(data, '__tablename__'):
            # It's a SQLAlchemy object
            return {
                'id': data.id,
                'name': data.name,
                'description': data.description,
                'permissions': list(data.permissions)  # Convert to list to ensure it's loaded
            }
        return data


class MembershipDetails(MembershipResponse):
    user: Optional[UserResponse] = None
    role: Optional[RoleWithPermissions] = None
    entity: Optional[EntityResponse] = None

    model_config = ConfigDict(from_attributes=True)


# Import after class definition to avoid circular imports
from app.schemas.permission import PermissionResponse

# Rebuild model to resolve forward references
RoleWithPermissions.model_rebuild()
MembershipDetails.model_rebuild()