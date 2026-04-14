from datetime import datetime
from sqlalchemy import String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    revoked_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP)
