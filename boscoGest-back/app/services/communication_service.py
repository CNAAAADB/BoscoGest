from datetime import datetime, timezone
from typing import List, Optional
import os
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.communication_model import Communication
from app.models.user_model import User
from app.schemas.communication import CommunicationCreate, CommunicationUpdate, VALID_TRANSITIONS
from app.models.membership_model import Membership
from app.repositories.communication_repository import CommunicationRepository
from app.services.authorization_service import AuthorizationService
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
        self.comm_repo = CommunicationRepository(db)
        self.auth_service = AuthorizationService(db)
        self.notification_service = NotificationService(db)

    @staticmethod
    def _resolve_images(communications):
        if isinstance(communications, list):
            for c in communications:
                if (
                    c.image_url
                    and not c.image_url.startswith("http")
                    and not c.image_url.startswith("/uploads")
                ):
                    c.image_url = storage.get_presigned_url(c.image_url)
            return communications
        if (
            communications
            and communications.image_url
            and not communications.image_url.startswith("http")
            and not communications.image_url.startswith("/uploads")
        ):
            communications.image_url = storage.get_presigned_url(
                communications.image_url
            )
        return communications

    def get_entities_with_create_permission(self, current_user: User) -> list:
        """Return entities where the user has permission to create communications."""
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
                    permission.resource == "communications"
                    and permission.action == "create"
                ):
                    if membership.entity.is_active:
                        entities_with_permission.append(membership.entity)
                    break

        return entities_with_permission

    def create_communication(
        self, communication_in: CommunicationCreate, current_user: User
    ) -> Communication:
        self.auth_service.check_entity_permission(
            current_user,
            communication_in.entity_id,
            "communications",
            "create",
        )

        # If publishing directly, check publish permission
        status = communication_in.status or "draft"
        if status == "published":
            self.auth_service.check_entity_permission(
                current_user,
                communication_in.entity_id,
                "communications",
                "publish",
            )

        data = communication_in.model_dump()
        data["status"] = status
        if status == "published":
            data["published_at"] = datetime.now(timezone.utc)

        db_communication = Communication(**data, created_by_id=current_user.id)
        self.comm_repo.create(db_communication)
        self.db.commit()
        self.db.refresh(db_communication)

        # Only notify when published
        if status == "published":
            self.notification_service.notify(
                event_type=EventType.COMMUNICATION_PUBLISHED,
                entity_id=communication_in.entity_id,
                actor=current_user,
                resource_type="communications",
                resource_id=db_communication.id,
                title=f"Nueva comunicación: {db_communication.title}",
            )

        return self._resolve_images(db_communication)

    def _can_review(self, current_user: User, entity_ids: List[int]) -> bool:
        """Check if user has review or publish permission in any of the entities."""
        for eid in entity_ids:
            try:
                self.auth_service.check_entity_permission(
                    current_user, eid, "communications", "review"
                )
                return True
            except HTTPException:
                pass
            try:
                self.auth_service.check_entity_permission(
                    current_user, eid, "communications", "publish"
                )
                return True
            except HTTPException:
                pass
        return False

    def list_communications(
        self, current_user: User, skip: int = 0, limit: int = 10,
        status: Optional[str] = None,
    ) -> List[Communication]:
        entity_ids = self.comm_repo.get_accessible_entity_ids(current_user.id)
        if not entity_ids:
            return []

        # Users with review/publish permission see all statuses; others only published
        if status:
            effective_status = status
            effective_statuses = None
        elif self._can_review(current_user, entity_ids):
            effective_status = None
            effective_statuses = None  # all statuses
        else:
            effective_status = "published"
            effective_statuses = None

        communications = self.comm_repo.get_by_entity_ids(
            entity_ids, skip=skip, limit=limit,
            status=effective_status, statuses=effective_statuses,
        )
        return self._resolve_images(communications)

    def count_communications(
        self, current_user: User, status: Optional[str] = None,
    ) -> dict:
        entity_ids = self.comm_repo.get_accessible_entity_ids(current_user.id)
        if not entity_ids:
            return {"total": 0}

        if status:
            effective_status = status
        elif not self._can_review(current_user, entity_ids):
            effective_status = "published"
        else:
            effective_status = None

        count = self.comm_repo.count_by_entity_ids(
            entity_ids, status=effective_status,
        )
        return {"total": count}

    def get_communication(
        self, communication_id: int, current_user: User
    ) -> Communication:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user,
            communication.entity_id,
            "communications",
            "read",
        )
        return self._resolve_images(communication)

    def update_communication(
        self,
        communication_id: int,
        communication_in: CommunicationUpdate,
        current_user: User,
    ) -> Communication:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        # Only draft and review communications can be edited
        if communication.status not in ("draft", "review"):
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden editar comunicaciones en estado borrador o revisión",
            )

        self.auth_service.check_entity_permission(
            current_user,
            communication.entity_id,
            "communications",
            "edit",
        )

        for field, value in communication_in.model_dump(exclude_unset=True).items():
            setattr(communication, field, value)

        self.db.commit()
        self.db.refresh(communication)
        return self._resolve_images(communication)

    def transition_status(
        self, communication_id: int, target_status: str, current_user: User,
    ) -> Communication:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        current_status = communication.status
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Transición no válida: {current_status} → {target_status}",
            )

        # Permission checks per transition
        if target_status == "review":
            self.auth_service.check_entity_permission(
                current_user, communication.entity_id, "communications", "create",
            )
        elif target_status == "published":
            self.auth_service.check_entity_permission(
                current_user, communication.entity_id, "communications", "publish",
            )
        elif target_status == "draft" and current_status == "review":
            self.auth_service.check_entity_permission(
                current_user, communication.entity_id, "communications", "review",
            )
        elif target_status == "archived":
            self.auth_service.check_entity_permission(
                current_user, communication.entity_id, "communications", "publish",
            )

        communication.status = target_status
        if target_status == "published":
            communication.published_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(communication)

        # Notify only on publication
        if target_status == "published":
            self.notification_service.notify(
                event_type=EventType.COMMUNICATION_PUBLISHED,
                entity_id=communication.entity_id,
                actor=current_user,
                resource_type="communications",
                resource_id=communication.id,
                title=f"Nueva comunicación: {communication.title}",
            )

        return self._resolve_images(communication)

    def delete_communication(
        self, communication_id: int, current_user: User
    ) -> dict:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user,
            communication.entity_id,
            "communications",
            "delete",
        )

        communication.is_active = False
        self.db.commit()
        return {"message": "Comunicación eliminada correctamente"}

    def upload_image(
        self,
        communication_id: int,
        file_contents: bytes,
        filename: str,
        content_type: str,
        current_user: User,
    ) -> dict:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        self.auth_service.check_entity_permission(
            current_user,
            communication.entity_id,
            "communications",
            "edit",
        )

        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Tipo de archivo no permitido. Use JPG, PNG, GIF o WEBP",
            )

        unique_filename = f"{uuid4()}{file_ext}"
        s3_key = f"communications/{unique_filename}"

        try:
            storage.upload(s3_key, file_contents, content_type or "image/jpeg")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al guardar el archivo: {str(e)}",
            )

        communication.image_url = s3_key
        self.db.commit()

        image_url = storage.get_presigned_url(s3_key)
        return {"image_url": image_url}


def get_communication_service(
    db: Session = Depends(get_sync_db),
) -> CommunicationService:
    return CommunicationService(db)
