from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    entity: Mapped["Entity"] = relationship("Entity", back_populates="resource_categories")
    resources: Mapped[List["Resource"]] = relationship("Resource", back_populates="category")
