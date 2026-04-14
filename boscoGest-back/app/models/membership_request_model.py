from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MembershipRequest(Base):
    __tablename__ = "membership_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "rejected", name="membership_request_status"),
        default="pending",
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="joined")
    entity: Mapped["Entity"] = relationship(foreign_keys=[entity_id], lazy="joined")
    reviewed_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[reviewed_by_id], lazy="select"
    )

    __table_args__ = (
        Index("ix_membership_requests_entity_status", "entity_id", "status"),
        Index("ix_membership_requests_user", "user_id"),
    )
