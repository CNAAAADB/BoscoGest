from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, TIMESTAMP, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsentClause(Base):
    """A version of the GDPR data-processing clause.

    Rows are append-only once published. Editing the text a user already
    accepted would destroy the evidence of what they agreed to, which is
    precisely what the accountability principle requires you to be able to
    show — so a change publishes a new version instead.

    The clause is platform-wide rather than per-entity: there is a single
    level-1 entity, and every member of every association is processed under
    the same terms.
    """

    __tablename__ = "consent_clauses"

    __table_args__ = (
        # Exactly one clause may be in force. Declared here rather than only in
        # the migration so autogenerate knows it exists — otherwise every
        # subsequent revision proposes dropping it.
        Index(
            "ix_consent_clauses_single_published",
            "is_published",
            unique=True,
            # The predicate has to be spelled per dialect: a bare
            # postgresql_where is ignored elsewhere, and SQLite would then
            # build a *full* unique index on is_published — which also forbids
            # a second unpublished draft.
            postgresql_where=text("is_published"),
            sqlite_where=text("is_published"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Free-form so it can follow whatever scheme is wanted ("1.0", "2026-05").
    version: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Drafts can be edited; exactly one published row is the current clause.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
