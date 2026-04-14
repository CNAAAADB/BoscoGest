from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, Text, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional
from app.database import Base

class Communication(Base):
    __tablename__ = "communications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="communications")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="communication", cascade="all, delete-orphan")

    @property
    def entity_name(self) -> Optional[str]:
        return self.entity.name if self.entity else None
