from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class RegisterRequest(BaseModel):
    name: str
    surname: str
    email: EmailStr
    password: str
    phone: str
    birthdate: str  # ISO date string: YYYY-MM-DD
    dni: str
    address: Optional[str] = None
    entity_id: int
    message: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        return v


class MembershipRequestCreate(BaseModel):
    entity_id: int
    message: Optional[str] = None


class MembershipRequestReject(BaseModel):
    rejection_reason: Optional[str] = None


class UserMinimal(BaseModel):
    id: int
    name: str
    surname: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class EntityMinimal(BaseModel):
    id: int
    name: str
    level: int

    model_config = ConfigDict(from_attributes=True)


class MembershipRequestResponse(BaseModel):
    id: int
    user_id: int
    entity_id: int
    status: str
    message: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    user: Optional[UserMinimal] = None
    entity: Optional[EntityMinimal] = None

    model_config = ConfigDict(from_attributes=True)
