from typing import List, Optional
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.activity_model import Activity
from app.models.activity_registration_model import ActivityRegistration
from app.models.entity_model import Entity
from sqlalchemy import select
from app.models.user_model import User
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse, ActivityPermissions, check_end_after_start
from app.repositories.activity_repository import ActivityRepository
from app.services.scoped_permissions import ScopedPermissions
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_repo = ActivityRepository(db)
        self.scope = ScopedPermissions(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    # ── Image resolution ────────────────────────────────────────────

    @staticmethod
    def _resolve_images(activities):
        """Convert S3 keys to presigned URLs for activity image_url fields."""
        if isinstance(activities, list):
            for a in activities:
                if (
                    a.image_url
                    and not a.image_url.startswith("http")
                    and not a.image_url.startswith("/uploads")
                ):
                    a.image_url = storage.get_presigned_url(a.image_url)
            return activities
        if (
            activities
            and activities.image_url
            and not activities.image_url.startswith("http")
            and not activities.image_url.startswith("/uploads")
        ):
            activities.image_url = storage.get_presigned_url(activities.image_url)
        return activities

    # ── Entity permissions ──────────────────────────────────────────

    def _active_memberships(self, user: User):
        return self.scope.active_memberships(user)

    def _admin_entity_ids(self, user: User, action: str) -> set[int]:
        return self.scope.ids(user, "activities", action)

    def _can_admin(self, user: User, entity_id: int, action: str) -> bool:
        return entity_id in self._admin_entity_ids(user, action)

    def _check_admin(self, user: User, entity_id: int, action: str) -> None:
        if not self._can_admin(user, entity_id, action):
            raise HTTPException(status_code=403, detail="No tienes permisos sobre esta actividad")

    def _member_entity_ids(self, user: User) -> set[int]:
        return {m.entity_id for m in self._active_memberships(user)}

    def _visible_entity_ids(self, user: User) -> set[int]:
        ids = self._member_entity_ids(user)
        for action in ("create", "update", "delete", "manage"):
            ids.update(self._admin_entity_ids(user, action))
        return ids

    def _permissions(self, user: User, activity: Activity) -> ActivityPermissions:
        manage = self._can_admin(user, activity.entity_id, "manage")
        return ActivityPermissions(
            can_edit=self._can_admin(user, activity.entity_id, "update"),
            can_delete=self._can_admin(user, activity.entity_id, "delete"),
            can_manage_registrations=manage,
            can_create_chat_group=manage or (
                activity.created_by_id == user.id
                and self._can_admin(user, activity.entity_id, "create")
            ),
            can_register=activity.entity_id in self._member_entity_ids(user),
        )

    def get_entities_with_create_permission(self, current_user: User) -> list:
        ids = self._admin_entity_ids(current_user, "create")
        return list(self.db.scalars(
            select(Entity).where(Entity.id.in_(ids)).order_by(Entity.name)
        ).all())

    # ── Activity CRUD ───────────────────────────────────────────────

    def create_activity(
        self, activity_in: ActivityCreate, current_user: User
    ) -> Activity:
        self._check_admin(current_user, activity_in.entity_id, "create")

        db_activity = Activity(
            **activity_in.model_dump(), created_by_id=current_user.id
        )
        self.activity_repo.create(db_activity)
        self.db.commit()
        self.db.refresh(db_activity)

        self.notification_service.notify(
            event_type=EventType.ACTIVITY_CREATED,
            entity_id=activity_in.entity_id,
            actor=current_user,
            resource_type="activities",
            resource_id=db_activity.id,
            title=f"Nueva actividad: {db_activity.title}",
        )

        return self._resolve_images(db_activity)

    def list_activities(self, current_user: User) -> List[Activity]:
        """List activities from active memberships and administrable descendants."""
        entity_ids = list(self._visible_entity_ids(current_user))
        if not entity_ids:
            return []

        activities = self.activity_repo.get_by_entity_ids(
            entity_ids, with_entity=True
        )
        return self._resolve_images(activities)

    def get_activity(self, activity_id: int, current_user: User) -> ActivityResponse:
        activity = self.activity_repo.get_by_id_with_entity(activity_id)
        if not activity or not activity.is_active or activity.entity_id not in self._visible_entity_ids(current_user):
            raise HTTPException(status_code=404, detail="Actividad no encontrada")
        return ActivityResponse.model_validate(self._resolve_images(activity)).model_copy(
            update={"permissions": self._permissions(current_user, activity)}
        )

    def update_activity(
        self,
        activity_id: int,
        activity_in: ActivityUpdate,
        current_user: User,
    ) -> Activity:
        activity = self.activity_repo.lock_activity(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "update")

        changes = activity_in.model_dump(exclude_unset=True)
        # Either end may change alone, so the check is against the result: a
        # new start can overtake the end already stored, and the other way round.
        try:
            check_end_after_start(
                changes.get("date", activity.date),
                changes.get("end_date", activity.end_date),
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        for field, value in changes.items():
            setattr(activity, field, value)

        self.db.commit()
        self.db.refresh(activity)

        self.notification_service.notify(
            event_type=EventType.ACTIVITY_UPDATED,
            entity_id=activity.entity_id,
            actor=current_user,
            resource_type="activities",
            resource_id=activity_id,
            title=f"Actividad actualizada: {activity.title}",
        )

        return self._resolve_images(activity)

    def delete_activity(self, activity_id: int, current_user: User) -> dict:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "delete")

        activity.is_active = False
        self.db.commit()
        return {"detail": "Actividad eliminada correctamente"}

    # ── Registrations ───────────────────────────────────────────────

    def register_activity(
        self, activity_id: int, current_user: User, guest_count: int = 0
    ) -> ActivityRegistration:
        activity = self.activity_repo.lock_activity(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        # Verify user belongs to the activity's entity
        membership_entity_ids = self._member_entity_ids(current_user)
        if activity.entity_id not in membership_entity_ids:
            raise HTTPException(
                status_code=403,
                detail="No perteneces a la entidad de esta actividad",
            )

        existing = self.activity_repo.get_registration(activity_id, current_user.id)
        if existing:
            raise HTTPException(
                status_code=400, detail="Ya estás inscrito en esta actividad"
            )

        if guest_count and not activity.allow_guests:
            raise HTTPException(status_code=400, detail='Esta actividad no admite acompañantes')

        # Capacity and waitlist logic
        accepted_count = self.activity_repo.count_occupied_seats(activity_id)
        if accepted_count + 1 + guest_count <= activity.capacity:
            status_value = "accepted"
        elif activity.allow_waitlist:
            status_value = "waitlist"
        else:
            raise HTTPException(
                status_code=400,
                detail="No hay plazas suficientes y la actividad no tiene lista de espera",
            )

        registration = ActivityRegistration(
            activity_id=activity_id,
            user_id=current_user.id,
            status=status_value,
            guest_count=guest_count,
        )
        self.activity_repo.create_registration(registration)
        self.db.commit()
        self.db.refresh(registration)
        return registration

    def get_my_registration(
        self, activity_id: int, current_user: User
    ) -> Optional[ActivityRegistration]:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active or activity.entity_id not in self._visible_entity_ids(current_user):
            raise HTTPException(status_code=404, detail="Actividad no encontrada")
        return self.activity_repo.get_active_registration(
            activity_id, current_user.id
        )

    def list_registrations(
        self, activity_id: int, current_user: User
    ) -> List[ActivityRegistration]:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "manage")

        # Filter only active registrations
        return [r for r in activity.registrations if r.is_active]

    def create_chat_group(self, activity_id: int, current_user: User) -> dict:
        """Create a chat group with all admitted participants of the activity.
        Only the activity creator or a user who can manage activities in the
        entity may do this."""
        from app.services.chat_service import ChatService

        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        if not self._permissions(current_user, activity).can_create_chat_group:
            raise HTTPException(
                status_code=403,
                detail="Solo el responsable de la actividad puede crear el grupo",
            )

        accepted_user_ids = [
            r.user_id
            for r in activity.registrations
            if r.is_active and r.status == "accepted"
        ]

        chat_service = ChatService(self.db)
        conv = chat_service.create_group(
            current_user,
            name=activity.title,
            description=f"Grupo de la actividad «{activity.title}»",
        )

        # Add every admitted participant (the creator is already the group admin).
        for uid in accepted_user_ids:
            if uid == current_user.id:
                continue
            if chat_service.repo.get_member(conv.id, uid):
                continue
            chat_service.repo.add_member(conv.id, uid)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create_chat_group",
            resource_type="activities",
            resource_id=activity_id,
            details={
                "conversation_id": conv.id,
                "members_added": len(accepted_user_ids),
            },
        )

        return {"conversation_id": conv.id, "name": conv.name}

    def accept_registration(
        self, activity_id: int, user_id: int, current_user: User
    ) -> ActivityRegistration:
        activity = self.activity_repo.lock_activity(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "manage")

        registration = self.activity_repo.get_registration(activity_id, user_id)
        if not registration:
            raise HTTPException(
                status_code=404, detail="Inscripción no encontrada"
            )

        if registration.status == 'accepted':
            return registration

        # Verify capacity
        accepted_count = self.activity_repo.count_occupied_seats(activity_id)
        if accepted_count + 1 + registration.guest_count > activity.capacity:
            raise HTTPException(
                status_code=400, detail="No hay aforo disponible"
            )

        registration.status = "accepted"
        self.db.commit()
        self.db.refresh(registration)

        self.notification_service.notify(
            event_type=EventType.REGISTRATION_ACCEPTED,
            entity_id=activity.entity_id,
            actor=current_user,
            resource_type="activities",
            resource_id=activity_id,
            title=f"Inscripción aceptada: {activity.title}",
            recipient_ids=[user_id],
        )

        return registration

    def reject_registration(
        self, activity_id: int, user_id: int, current_user: User
    ) -> ActivityRegistration:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "manage")

        registration = self.activity_repo.get_registration(activity_id, user_id)
        if not registration:
            raise HTTPException(
                status_code=404, detail="Inscripción no encontrada"
            )

        registration.status = "rejected"
        self.db.commit()
        self.db.refresh(registration)

        self.notification_service.notify(
            event_type=EventType.REGISTRATION_REJECTED,
            entity_id=activity.entity_id,
            actor=current_user,
            resource_type="activities",
            resource_id=activity_id,
            title=f"Inscripción rechazada: {activity.title}",
            recipient_ids=[user_id],
        )

        return registration

    # ── Image upload ────────────────────────────────────────────────

    def upload_image(
        self,
        activity_id: int,
        file_contents: bytes,
        filename: str,
        content_type: str,
        current_user: User,
    ) -> dict:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity or not activity.is_active:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self._check_admin(current_user, activity.entity_id, "update")

        if not content_type or not content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="El archivo debe ser una imagen"
            )

        unique_filename = f"{uuid4().hex}_{filename}"
        s3_key = f"activities/{unique_filename}"

        storage.upload(s3_key, file_contents, content_type or "image/jpeg")

        activity.image_url = s3_key
        self.db.commit()
        self.db.refresh(activity)

        image_url = storage.get_presigned_url(s3_key)
        return {"image_url": image_url}


def get_activity_service(
    db: Session = Depends(get_sync_db),
) -> ActivityService:
    return ActivityService(db)
