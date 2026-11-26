from datetime import datetime, timezone
from typing import List, Optional
import os
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.communication_model import Communication
from app.models.user_model import User
from app.schemas.communication import CommunicationCreate, CommunicationUpdate, VALID_TRANSITIONS
from app.models.entity_model import Entity
from sqlalchemy import select
from app.repositories.communication_repository import CommunicationRepository
from app.services.scoped_permissions import ScopedPermissions
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
        self.comm_repo = CommunicationRepository(db)
        self.scope = ScopedPermissions(db)
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

    ADMIN_ACTIONS = ("create", "edit", "delete", "publish", "review")

    def get_entities_with_create_permission(self, current_user: User) -> list:
        ids = self.scope.ids(current_user, "communications", "create")
        return list(self.db.scalars(select(Entity).where(Entity.id.in_(ids)).order_by(Entity.name)).all())

    def _decorate(self, user, rows):
        rows = self.scope.decorate(user, rows, "communications", self.ADMIN_ACTIONS)
        for row in rows if isinstance(rows, list) else [rows]:
            row.permissions["comment_create"] = self.scope.allows(user, row.entity_id, "comment", "create", inherit=False)
            row.permissions["comment_delete"] = self.scope.allows(user, row.entity_id, "comment", "delete", inherit=False)
            row.permissions["comment_moderate"] = self.scope.allows(user, row.entity_id, "comment", "manage_all", wildcard=False)
        return rows

    def create_communication(
        self, communication_in: CommunicationCreate, current_user: User
    ) -> Communication:
        self.scope.require(
            current_user,
            communication_in.entity_id,
            "communications",
            "create",
        )

        # If publishing directly, check publish permission
        status = communication_in.status or "draft"
        if status == "published":
            self.scope.require(
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

    def _visibility(self, user):
        visible = self.scope.content_ids(user, "communications", self.ADMIN_ACTIONS)
        private = set()
        for action in ("create", "edit", "review", "publish"):
            private.update(self.scope.ids(user, "communications", action))
        return visible, private

    def list_communications(self, current_user: User, skip: int = 0, limit: int = 10,
                            status: Optional[str] = None) -> List[Communication]:
        visible, private = self._visibility(current_user)
        rows = self.comm_repo.get_by_entity_ids(
            list(visible), skip=skip, limit=limit, status=status,
            private_entity_ids=list(private),
        )
        return self._decorate(current_user, self._resolve_images(rows))

    def count_communications(self, current_user: User, status: Optional[str] = None) -> dict:
        visible, private = self._visibility(current_user)
        return {"total": self.comm_repo.count_by_entity_ids(
            list(visible), status=status, private_entity_ids=list(private),
        )}

    def get_communication(self, communication_id: int, current_user: User) -> Communication:
        communication = self.comm_repo.get_by_id(communication_id)
        visible, private = self._visibility(current_user)
        if (not communication or not communication.is_active
                or communication.entity_id not in visible
                or (communication.status != "published" and communication.entity_id not in private)):
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        return self._decorate(current_user, self._resolve_images(communication))

    def update_communication(
        self,
        communication_id: int,
        communication_in: CommunicationUpdate,
        current_user: User,
    ) -> Communication:
        communication = self.comm_repo.get_by_id(communication_id)
        if not communication or not communication.is_active:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        # Only draft and review communications can be edited
        if communication.status not in ("draft", "review"):
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden editar comunicaciones en estado borrador o revisión",
            )

        self.scope.require(
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
        if not communication or not communication.is_active:
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
            self.scope.require(
                current_user, communication.entity_id, "communications", "create",
            )
        elif target_status == "published":
            self.scope.require(
                current_user, communication.entity_id, "communications", "publish",
            )
        elif target_status == "draft" and current_status == "review":
            self.scope.require(
                current_user, communication.entity_id, "communications", "review",
            )
        elif target_status == "archived":
            self.scope.require(
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
        if not communication or not communication.is_active:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        self.scope.require(
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
        if not communication or not communication.is_active:
            raise HTTPException(
                status_code=404, detail="Comunicación no encontrada"
            )

        self.scope.require(
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
