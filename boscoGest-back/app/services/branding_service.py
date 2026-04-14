from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.entity_model import Entity
from app.models.entity_branding_model import EntityBranding
from app.models.user_model import User
from app.schemas.entity_branding import EntityBrandingCreate, EntityBrandingUpdate
from app.repositories.branding_repository import BrandingRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db

storage = get_storage_service()


class BrandingService:
    def __init__(self, db: Session):
        self.db = db
        self.branding_repo = BrandingRepository(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)

    @staticmethod
    def _resolve_logo_url(branding: EntityBranding) -> EntityBranding:
        if branding and branding.logo_url and not branding.logo_url.startswith("http"):
            branding.logo_url = storage.get_presigned_url(branding.logo_url)
        return branding

    def get_entity_branding(
        self, entity_id: int, current_user: User
    ) -> EntityBranding:
        entity = self.db.get(Entity, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        self.auth_service.check_entity_permission(
            current_user, entity_id, "branding", "read"
        )

        branding = self.branding_repo.get_by_entity_id(entity_id)
        if not branding:
            raise HTTPException(
                status_code=404,
                detail="Branding not configured for this entity. Use POST to create.",
            )

        self.db.expunge(branding)
        return self._resolve_logo_url(branding)

    def get_branding_by_subdomain(self, subdomain: str) -> EntityBranding:
        branding = self.branding_repo.get_by_subdomain(subdomain)
        if not branding:
            raise HTTPException(status_code=404, detail="Subdomain not found")

        self.db.expunge(branding)
        return self._resolve_logo_url(branding)

    def create_branding(
        self,
        branding_in: EntityBrandingCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityBranding:
        entity = self.db.get(Entity, branding_in.entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        self.auth_service.check_entity_permission(
            current_user, branding_in.entity_id, "branding", "update"
        )

        existing = self.branding_repo.get_by_entity_id(branding_in.entity_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Branding already exists for this entity. Use PUT to update.",
            )

        if branding_in.subdomain:
            if self.branding_repo.subdomain_exists(branding_in.subdomain):
                raise HTTPException(
                    status_code=409, detail="Subdomain is already in use"
                )

        branding = EntityBranding(**branding_in.model_dump())
        self.branding_repo.create(branding)
        self.db.commit()
        self.db.refresh(branding)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="branding",
            resource_id=branding.id,
            details={"entity_id": branding.entity_id},
            ip_address=ip_address,
        )

        self.db.expunge(branding)
        return self._resolve_logo_url(branding)

    def update_branding(
        self,
        entity_id: int,
        branding_in: EntityBrandingUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityBranding:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "branding", "update"
        )

        branding = self.branding_repo.get_by_entity_id(entity_id)
        if not branding:
            raise HTTPException(
                status_code=404,
                detail="Branding not found for this entity. Use POST to create.",
            )

        update_data = branding_in.model_dump(exclude_unset=True)
        if "subdomain" in update_data and update_data["subdomain"]:
            if self.branding_repo.subdomain_exists(
                update_data["subdomain"], exclude_id=branding.id
            ):
                raise HTTPException(
                    status_code=409, detail="Subdomain is already in use"
                )

        for field, value in update_data.items():
            setattr(branding, field, value)

        self.db.commit()
        self.db.refresh(branding)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="update",
            resource_type="branding",
            resource_id=branding.id,
            details=update_data,
            ip_address=ip_address,
        )

        self.db.expunge(branding)
        return self._resolve_logo_url(branding)

    async def upload_logo(
        self,
        entity_id: int,
        file_contents: bytes,
        filename: str,
        content_type: str,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityBranding:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "branding", "update"
        )

        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            )

        if len(file_contents) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="File size exceeds 5MB limit"
            )

        branding = self.branding_repo.get_by_entity_id(entity_id)
        if not branding:
            branding = EntityBranding(entity_id=entity_id)
            self.db.add(branding)
            self.db.flush()

        file_ext = filename.split(".")[-1] if "." in filename else "png"
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        s3_key = f"logos/{unique_filename}"

        storage.upload(s3_key, file_contents, content_type or "image/png")

        branding.logo_url = s3_key
        self.db.commit()
        self.db.refresh(branding)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="upload_logo",
            resource_type="branding",
            resource_id=branding.id,
            details={"filename": unique_filename},
            ip_address=ip_address,
        )

        self.db.expunge(branding)
        return self._resolve_logo_url(branding)

    def delete_branding(
        self,
        entity_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "branding", "update"
        )

        branding = self.branding_repo.get_by_entity_id(entity_id)
        if not branding:
            raise HTTPException(
                status_code=404, detail="Branding not found for this entity"
            )

        branding_id = branding.id
        self.branding_repo.hard_delete(branding)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="branding",
            resource_id=branding_id,
            details={"entity_id": entity_id},
            ip_address=ip_address,
        )

        return {"message": "Branding deleted successfully"}


def get_branding_service(db: Session = Depends(get_sync_db)) -> BrandingService:
    return BrandingService(db)
