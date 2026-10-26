from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, TIMESTAMP, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Magazine(Base):
    __tablename__ = 'magazines'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    collection: Mapped[Optional[str]] = mapped_column(String(100))
    issue_number: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(500))  # Path to PDF file
    entity_id: Mapped[int] = mapped_column(ForeignKey('entities.id', ondelete='CASCADE'), index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships
    entity: Mapped["Entity"] = relationship("Entity", back_populates="magazines")
