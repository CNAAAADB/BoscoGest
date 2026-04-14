from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.entity_branding_model import EntityBranding
from app.repositories.base_repository import BaseRepository


class BrandingRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, EntityBranding)

    def get_by_id(self, branding_id: int) -> Optional[EntityBranding]:
        return self.base.get_by_id(branding_id)

    def get_by_entity_id(self, entity_id: int) -> Optional[EntityBranding]:
        stmt = select(EntityBranding).where(EntityBranding.entity_id == entity_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_subdomain(self, subdomain: str) -> Optional[EntityBranding]:
        stmt = select(EntityBranding).where(
            EntityBranding.subdomain == subdomain.lower()
        )
        return self.db.execute(stmt).scalars().first()

    def subdomain_exists(
        self, subdomain: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(EntityBranding).where(
            EntityBranding.subdomain == subdomain.lower()
        )
        if exclude_id:
            stmt = stmt.where(EntityBranding.id != exclude_id)
        return self.db.execute(stmt).scalars().first() is not None

    def create(self, branding: EntityBranding) -> EntityBranding:
        return self.base.create(branding)

    def hard_delete(self, branding: EntityBranding) -> None:
        self.base.hard_delete(branding)
