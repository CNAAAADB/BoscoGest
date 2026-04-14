from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete, func
from app.models.notification_model import Notification, NotificationPreference
from app.repositories.base_repository import BaseRepository


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Notification)

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        return self.base.get_by_id(notification_id)

    def get_by_user(
        self,
        user_id: int,
        unread_only: bool = False,
        event_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        stmt = (
            select(Notification)
            .options(
                joinedload(Notification.actor),
                joinedload(Notification.entity),
            )
            .where(Notification.recipient_id == user_id)
        )

        if unread_only:
            stmt = stmt.where(Notification.is_read == False)

        if event_type:
            stmt = stmt.where(Notification.event_type == event_type)

        stmt = (
            stmt.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def count_unread(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read == False,
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def bulk_create(self, notifications: List[Notification]) -> List[Notification]:
        self.db.add_all(notifications)
        self.db.flush()
        for n in notifications:
            self.db.refresh(n)
        return notifications

    def mark_read(self, notification_id: int, user_id: int) -> bool:
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = self.db.execute(stmt)
        return result.rowcount > 0

    def mark_all_read(self, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = self.db.execute(stmt)
        return result.rowcount

    def hard_delete(self, notification_id: int, user_id: int) -> bool:
        stmt = delete(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        result = self.db.execute(stmt)
        return result.rowcount > 0


class NotificationPreferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> List[NotificationPreference]:
        stmt = (
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .order_by(NotificationPreference.event_type)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_user_and_event(
        self, user_id: int, event_type: str
    ) -> Optional[NotificationPreference]:
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.event_type == event_type,
        )
        return self.db.execute(stmt).scalars().first()

    def get_disabled_event_types(self, user_id: int) -> set[str]:
        """Return event types where in_app is explicitly disabled."""
        stmt = select(NotificationPreference.event_type).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.in_app_enabled == False,
        )
        return set(self.db.execute(stmt).scalars().all())

    def upsert(
        self,
        user_id: int,
        event_type: str,
        in_app_enabled: bool = True,
        email_enabled: bool = False,
    ) -> NotificationPreference:
        existing = self.get_by_user_and_event(user_id, event_type)
        if existing:
            existing.in_app_enabled = in_app_enabled
            existing.email_enabled = email_enabled
            self.db.flush()
            return existing

        pref = NotificationPreference(
            user_id=user_id,
            event_type=event_type,
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
        )
        self.db.add(pref)
        self.db.flush()
        self.db.refresh(pref)
        return pref
