from pydantic import BaseModel, EmailStr, field_validator, model_validator, Field, ConfigDict
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# Tallas permitidas (debe coincidir con USER_SIZE_OPTIONS del frontend)
ALLOWED_SIZES = {"XS", "S", "M", "L", "XL", "XXL", "XXXL"}

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    name: str
    surname: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birthdate: date
    dni: str
    photo: Optional[str] = None
    iban: Optional[str] = None
    size: Optional[str] = None
    hobbies: Optional[str] = None
    job_position: Optional[str] = None

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if v not in ALLOWED_SIZES:
            raise ValueError(f'Talla no válida. Valores permitidos: {", ".join(sorted(ALLOWED_SIZES))}')
        return v

    @model_validator(mode='after')
    def email_or_phone_required(self):
        if not (self.email or self.phone):
            raise ValueError('Debe indicar email o teléfono')
        return self

class UserCreate(UserBase):
    """Creating a member on someone else's behalf.

    No password: one is generated and never disclosed, because the person
    signs in through the one-shot link in their welcome email and chooses
    their own there. Asking whoever fills this in to invent a password meant
    inventing a credential that nobody would ever use.

    Self-registration is a different schema — those people do choose their own.
    """

    entity_id: Optional[int] = None
    role_id: Optional[int] = None

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

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if v not in ALLOWED_SIZES:
            raise ValueError(f'Talla no válida. Valores permitidos: {", ".join(sorted(ALLOWED_SIZES))}')
        return v

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

class AccountDeletionRequest(BaseModel):
    """What someone sends to delete their own account.

    The password is asked for again here even though the caller is already
    authenticated: this is irreversible, and a forgotten session on a shared
    phone should not be enough to wipe an account.
    """

    password: str


class AccountDeletionResult(BaseModel):
    message: str


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
    """A user as seen by a given viewer.

    Every field outside the public tier is Optional because it may be redacted:
    see app/services/user_visibility.py for who sees what. A redacted field
    comes back as null rather than being omitted, so the shape stays stable.
    """

    # Public tier — always present.
    id: int
    name: str
    surname: str
    photo: Optional[str] = None
    job_position: Optional[str] = None
    is_active: bool
    must_change_password: bool
    created_at: datetime

    # Contact tier — requires users:read.
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    size: Optional[str] = None
    hobbies: Optional[str] = None

    # Sensitive tier — requires users:read_sensitive, or being the subject.
    dni: Optional[str] = None
    iban: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentStatus(BaseModel):
    """Whether the user has accepted the current data-processing clause."""

    accepted: bool
    accepted_at: Optional[datetime] = None
    accepted_version: Optional[str] = None
    current_version: str
    text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentAccept(BaseModel):
    """Body of POST /users/me/consent."""

    version: str


class ConsentClauseResponse(BaseModel):
    """A stored version of the data-processing clause."""

    id: int
    version: str
    text: str
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    created_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentClauseCreate(BaseModel):
    version: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1)
    # Publishing immediately makes every member reaccept on their next login,
    # so it is opt-in rather than the default.
    publish: bool = False


class ConsentClauseUpdate(BaseModel):
    text: str = Field(min_length=1)


class PaginatedUsers(BaseModel):
    """A page of users plus the total, so the client can render a paginator.

    Listing endpoints previously returned a bare list capped at limit=100 with
    no indication that anything had been left out.
    """

    items: List[UserResponse]
    total: int
    skip: int
    limit: int

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