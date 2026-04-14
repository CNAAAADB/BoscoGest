from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .relationships import entity_roles
from app.database import Base

class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    level: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    parent: Mapped[Optional["Entity"]] = relationship( "Entity", remote_side=[id], back_populates="children" )
    children: Mapped[List["Entity"]] = relationship( "Entity", back_populates="parent", cascade="all, delete-orphan" )
    memberships: Mapped[List["Membership"]] = relationship( "Membership", back_populates="entity", cascade="all, delete-orphan" )
    activities: Mapped[List["Activities"]] = relationship("Activity", back_populates="entity", cascade="all, delete-orphan")
    communications: Mapped[List["Communication"]] = relationship("Communication", back_populates="entity", cascade="all, delete-orphan")
    magazines: Mapped[List["Magazine"]] = relationship("Magazine", back_populates="entity", cascade="all, delete-orphan")
    roles: Mapped[List["Role"]] = relationship(secondary=entity_roles, back_populates="entities")

    # Branding personalizado (1:1)
    branding: Mapped[Optional["EntityBranding"]] = relationship(
        "EntityBranding",
        back_populates="entity",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Configuración de vistas (1:N)
    view_configs: Mapped[List["EntityViewConfig"]] = relationship(
        "EntityViewConfig",
        back_populates="entity",
        cascade="all, delete-orphan"
    )

    # Recursos formativos
    resources: Mapped[List["Resource"]] = relationship(
        "Resource", back_populates="entity", cascade="all, delete-orphan"
    )
    resource_categories: Mapped[List["ResourceCategory"]] = relationship(
        "ResourceCategory", back_populates="entity", cascade="all, delete-orphan"
    )
