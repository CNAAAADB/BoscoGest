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

The same machinery serves the "forgot my password" links, with ``purpose``
set to ``reset``. Those differ in two ways: they live two hours, because
they are asked for on the spot by whoever is about to use them, and spending
one does not open a session by itself — it has to come with the new password.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import config
from app.models.activation_token_model import ActivationToken
from app.models.user_model import User

logger = logging.getLogger(__name__)

PURPOSE_ACTIVATION = "activation"
PURPOSE_RESET = "reset"

# Long enough to survive a weekend, short enough not to be a standing credential.
TOKEN_TTL_HOURS = 72

# Someone who asks for a reset link is waiting for it, so this can be short.
# Two hours rather than one leaves room for a message that is slow to arrive
# or for someone who needs help opening it.
RESET_TTL_HOURS = 2

# The reset form is open to anyone. Without a pause between links it would let
# a stranger fill someone's inbox, one request at a time.
RESET_COOLDOWN = timedelta(minutes=2)

_TTL_HOURS = {PURPOSE_ACTIVATION: TOKEN_TTL_HOURS, PURPOSE_RESET: RESET_TTL_HOURS}

# 32 bytes of urlsafe base64 — 256 bits. Guessing is not a threat model.
TOKEN_BYTES = 32


def hash_token(raw_token: str) -> str:
    """The form kept in the database. Never store the secret itself."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_activation_url(raw_token: str) -> str:
    """The address that goes in the email."""
    base = config.APP_BASE_URL.rstrip("/")
    return f"{base}/activar?token={quote(raw_token, safe='')}"


def build_reset_url(raw_token: str) -> str:
    """The address that goes in the forgotten-password email."""
    base = config.APP_BASE_URL.rstrip("/")
    return f"{base}/restablecer?token={quote(raw_token, safe='')}"


def issue_token(db: Session, user: User, purpose: str = PURPOSE_ACTIVATION) -> str:
    """Create a link for this user and return the secret to email them.

    Any outstanding link of the same kind is invalidated first: a second
    welcome email must not leave the first one working, or revoking access
    would mean hunting down every message ever sent.

    Commits, because the caller is usually a background task with no
    transaction of its own, and because the link must be durable before the
    email quoting it goes out.
    """
    invalidate_tokens_for_user(db, user.id, commit=False, purpose=purpose)

    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(
        ActivationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(hours=_TTL_HOURS[purpose]),
            # Set here rather than left to the database's now(), which follows
            # the server's time zone: issued_recently compares it with utcnow.
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return raw_token


def invalidate_tokens_for_user(
    db: Session, user_id: int, commit: bool = True, purpose: str | None = None
) -> int:
    """Burn every unused link this person holds. Returns how many.

    Called when a password is set — from the first-login screen, a reset or a
    regular change — so a link that is still in an inbox cannot be replayed
    afterwards. ``purpose`` limits it to one kind, for when a fresh link of
    that kind replaces the old ones.
    """
    conditions = [
        ActivationToken.user_id == user_id,
        ActivationToken.used_at.is_(None),
    ]
    if purpose is not None:
        conditions.append(ActivationToken.purpose == purpose)
    result = db.execute(
        update(ActivationToken)
        .where(*conditions)
        .values(used_at=datetime.utcnow())
    )
    if commit:
        db.commit()
    return result.rowcount or 0


def issued_recently(db: Session, user_id: int, purpose: str, within: timedelta) -> bool:
    """Whether a link of this kind went out to this person a moment ago."""
    latest = db.execute(
        select(func.max(ActivationToken.created_at)).where(
            ActivationToken.user_id == user_id,
            ActivationToken.purpose == purpose,
        )
    ).scalar()
    return latest is not None and latest > datetime.utcnow() - within


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


_MESSAGES = {
    PURPOSE_ACTIVATION: {
        "used": (
            "Este enlace ya se ha utilizado. Si aún no tienes contraseña, "
            "pide uno nuevo."
        ),
        "expired": (
            "Este enlace ha caducado. Los enlaces de acceso duran 72 horas; "
            "pide uno nuevo para entrar."
        ),
    },
    PURPOSE_RESET: {
        "used": (
            "Este enlace ya se ha utilizado. Si sigues sin poder entrar, "
            "pide uno nuevo."
        ),
        "expired": (
            f"Este enlace ha caducado. Los enlaces para cambiar la contraseña "
            f"duran {RESET_TTL_HOURS} horas; pide uno nuevo."
        ),
    },
}


def redeem_token(db: Session, raw_token: str, purpose: str = PURPOSE_ACTIVATION) -> User:
    """Spend a link and return the user it belongs to.

    Raises ActivationError when it cannot be spent. The token is marked used
    with a conditional update rather than a read-then-write, so two clicks
    arriving together cannot both come back with a session.

    A link of another kind counts as not existing: a reset link is no way to
    sign in without choosing a password, and a welcome link is not taken on
    the reset screen either.
    """
    messages = _MESSAGES[purpose]
    token = db.execute(
        select(ActivationToken).where(
            ActivationToken.token_hash == hash_token(raw_token),
            ActivationToken.purpose == purpose,
        )
    ).scalars().first()

    if token is None:
        raise ActivationError(
            "invalid",
            "Este enlace no es válido. Comprueba que lo has copiado entero.",
        )

    if token.used_at is not None:
        raise ActivationError("used", messages["used"])

    if token.expires_at < datetime.utcnow():
        raise ActivationError("expired", messages["expired"])

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
        raise ActivationError("used", messages["used"])

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise ActivationError(
            "invalid",
            "La cuenta asociada a este enlace ya no está disponible.",
        )

    db.commit()
    return user
