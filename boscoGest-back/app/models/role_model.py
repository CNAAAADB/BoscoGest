from typing import List, Optional
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .relationships import role_permissions, group_roles, entity_roles
from app.database import Base

class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="role", cascade="all, delete-orphan")
    permissions: Mapped[List["Permission"]] = relationship(secondary=role_permissions, back_populates="roles")
    groups: Mapped[List["Group"]] = relationship(secondary=group_roles, back_populates="roles")
    entities: Mapped[List["Entity"]] = relationship(secondary=entity_roles, back_populates="roles")
