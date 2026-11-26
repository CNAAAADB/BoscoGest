from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.comment_model import Comment
from app.models.communication_model import Communication
from app.models.user_model import User
from app.schemas.communication import CommentCreate, CommentUpdate
from app.repositories.comment_repository import CommentRepository
from app.services.scoped_permissions import ScopedPermissions
from app.services.notification_service import NotificationService, EventType
from app.utils.auth import get_sync_db


class CommentService:
    def __init__(self, db: Session):
        self.db = db
        self.comment_repo = CommentRepository(db)
        self.scope = ScopedPermissions(db)
        self.notification_service = NotificationService(db)

    def _get_communication(self, communication_id: int) -> Communication:
        communication = (
            self.db.query(Communication)
            .filter(Communication.id == communication_id)
            .first()
        )
        if not communication or not communication.is_active or communication.status != "published":
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        return communication

    def create_comment(
        self,
        communication_id: int,
        comment_in: CommentCreate,
        current_user: User,
    ) -> Comment:
        communication = self._get_communication(communication_id)
        self.scope.require(
            current_user, communication.entity_id, "comment", "create", inherit=False
        )
        comment = Comment(
            **comment_in.model_dump(),
            communication_id=communication_id,
            user_id=current_user.id,
        )
        self.comment_repo.create(comment)
        self.db.commit()
        self.db.refresh(comment)

        # Notify: communication author + distinct commenters
        existing_comments = self.comment_repo.get_by_communication_id(communication_id)
        recipient_ids = {communication.created_by_id}
        for c in existing_comments:
            recipient_ids.add(c.user_id)
        recipient_ids.discard(current_user.id)

        if recipient_ids:
            self.notification_service.notify(
                event_type=EventType.COMMENT_ADDED,
                entity_id=communication.entity_id,
                actor=current_user,
                resource_type="communications",
                resource_id=communication_id,
                title=f"Nuevo comentario en: {communication.title}",
                recipient_ids=list(recipient_ids),
            )

        return comment

    def list_comments(
        self, communication_id: int, current_user: User
    ) -> List[Comment]:
        communication = self._get_communication(communication_id)
        self.scope.require(
            current_user, communication.entity_id, "comment", "read", inherit=False
        )
        return self.comment_repo.get_by_communication_id(communication_id)

    def update_comment(
        self,
        comment_id: int,
        comment_in: CommentUpdate,
        current_user: User,
    ) -> Comment:
        comment = self.comment_repo.get_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        communication = self._get_communication(comment.communication_id)
        if comment.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo el autor puede editar su comentario")
        self.scope.require(current_user, communication.entity_id, "comment", "edit", inherit=False)

        for field, value in comment_in.model_dump(exclude_unset=True).items():
            setattr(comment, field, value)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment_id: int, current_user: User) -> dict:
        comment = self.comment_repo.get_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        communication = self._get_communication(comment.communication_id)
        if not self.scope.allows(current_user, communication.entity_id, "comment", "manage_all", wildcard=False):
            if comment.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Solo el autor o un moderador puede eliminar este comentario")
            self.scope.require(current_user, communication.entity_id, "comment", "delete", inherit=False)

        self.comment_repo.hard_delete(comment)
        self.db.commit()
        return {"message": "Comentario eliminado correctamente"}


def get_comment_service(db: Session = Depends(get_sync_db)) -> CommentService:
    return CommentService(db)
