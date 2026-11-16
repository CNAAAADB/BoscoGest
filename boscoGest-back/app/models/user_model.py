from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, TIMESTAMP, func, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .relationships import user_groups, user_permissions
from app.database import Base

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    name: Mapped[str] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    birthdate: Mapped[datetime] = mapped_column(Date)
    dni: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(Text)
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    size: Mapped[Optional[str]] = mapped_column(String(10))
    hobbies: Mapped[Optional[str]] = mapped_column(Text)
    job_position: Mapped[Optional[str]] = mapped_column(String(100))

    # GDPR: consent to the data-processing clause, recorded on first login
    # right after the forced password change. The version is stored alongside
    # the timestamp so consent can be requested again when the clause changes —
    # a bare boolean could not tell who agreed to which text.
    consent_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    consent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    direct_permissions: Mapped[List["Permission"]] = relationship(secondary=user_permissions, back_populates="users")
    groups: Mapped[List["Group"]] = relationship(secondary=user_groups, back_populates="users")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")
    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    fee_assignments: Mapped[List["FeeAssignment"]] = relationship(
        "FeeAssignment", foreign_keys="FeeAssignment.user_id", back_populates="user"
    )
