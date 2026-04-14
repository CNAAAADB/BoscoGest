from typing import List, Optional
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .relationships import user_groups, group_roles
from app.database import Base

class Group(Base):
    __tablename__ = 'groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[List["User"]] = relationship(secondary=user_groups, back_populates="groups")
    roles: Mapped[List["Role"]] = relationship(secondary=group_roles, back_populates="groups")
