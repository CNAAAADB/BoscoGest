from typing import List, Optional
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.activity_model import Activity
from app.models.activity_registration_model import ActivityRegistration
from app.models.membership_model import Membership
from app.models.user_model import User
from app.schemas.activity import ActivityCreate, ActivityUpdate, check_end_after_start
from app.repositories.activity_repository import ActivityRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_repo = ActivityRepository(db)
        self.auth_service = AuthorizationService(db)
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

    def get_entities_with_create_permission(self, current_user: User) -> list:
        """
        Return entities where the current user has permission to create activities.
        Checks active memberships and their role permissions.
        """
        memberships = (
            self.db.query(Membership)
            .filter(
                Membership.user_id == current_user.id,
                Membership.is_active == True,
            )
            .all()
        )

        entities_with_permission = []
        for membership in memberships:
            for permission in membership.role.permissions:
                if (
                    permission.resource == "activities"
                    and permission.action == "create"
                ):
                    if membership.entity.is_active:
                        entities_with_permission.append(membership.entity)
                    break

        return entities_with_permission

    # ── Activity CRUD ───────────────────────────────────────────────

    def create_activity(
        self, activity_in: ActivityCreate, current_user: User
    ) -> Activity:
        self.auth_service.check_entity_permission(
            current_user, activity_in.entity_id, "activities", "create"
        )

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
        """List active activities from entities where the user has a membership."""
        entity_ids = self.activity_repo.get_accessible_entity_ids(current_user.id)
        if not entity_ids:
            return []

        activities = self.activity_repo.get_by_entity_ids(
            entity_ids, with_entity=True
        )
        return self._resolve_images(activities)

    def get_activity(self, activity_id: int) -> Activity:
        activity = self.activity_repo.get_by_id_with_entity(activity_id)
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )
        return self._resolve_images(activity)

    def update_activity(
        self,
        activity_id: int,
        activity_in: ActivityUpdate,
        current_user: User,
    ) -> Activity:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "update"
        )

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
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "delete"
        )

        activity.is_active = False
        self.db.commit()
        return {"detail": "Actividad eliminada correctamente"}

    # ── Registrations ───────────────────────────────────────────────

    def register_activity(
        self, activity_id: int, current_user: User
    ) -> ActivityRegistration:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        # Verify user belongs to the activity's entity
        membership_entity_ids = [m.entity_id for m in current_user.memberships]
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

        # Capacity and waitlist logic
        accepted_count = self.activity_repo.count_accepted_registrations(activity_id)
        if accepted_count < activity.capacity:
            status_value = "accepted"
        elif activity.allow_waitlist:
            status_value = "waitlist"
        else:
            raise HTTPException(
                status_code=400,
                detail="Aforo completo y sin lista de espera",
            )

        registration = ActivityRegistration(
            activity_id=activity_id,
            user_id=current_user.id,
            status=status_value,
        )
        self.activity_repo.create_registration(registration)
        self.db.commit()
        self.db.refresh(registration)
        return registration

    def get_my_registration(
        self, activity_id: int, current_user: User
    ) -> Optional[ActivityRegistration]:
        return self.activity_repo.get_active_registration(
            activity_id, current_user.id
        )

    def list_registrations(
        self, activity_id: int, current_user: User
    ) -> List[ActivityRegistration]:
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "manage"
        )

        # Filter only active registrations
        return [r for r in activity.registrations if r.is_active]

    def create_chat_group(self, activity_id: int, current_user: User) -> dict:
        """Create a chat group with all admitted participants of the activity.
        Only the activity creator or a user who can manage activities in the
        entity may do this."""
        from app.services.chat_service import ChatService

        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        is_creator = activity.created_by_id == current_user.id
        can_manage = self.auth_service.has_effective_permission(
            current_user, activity.entity_id, "activities", "manage"
        )
        if not (is_creator or can_manage):
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
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "manage"
        )

        registration = self.activity_repo.get_registration(activity_id, user_id)
        if not registration:
            raise HTTPException(
                status_code=404, detail="Inscripción no encontrada"
            )

        # Verify capacity
        accepted_count = self.activity_repo.count_accepted_registrations(activity_id)
        if accepted_count >= activity.capacity:
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
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "manage"
        )

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
        if not activity:
            raise HTTPException(
                status_code=404, detail="Actividad no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user, activity.entity_id, "activities", "update"
        )

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
