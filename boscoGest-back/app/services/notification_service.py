import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.notification_model import Notification, NotificationPreference
from app.models.membership_model import Membership
from app.models.user_model import User
from app.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationRepository,
    NotificationPreferenceRepository,
)
from app.services.notification_manager import notification_manager
from app.services import push_service
from app.utils.auth import get_sync_db

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    MAGAZINE_PUBLISHED = "magazine_published"
    ACTIVITY_CREATED = "activity_created"
    ACTIVITY_UPDATED = "activity_updated"
    REGISTRATION_ACCEPTED = "registration_accepted"
    REGISTRATION_REJECTED = "registration_rejected"
    COMMUNICATION_PUBLISHED = "communication_published"
    COMMENT_ADDED = "comment_added"
    RESOURCE_PUBLISHED = "resource_published"
    MEMBERSHIP_CREATED = "membership_created"
    MEMBERSHIP_REQUEST_CREATED = "membership_request_created"
    MEMBERSHIP_REQUEST_ACCEPTED = "membership_request_accepted"
    MEMBERSHIP_REQUEST_REJECTED = "membership_request_rejected"
    CHAT_MESSAGE_RECEIVED = "chat_message_received"
    FEE_GENERATED = "fee_generated"
    FEE_REMINDER = "fee_reminder"
    FEE_PAID = "fee_paid"
    FEE_OVERDUE = "fee_overdue"
    FEE_RENEWED = "fee_renewed"
    FEE_PROOF_SUBMITTED = "fee_proof_submitted"
    FEE_PROOF_REJECTED = "fee_proof_rejected"


