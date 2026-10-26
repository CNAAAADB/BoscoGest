"""One-shot sign-in links for people who never learn their password.

An administrator creating a user — alone or through a CSV import — generates a
password nobody tells them. The welcome email carries a link instead. Following
it signs them in once, which is when they choose a password of their own.

The rules, and why each one is here:

* **Single use.** The link travels by email and stays in an inbox afterwards.
  Once followed, it stops working, so a forwarded or leaked message is no
  longer a way in.
* **Expiry.** Seventy-two hours by default. Long enough for someone who reads
  their mail on Monday after a Friday import, short enough that a stale message
  is not a standing credential.
* **Hashed at rest.** Only the SHA-256 of the secret is stored, so the table is
  useless to anyone who reads the database.
* **Superseded on use.** Setting a password invalidates every outstanding link
  for that person, including ones issued by a second import.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import config
from app.models.activation_token_model import ActivationToken
from app.models.user_model import User

logger = logging.getLogger(__name__)

# Long enough to survive a weekend, short enough not to be a standing credential.
TOKEN_TTL_HOURS = 72

# 32 bytes of urlsafe base64 — 256 bits. Guessing is not a threat model.
TOKEN_BYTES = 32


def hash_token(raw_token: str) -> str:
    """The form kept in the database. Never store the secret itself."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_activation_url(raw_token: str) -> str:
    """The address that goes in the email."""
    base = config.APP_BASE_URL.rstrip("/")
    return f"{base}/activar?token={quote(raw_token, safe='')}"


def issue_token(db: Session, user: User) -> str:
    """Create a link for this user and return the secret to email them.

    Any outstanding link is invalidated first: a second welcome email must not
    leave the first one working, or revoking access would mean hunting down
    every message ever sent.

    Commits, because the caller is usually a background task with no
    transaction of its own, and because the link must be durable before the
    email quoting it goes out.
    """
    invalidate_tokens_for_user(db, user.id, commit=False)

    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(
        ActivationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS),
        )
    )
    db.commit()
    return raw_token


def invalidate_tokens_for_user(db: Session, user_id: int, commit: bool = True) -> int:
    """Burn every unused link this person holds. Returns how many.

    Called when a password is set — from the first-login screen or by an
    administrator — so a link that is still in an inbox cannot be replayed
    afterwards.
    """
    result = db.execute(
        update(ActivationToken)
        .where(
            ActivationToken.user_id == user_id,
            ActivationToken.used_at.is_(None),
        )
        .values(used_at=datetime.utcnow())
    )
    if commit:
        db.commit()
    return result.rowcount or 0


class ActivationError(Exception):
    """A link that cannot be redeemed, with a reason worth showing.

    The three cases read very differently to the person holding the link, and
    collapsing them into one message would leave them with no idea what to do
    next.
    """

    def __init__(self, reason: str, message: str):
        # 'expired' | 'used' | 'invalid'
        self.reason = reason
        self.message = message
        super().__init__(message)


def redeem_token(db: Session, raw_token: str) -> User:
    """Spend a link and return the user it belongs to.

    Raises ActivationError when it cannot be spent. The token is marked used
    with a conditional update rather than a read-then-write, so two clicks
    arriving together cannot both come back with a session.
    """
    token = db.execute(
        select(ActivationToken).where(
            ActivationToken.token_hash == hash_token(raw_token)
        )
    ).scalars().first()

    if token is None:
        raise ActivationError(
            "invalid",
            "Este enlace no es válido. Comprueba que lo has copiado entero.",
        )

    if token.used_at is not None:
        raise ActivationError(
            "used",
            "Este enlace ya se ha utilizado. Si aún no tienes contraseña, "
            "pide uno nuevo.",
        )

    if token.expires_at < datetime.utcnow():
        raise ActivationError(
            "expired",
            "Este enlace ha caducado. Los enlaces de acceso duran 72 horas; "
            "pide uno nuevo para entrar.",
        )

    # Claim it. Whoever's UPDATE lands first is the one that gets the session:
    # the WHERE clause fails for the second, and rowcount says so.
    claimed = db.execute(
        update(ActivationToken)
        .where(
            ActivationToken.id == token.id,
            ActivationToken.used_at.is_(None),
        )
        .values(used_at=datetime.utcnow())
    )
    if not claimed.rowcount:
        db.rollback()
        raise ActivationError(
            "used",
            "Este enlace ya se ha utilizado. Si aún no tienes contraseña, "
            "pide uno nuevo.",
        )

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise ActivationError(
            "invalid",
            "La cuenta asociada a este enlace ya no está disponible.",
        )

    db.commit()
    return user
