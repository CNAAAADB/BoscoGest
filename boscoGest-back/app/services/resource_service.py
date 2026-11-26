from typing import List, Optional
import os
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.resource_model import Resource, ResourceType
from app.models.resource_category_model import ResourceCategory
from app.models.entity_model import Entity
from app.models.user_model import User
from app.schemas.resource import ResourceCreate, ResourceUpdate
from app.repositories.resource_repository import (
    ResourceRepository,
    ResourceCategoryRepository,
)
from app.services.scoped_permissions import ScopedPermissions
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()

DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ResourceCategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.category_repo = ResourceCategoryRepository(db)
        self.scope = ScopedPermissions(db)
        self.audit_service = AuditService(db)

    def create_category(
        self, category_in, current_user: User, ip_address: str | None = None
    ) -> ResourceCategory:
        self.scope.require(
            current_user, category_in.entity_id, "resources", "create"
        )

        entity = self.db.execute(
            select(Entity).where(
                Entity.id == category_in.entity_id, Entity.is_active == True
            )
        ).scalars().first()
        if not entity:
            raise HTTPException(
                status_code=404, detail="Entity not found or inactive"
            )

        db_category = ResourceCategory(**category_in.model_dump())
        self.category_repo.create(db_category)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="resource_categories",
            resource_id=db_category.id,
            details={
                "name": category_in.name,
                "entity_id": category_in.entity_id,
            },
            ip_address=ip_address,
        )
        return db_category

    def list_categories(
        self, entity_id: int, current_user: User
    ) -> List[ResourceCategory]:
        if entity_id not in self.scope.content_ids(current_user, "resources", ("create", "update", "delete")):
            raise HTTPException(status_code=403, detail="Permission denied")
        return self.category_repo.get_by_entity_id(entity_id)

    def update_category(
        self,
        category_id: int,
        category_update,
        current_user: User,
        ip_address: str | None = None,
    ) -> ResourceCategory:
        db_category = self.category_repo.get_by_id(category_id)
        if not db_category:
            raise HTTPException(status_code=404, detail="Category not found")

        self.scope.require(
            current_user, db_category.entity_id, "resources", "update"
        )

        update_data = category_update.model_dump(exclude_unset=True)
        if update_data:
            for key, value in update_data.items():
                setattr(db_category, key, value)
            self.db.commit()
            self.db.refresh(db_category)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="resource_categories",
                resource_id=category_id,
                details=update_data,
                ip_address=ip_address,
            )
        return db_category

    def delete_category(
        self,
        category_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        db_category = self.category_repo.get_by_id(category_id)
        if not db_category:
            raise HTTPException(status_code=404, detail="Category not found")

        self.scope.require(
            current_user, db_category.entity_id, "resources", "delete"
        )

        db_category.is_active = False
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="resource_categories",
            resource_id=category_id,
            details={"name": db_category.name},
            ip_address=ip_address,
        )


