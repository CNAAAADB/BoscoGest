from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional

class PermissionBase(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    inheritable: bool = True

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    inheritable: Optional[bool] = None

class PermissionResponse(PermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)