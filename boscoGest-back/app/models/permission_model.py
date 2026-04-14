from typing import Any, Dict, List, Optional
from sqlalchemy import String, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .relationships import role_permissions, user_permissions
from app.database import Base

class Permission(Base):
    __tablename__ = 'permissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    inheritable: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[List["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")
    users: Mapped[List["User"]] = relationship(secondary=user_permissions, back_populates="direct_permissions")

    __table_args__ = (
        {'sqlite_autoincrement': True},  # For SQLite, if used
    )
