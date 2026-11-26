"""Board/committee appointments, independent of application authorization roles.

A person may hold several appointments in the same association or different
entities. An appointment NEVER grants permissions in BoscoGest.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BoardPosition(Base):
    __tablename__ = "board_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_id", "normalized_title",
                         name="uq_board_position_per_entity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_code: Mapped[str] = mapped_column(String(30), nullable=False)
    custom_title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    normalized_title: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
