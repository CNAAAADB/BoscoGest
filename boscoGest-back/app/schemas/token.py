from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class ActivationRequest(BaseModel):
    """The secret from a welcome-email link."""

    token: str = Field(..., min_length=16, max_length=256)


class ActivationResendRequest(BaseModel):
    """Ask for a fresh link when the one in the inbox no longer works."""

    identifier: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Email o teléfono con el que se dio de alta la cuenta",
    )
