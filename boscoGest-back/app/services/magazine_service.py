from typing import List
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.entity_model import Entity
from app.models.magazine_model import Magazine
from app.models.user_model import User
from app.schemas.magazine import MagazineUpdate
from app.repositories.magazine_repository import MagazineRepository
from app.services.scoped_permissions import ScopedPermissions
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class MagazineService:
    def __init__(self, db: Session):
        self.db = db
        self.magazine_repo = MagazineRepository(db)
        self.scope = ScopedPermissions(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    async def create_magazine(
        self,
        title: str,
        entity_id: int,
        file_contents: bytes,
        filename: str,
        current_user: User,
        collection: str | None = None,
        issue_number: str | None = None,
        description: str | None = None,
        ip_address: str | None = None,
    ) -> Magazine:
        self.scope.require(
            current_user, entity_id, "magazines", "create"
        )

        collection_value = collection if collection and collection.strip() else None
        description_value = (
            description if description and description.strip() else None
        )

        issue_number_value = None
        if issue_number and issue_number.strip():
            try:
                issue_number_value = int(issue_number)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Issue number must be a valid integer",
                )

        entity = self.db.execute(
            select(Entity).where(Entity.id == entity_id, Entity.is_active == True)
        ).scalars().first()

        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity with id {entity_id} not found or inactive",
            )

        if not filename.endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed",
            )

        unique_filename = f"{uuid.uuid4()}.pdf"
        s3_key = f"magazines/{unique_filename}"

        try:
            storage.upload(s3_key, file_contents, "application/pdf")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {str(e)}",
            )

        db_magazine = Magazine(
            title=title,
            collection=collection_value,
            issue_number=issue_number_value,
            description=description_value,
            entity_id=entity_id,
            file_path=s3_key,
        )

        self.magazine_repo.create(db_magazine)
        self.db.commit()
        self.db.refresh(db_magazine)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="magazines",
            resource_id=db_magazine.id,
            details={
                "title": title,
                "collection": collection,
                "issue_number": issue_number,
                "entity_id": entity_id,
            },
            ip_address=ip_address,
        )

        self.notification_service.notify(
            event_type=EventType.MAGAZINE_PUBLISHED,
            entity_id=entity_id,
            actor=current_user,
            resource_type="magazines",
            resource_id=db_magazine.id,
            title=f"Nueva revista: {title}",
        )

        return db_magazine

    def list_magazines(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Magazine]:
        accessible_entity_ids = self.scope.content_ids(current_user, "magazines", ("create", "update", "delete"))

        if not accessible_entity_ids:
            return []

        rows = self.magazine_repo.get_by_entity_ids(
            list(accessible_entity_ids), skip=skip, limit=limit
        )
        return self.scope.decorate(current_user, rows, "magazines", ("update", "delete"))

    def get_magazine(self, magazine_id: int, current_user: User) -> Magazine:
        magazine = self.magazine_repo.get_by_id_with_entity(magazine_id)
        if not magazine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found"
            )

        if magazine.entity_id not in self.scope.content_ids(current_user, "magazines", ("create", "update", "delete")):
            raise HTTPException(status_code=404, detail="Magazine not found")
        return self.scope.decorate(current_user, magazine, "magazines", ("update", "delete"))(self, magazine_id: int, current_user: User) -> str:
        magazine = self.magazine_repo.get_by_id(magazine_id)
        if not magazine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found"
            )

        if magazine.entity_id not in self.scope.content_ids(current_user, "magazines", ("create", "update", "delete")):
            raise HTTPException(status_code=404, detail="Magazine not found")

        key = magazine.file_path
        if key.startswith("/uploads/"):
            key = key[len("/uploads/"):]
        elif key.startswith("uploads/"):
            key = key[len("uploads/"):]

        return storage.get_presigned_url(
            key, expires_in=900, filename=f"{magazine.title}.pdf"
        )

    def update_magazine(
        self,
        magazine_id: int,
        magazine_update: MagazineUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Magazine:
        db_magazine = self.magazine_repo.get_by_id(magazine_id)
        if not db_magazine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found"
            )

        self.scope.require(
            current_user, db_magazine.entity_id, "magazines", "update"
        )

        update_data = magazine_update.model_dump(exclude_unset=True)
        if update_data:
            db_magazine = self.magazine_repo.update(magazine_id, update_data)
            self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="magazines",
                resource_id=magazine_id,
                details=update_data,
                ip_address=ip_address,
            )

        return db_magazine

    def delete_magazine(
        self,
        magazine_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        db_magazine = self.magazine_repo.get_by_id(magazine_id)
        if not db_magazine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Magazine not found"
            )

        self.scope.require(
            current_user, db_magazine.entity_id, "magazines", "delete"
        )

        title = db_magazine.title
        file_path = db_magazine.file_path

        self.magazine_repo.hard_delete(magazine_id)
        self.db.commit()

        try:
            storage.delete(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="magazines",
            resource_id=magazine_id,
            details={"title": title},
            ip_address=ip_address,
        )


def get_magazine_service(db: Session = Depends(get_sync_db)) -> MagazineService:
    return MagazineService(db)
