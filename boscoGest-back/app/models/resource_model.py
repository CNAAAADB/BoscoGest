import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, ForeignKey, TIMESTAMP, func, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ResourceType(str, enum.Enum):
    LINK = "link"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_type: Mapped[ResourceType] = mapped_column(
        SQLAlchemyEnum(ResourceType, values_callable=lambda x: [e.value for e in x])
    )
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resource_categories.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True, onupdate=func.now())

    entity: Mapped["Entity"] = relationship("Entity", back_populates="resources")
    category: Mapped[Optional["ResourceCategory"]] = relationship("ResourceCategory", back_populates="resources")
    creator: Mapped["User"] = relationship("User")
