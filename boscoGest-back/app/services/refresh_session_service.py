"""Rotating, hashed refresh credentials for web and mobile sessions."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_session_model import RefreshSession
from app.models.user_model import User
from app.utils.auth import create_access_token

SESSION_DAYS = 30


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="La sesión ha caducado. Vuelve a iniciar sesión.",
    )


def create_session(db: Session, user: User) -> tuple[str, str]:
    """Issue an access token and a random refresh secret for one device."""
    raw = secrets.token_urlsafe(48)
    row = RefreshSession(
        user_id=user.id,
        family_id=str(uuid.uuid4()),
        token_hash=_hash(raw),
        expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
    )
    db.add(row)
    db.commit()
    return create_access_token({"sub": str(user.id)}), raw


def rotate_session(db: Session, raw: str) -> tuple[str, str]:
    """Exchange once, revoking the old credential. Concurrent replays fail.

    SELECT FOR UPDATE serializes rotations on PostgreSQL, so two simultaneous
    uses of the same credential cannot both create valid child credentials.
    """
    if not raw or len(raw) > 256:
        raise _unauthorized()
    now = datetime.utcnow()
    row = db.execute(
        select(RefreshSession)
        .where(RefreshSession.token_hash == _hash(raw))
        .with_for_update()
    ).scalars().first()
    if row is None:
        raise _unauthorized()
    if row.revoked_at is not None:
        # Multiple tabs or a delayed retry can replay a token immediately
        # after successful rotation. Reject it, but do not destroy the
        # legitimate session for a transient race (<30 seconds).
        if now - row.revoked_at <= timedelta(seconds=30):
            raise _unauthorized()
        # A later replay is suspicious: revoke its device token family.
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == row.user_id,
                RefreshSession.family_id == row.family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        db.commit()
        raise _unauthorized()
    user = db.get(User, row.user_id)
    if row.expires_at <= now or user is None or not user.is_active:
        row.revoked_at = now
        db.commit()
        raise _unauthorized()
    row.revoked_at = now
    fresh = secrets.token_urlsafe(48)
    db.add(
        RefreshSession(
            user_id=row.user_id,
            family_id=row.family_id,
            token_hash=_hash(fresh),
            expires_at=now + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return create_access_token({"sub": str(user.id)}), fresh


def revoke_session(db: Session, raw: str | None) -> None:
    """Invalidate the entire device family, without revealing if it existed."""
    if not raw or len(raw) > 256:
        return
    row = db.execute(
        select(RefreshSession).where(RefreshSession.token_hash == _hash(raw))
    ).scalars().first()
    if row:
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == row.user_id,
                RefreshSession.family_id == row.family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        db.commit()


def revoke_user_sessions(db: Session, user_id: int) -> None:
    """Revoke all devices when a password changes or an account is removed."""
    db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.utcnow())
    )
    db.commit()