# Human-readable descriptions for preference UI
EVENT_TYPE_LABELS: Dict[str, str] = {
    EventType.MAGAZINE_PUBLISHED: "Nueva revista publicada",
    EventType.ACTIVITY_CREATED: "Nueva actividad creada",
    EventType.ACTIVITY_UPDATED: "Actividad actualizada",
    EventType.REGISTRATION_ACCEPTED: "Inscripción aceptada",
    EventType.REGISTRATION_REJECTED: "Inscripción rechazada",
    EventType.COMMUNICATION_PUBLISHED: "Nueva comunicación publicada",
    EventType.COMMENT_ADDED: "Nuevo comentario",
    EventType.RESOURCE_PUBLISHED: "Nuevo recurso publicado",
    EventType.MEMBERSHIP_CREATED: "Membresía creada",
    EventType.MEMBERSHIP_REQUEST_CREATED: "Nueva solicitud de membresía",
    EventType.MEMBERSHIP_REQUEST_ACCEPTED: "Solicitud de membresía aceptada",
    EventType.MEMBERSHIP_REQUEST_REJECTED: "Solicitud de membresía rechazada",
    EventType.CHAT_MESSAGE_RECEIVED: "Nuevo mensaje de chat",
    EventType.FEE_GENERATED: "Nueva cuota asignada",
    EventType.FEE_REMINDER: "Recordatorio de cuota pendiente",
    EventType.FEE_PAID: "Cuota pagada",
    EventType.FEE_PROOF_SUBMITTED: "Justificante de pago recibido",
    EventType.FEE_PROOF_REJECTED: "Justificante devuelto",
    EventType.FEE_OVERDUE: "Cuota vencida",
    EventType.FEE_RENEWED: "Cuota renovada",
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.preference_repo = NotificationPreferenceRepository(db)
        self.device_repo = DeviceTokenRepository(db)

    # ── Public API: emit notification ────────────────────────────────

    def notify(
        self,
        event_type: str,
        entity_id: int | None,
        actor: User | None,
        resource_type: str,
        resource_id: int | None = None,
        title: str = "",
        body: str | None = None,
        data: Dict[str, Any] | None = None,
        recipient_ids: List[int] | None = None,
    ) -> List[Notification]:
        """
        Create notifications for the appropriate recipients and enqueue
        WebSocket pushes for online users.

        Args:
            recipient_ids: Explicit list of user IDs.  If None, resolved
                           automatically from entity memberships.
        """
        actor_id = actor.id if actor else None
        if recipient_ids is None:
            if entity_id is None:
                raise ValueError('An entity is required to resolve notification recipients')
            recipient_ids = self._resolve_entity_members(entity_id, exclude_id=actor_id)
        else:
            recipient_ids = [uid for uid in recipient_ids if uid != actor_id]

        if not recipient_ids:
            return []

        in_app_ids = self._filter_by_preferences(recipient_ids, event_type) if entity_id is not None else []
        push_ids = recipient_ids if event_type == EventType.CHAT_MESSAGE_RECEIVED else in_app_ids
        notifications = self.notification_repo.bulk_create(
            [
                Notification(
                    recipient_id=uid,
                    actor_id=actor_id,
                    event_type=event_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    entity_id=entity_id,
                    title=title,
                    body=body,
                    data=data,
                )
                for uid in in_app_ids
            ]
        ) if in_app_ids else []
        if notifications:
            self.db.commit()

        # Push to WebSocket for online users
        for n in notifications:
            notification_manager.enqueue(
                n.recipient_id,
                {
                    "id": n.id,
                    "event_type": n.event_type,
                    "resource_type": n.resource_type,
                    "resource_id": n.resource_id,
                    "entity_id": n.entity_id,
                    "title": n.title,
                    "body": n.body,
                    "data": n.data,
                    "actor": (
                        {"id": actor.id, "name": actor.name, "surname": actor.surname}
                        if actor else None
                    ),
                    "is_read": False,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                },
            )

        self._push(
            push_ids, event_type, title, body, resource_type, resource_id
        )

        return notifications

    def _push(
        self,
        recipient_ids: List[int],
        event_type: str,
        title: str,
        body: str | None,
        resource_type: str,
        resource_id: int | None,
    ) -> None:
        """Un chat debe avisar al móvil incluso con una sesión web conectada."""
        destinatarios = [
            uid for uid in recipient_ids
            if event_type == EventType.CHAT_MESSAGE_RECEIVED or not notification_manager.is_online(uid)
        ]
        if not destinatarios:
            return

        destinatarios = self._filter_push_disabled(destinatarios, event_type)

        for uid in destinatarios:
            try:
                push_service.send_to_user(
                    self.db,
                    uid,
                    title='Nuevo mensaje' if event_type == EventType.CHAT_MESSAGE_RECEIVED else title,
                    body='Abre la conversación para leerlo.' if event_type == EventType.CHAT_MESSAGE_RECEIVED else body,
                    # Solo identificadores: el aviso se ve en la pantalla
                    # bloqueada y no debe llevar datos personales. El cliente
                    # los usa para abrir la pantalla que toca al pulsarlo.
                    data={
                        "event_type": event_type.value if isinstance(event_type, EventType) else event_type,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                    },
                )
            except Exception:
                logger.warning(
                    "Fallo enviando push al usuario %s", uid, exc_info=True
                )

    def _filter_push_disabled(
        self, user_ids: List[int], event_type: str
    ) -> List[int]:
        """Quita a quien haya apagado el push para este tipo de evento.

        Aparte del filtro in-app: alguien puede querer ver el aviso dentro de
        la aplicación pero no que le suene el móvil.
        """
        disabled_stmt = select(NotificationPreference.user_id).where(
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.event_type == event_type,
            NotificationPreference.push_enabled == False,
        )
        disabled_ids = set(self.db.execute(disabled_stmt).scalars().all())
        return [uid for uid in user_ids if uid not in disabled_ids]

    # ── Dispositivos ─────────────────────────────────────────────────

    def register_device(self, user_id: int, token: str, platform: str):
        device = self.device_repo.register(user_id, token, platform)
        self.db.commit()
        return device

    def unregister_device(self, user_id: int, token: str) -> bool:
        removed = self.device_repo.unregister(token, user_id)
        self.db.commit()
        return removed

    # ── Read operations (for router) ─────────────────────────────────

    def list_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        event_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        return self.notification_repo.get_by_user(
            user_id,
            unread_only=unread_only,
            event_type=event_type,
            skip=skip,
            limit=limit,
        )

    def get_unread_count(self, user_id: int) -> int:
        return self.notification_repo.count_unread(user_id)

    def mark_read(self, notification_id: int, user_id: int) -> bool:
        result = self.notification_repo.mark_read(notification_id, user_id)
        self.db.commit()
        return result

    def mark_all_read(self, user_id: int) -> int:
        count = self.notification_repo.mark_all_read(user_id)
        self.db.commit()
        return count

    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        result = self.notification_repo.hard_delete(notification_id, user_id)
        self.db.commit()
        return result

    # ── Preferences ──────────────────────────────────────────────────

    def get_preferences(self, user_id: int) -> List[NotificationPreference]:
        return self.preference_repo.get_by_user(user_id)

    def update_preferences(
        self, user_id: int, preferences: list
    ) -> List[NotificationPreference]:
        results = []
        for pref in preferences:
            results.append(
                self.preference_repo.upsert(
                    user_id=user_id,
                    event_type=pref.event_type,
                    in_app_enabled=pref.in_app_enabled,
                    email_enabled=pref.email_enabled,
                    push_enabled=pref.push_enabled,
                )
            )
        self.db.commit()
        return results

    # ── Private helpers ──────────────────────────────────────────────

    def _resolve_entity_members(
        self, entity_id: int, exclude_id: int | None = None
    ) -> List[int]:
        """Get all active user IDs with membership in the given entity."""
        stmt = select(Membership.user_id).where(
            Membership.entity_id == entity_id,
            Membership.is_active == True,
        )
        if exclude_id is not None:
            stmt = stmt.where(Membership.user_id != exclude_id)
        return list(self.db.execute(stmt).scalars().all())

    def _filter_by_preferences(
        self, user_ids: List[int], event_type: str
    ) -> List[int]:
        """Remove users who explicitly disabled this event type."""
        disabled_stmt = select(NotificationPreference.user_id).where(
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.event_type == event_type,
            NotificationPreference.in_app_enabled == False,
        )
        disabled_ids = set(self.db.execute(disabled_stmt).scalars().all())
        return [uid for uid in user_ids if uid not in disabled_ids]


def get_notification_service(
    db: Session = Depends(get_sync_db),
) -> NotificationService:
    return NotificationService(db)
