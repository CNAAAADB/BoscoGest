from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class GroupDetails(GroupResponse):
    users: List["UserResponse"] = [] # type: ignore
    roles: List["RoleResponse"] = [] # type: ignore

    model_config = ConfigDict(from_attributes=True)

# Importa aquí al final para no generar circular import
from app.schemas.user import UserResponse
from app.schemas.role import RoleResponse

# Resuelve referencias forward
GroupDetails.model_rebuild()