class ResourceService:
    def __init__(self, db: Session):
        self.db = db
        self.resource_repo = ResourceRepository(db)
        self.scope = ScopedPermissions(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    def create_resource_link(
        self,
        resource_in: ResourceCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Resource:
        self.scope.require(
            current_user, resource_in.entity_id, "resources", "create"
        )

        if resource_in.resource_type not in (ResourceType.LINK, ResourceType.VIDEO):
            raise HTTPException(
                status_code=400,
                detail="This endpoint is for link/video resources only. "
                "Use POST /resources/ for file uploads.",
            )
        if not resource_in.url:
            raise HTTPException(
                status_code=400,
                detail="URL is required for link/video resources",
            )

        entity = self.db.execute(
            select(Entity).where(
                Entity.id == resource_in.entity_id, Entity.is_active == True
            )
        ).scalars().first()
        if not entity:
            raise HTTPException(
                status_code=404, detail="Entity not found or inactive"
            )

        if resource_in.category_id:
            category = self.db.execute(
                select(ResourceCategory).where(
                    ResourceCategory.id == resource_in.category_id,
                    ResourceCategory.is_active == True,
                )
            ).scalars().first()
            if not category:
                raise HTTPException(
                    status_code=404, detail="Category not found"
                )

        db_resource = Resource(
            **resource_in.model_dump(), created_by=current_user.id
        )
        self.db.add(db_resource)
        self.db.commit()
        self.db.refresh(db_resource)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="resources",
            resource_id=db_resource.id,
            details={
                "title": resource_in.title,
                "type": resource_in.resource_type.value,
                "entity_id": resource_in.entity_id,
            },
            ip_address=ip_address,
        )

        self.notification_service.notify(
            event_type=EventType.RESOURCE_PUBLISHED,
            entity_id=resource_in.entity_id,
            actor=current_user,
            resource_type="resources",
            resource_id=db_resource.id,
            title=f"Nuevo recurso: {resource_in.title}",
        )

        return db_resource

    async def create_resource_file(
        self,
        title: str,
        resource_type: ResourceType,
        entity_id: int,
        file_contents: bytes,
        filename: str,
        content_type: str,
        current_user: User,
        description: str | None = None,
        tags: str | None = None,
        category_id: int | None = None,
        ip_address: str | None = None,
    ) -> Resource:
        self.scope.require(
            current_user, entity_id, "resources", "create"
        )

        if resource_type not in (ResourceType.DOCUMENT, ResourceType.IMAGE):
            raise HTTPException(
                status_code=400,
                detail="This endpoint is for document/image resources. "
                "Use POST /resources/link for links/videos.",
            )

        entity = self.db.execute(
            select(Entity).where(
                Entity.id == entity_id, Entity.is_active == True
            )
        ).scalars().first()
        if not entity:
            raise HTTPException(
                status_code=404, detail="Entity not found or inactive"
            )

        file_ext = os.path.splitext(filename)[1].lower() if filename else ""
        if (
            resource_type == ResourceType.DOCUMENT
            and file_ext not in DOCUMENT_EXTENSIONS
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for document. Allowed: "
                f"{', '.join(DOCUMENT_EXTENSIONS)}",
            )
        if (
            resource_type == ResourceType.IMAGE
            and file_ext not in IMAGE_EXTENSIONS
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for image. Allowed: "
                f"{', '.join(IMAGE_EXTENSIONS)}",
            )

        if category_id:
            category = self.db.execute(
                select(ResourceCategory).where(
                    ResourceCategory.id == category_id,
                    ResourceCategory.is_active == True,
                )
            ).scalars().first()
            if not category:
                raise HTTPException(
                    status_code=404, detail="Category not found"
                )

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"resources/{unique_filename}"

        try:
            storage.upload(s3_key, file_contents, content_type or "application/octet-stream")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error saving file: {str(e)}"
            )

        description_value = (
            description if description and description.strip() else None
        )
        tags_value = tags if tags and tags.strip() else None

        db_resource = Resource(
            title=title,
            description=description_value,
            resource_type=resource_type,
            file_path=s3_key,
            original_filename=filename,
            tags=tags_value,
            entity_id=entity_id,
            category_id=category_id if category_id else None,
            created_by=current_user.id,
        )
        self.db.add(db_resource)
        self.db.commit()
        self.db.refresh(db_resource)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="resources",
            resource_id=db_resource.id,
            details={
                "title": title,
                "type": resource_type.value,
                "entity_id": entity_id,
                "filename": filename,
            },
            ip_address=ip_address,
        )

        self.notification_service.notify(
            event_type=EventType.RESOURCE_PUBLISHED,
            entity_id=entity_id,
            actor=current_user,
            resource_type="resources",
            resource_id=db_resource.id,
            title=f"Nuevo recurso: {title}",
        )

        return db_resource

    def list_resources(
        self,
        current_user: User,
        entity_id: int | None = None,
        category_id: int | None = None,
        resource_type: ResourceType | None = None,
        tags: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Resource]:
        accessible_ids = self.scope.content_ids(current_user, "resources", ("create", "update", "delete"))
        if entity_id is not None:
            if entity_id not in accessible_ids:
                raise HTTPException(status_code=403, detail="Permission denied")
            accessible_ids = {entity_id}

        rows = self.resource_repo.get_filtered(
            list(accessible_ids),
            category_id=category_id,
            resource_type=resource_type,
            tags=tags,
            search=search,
            skip=skip,
            limit=limit,
        )
        return self.scope.decorate(current_user, rows, "resources", ("update", "delete"))

    def get_resource(self, resource_id: int, current_user: User) -> Resource:
        resource = self.resource_repo.get_by_id_with_relations(resource_id)
        if not resource or not resource.is_active:
            raise HTTPException(status_code=404, detail="Resource not found")

        if resource.entity_id not in self.scope.content_ids(current_user, "resources", ("create", "update", "delete")):
            raise HTTPException(status_code=404, detail="Resource not found")
        return self.scope.decorate(current_user, resource, "resources", ("update", "delete"))

    def get_resource_file_url(
        self, resource_id: int, current_user: User
    ) -> str:
        resource = self.resource_repo.get_by_id(resource_id)
        if not resource or not resource.is_active:
            raise HTTPException(status_code=404, detail="Resource not found")

        if resource.entity_id not in self.scope.content_ids(current_user, "resources", ("create", "update", "delete")):
            raise HTTPException(status_code=404, detail="Resource not found")

        if not resource.file_path:
            raise HTTPException(
                status_code=404, detail="Resource file not found"
            )

        filename = resource.original_filename or os.path.basename(
            resource.file_path
        )
        return storage.get_presigned_url(
            resource.file_path, expires_in=900, filename=filename
        )

    def update_resource(
        self,
        resource_id: int,
        resource_update: ResourceUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Resource:
        db_resource = self.resource_repo.get_by_id(resource_id)
        if not db_resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        self.scope.require(
            current_user, db_resource.entity_id, "resources", "update"
        )

        update_data = resource_update.model_dump(exclude_unset=True)
        if update_data:
            self.resource_repo.update(resource_id, update_data)
            self.db.commit()

            db_resource = self.resource_repo.get_by_id(resource_id)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="resources",
                resource_id=resource_id,
                details=update_data,
                ip_address=ip_address,
            )
        return db_resource

    def delete_resource(
        self,
        resource_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        db_resource = self.resource_repo.get_by_id(resource_id)
        if not db_resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        self.scope.require(
            current_user, db_resource.entity_id, "resources", "delete"
        )

        title = db_resource.title
        file_path = db_resource.file_path

        self.resource_repo.hard_delete(resource_id)
        self.db.commit()

        if file_path:
            try:
                storage.delete(file_path)
            except Exception:
                pass

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="resources",
            resource_id=resource_id,
            details={"title": title},
            ip_address=ip_address,
        )


def get_resource_service(
    db: Session = Depends(get_sync_db),
) -> ResourceService:
    return ResourceService(db)


def get_resource_category_service(
    db: Session = Depends(get_sync_db),
) -> ResourceCategoryService:
    return ResourceCategoryService(db)
