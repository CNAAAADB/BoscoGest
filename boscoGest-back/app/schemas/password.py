from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v