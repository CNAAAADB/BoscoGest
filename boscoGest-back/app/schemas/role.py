from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = Field(default=None, description="Optional list of permission IDs to assign to the role")

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = Field(default=None, description="Optional list of permission IDs. If provided (even empty), replaces current permissions. If not provided, keeps existing permissions.")

class RoleResponse(RoleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class RoleDetails(RoleResponse):
    permissions: List["PermissionResponse"] = [] # type: ignore
    groups: List["GroupResponse"] = []  # type: ignore
    memberships: List["MembershipResponse"] = []  # type: ignore

    model_config = ConfigDict(from_attributes=True)

from app.schemas.permission import PermissionResponse
from app.schemas.group import GroupResponse
from app.schemas.membership import MembershipResponse

# Resuelve referencias forward
RoleDetails.model_rebuild()