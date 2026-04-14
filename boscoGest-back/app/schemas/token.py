from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None