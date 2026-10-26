from datetime import datetime
from typing import Optional
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ActivationToken(Base):
    """A one-shot link letting someone sign in for the first time.

    People created by an administrator — one at a time or through a CSV import
    — never learn the password generated for them. The welcome email carries a
    link instead, and following it signs them in exactly once, long enough to
    choose their own password.

    Only the hash of the secret is kept. A leaked database therefore yields no
    usable links, the same reasoning that applies to passwords: the column is
    a credential, not a reference.
    """

    __tablename__ = "activation_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # SHA-256 of the secret handed out in the email, hex-encoded.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    # Set the moment the link is followed. Its presence is what makes the link
    # single-use, and it is written with a conditional update so two
    # simultaneous requests cannot both succeed.
    used_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), nullable=False
    )

    user = relationship("User")

    __table_args__ = (
        # Finding a user's outstanding links, to invalidate them once they have
        # a password or to replace them with a fresh one.
        Index("ix_activation_tokens_user", "user_id"),
    )
