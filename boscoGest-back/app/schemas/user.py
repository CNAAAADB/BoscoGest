from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime, date
from typing import Dict, Any, List, Optional

class UserBase(BaseModel):
    email: EmailStr
    name: str
    surname: str
    phone: str
    address: Optional[str] = None
    birthdate: date
    dni: str
    photo: Optional[str] = None
    iban: Optional[str] = None
    size: Optional[str] = None
    hobbies: Optional[str] = None
    job_position: Optional[str] = None

class UserCreate(UserBase):
    password: str
    entity_id: Optional[int] = None
    role_id: Optional[int] = None

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

    @field_validator('role_id')
    @classmethod
    def validate_role_with_entity(cls, v: Optional[int], info) -> Optional[int]:
        entity_id = info.data.get('entity_id')
        if (v is None and entity_id is not None) or (v is not None and entity_id is None):
            raise ValueError('Both entity_id and role_id must be provided together or both omitted')
        return v
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[date] = None
    dni: Optional[str] = None
    photo: Optional[str] = None
    iban: Optional[str] = None
    size: Optional[str] = None
    hobbies: Optional[str] = None
    job_position: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        new_password = info.data.get('new_password')
        if new_password and v != new_password:
            raise ValueError('Passwords do not match')
        return v

class FirstTimePasswordChange(BaseModel):
    new_password: str
    confirm_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        new_password = info.data.get('new_password')
        if new_password and v != new_password:
            raise ValueError('Passwords do not match')
        return v

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    surname: str
    phone: str
    address: Optional[str]
    birthdate: date
    dni: str
    photo: Optional[str]
    iban: Optional[str]
    size: Optional[str]
    hobbies: Optional[str]
    job_position: Optional[str]
    is_active: bool
    must_change_password: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserDetails(UserResponse):
    groups: List["GroupResponse"] = []  # type: ignore
    roles: List["RoleResponse"] = []    # type: ignore
    memberships: List["MembershipDetails"] = []  # type: ignore

    model_config = ConfigDict(from_attributes=True)

# Importa aquí al final para no generar circular import
from app.schemas.group import GroupResponse
from app.schemas.role import RoleResponse
from app.schemas.membership import MembershipDetails

# Resuelve referencias forward
UserDetails.model_rebuild()