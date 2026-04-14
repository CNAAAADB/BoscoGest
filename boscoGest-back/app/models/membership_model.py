from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "entity_id", name="uq_user_entity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    role: Mapped["Role"] = relationship("Role", back_populates="memberships")
    entity: Mapped["Entity"] = relationship("Entity", back_populates="memberships")