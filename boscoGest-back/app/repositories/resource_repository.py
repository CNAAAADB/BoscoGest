from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete, or_
from app.models.resource_model import Resource, ResourceType
from app.models.resource_category_model import ResourceCategory
from app.repositories.base_repository import BaseRepository


class ResourceCategoryRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, ResourceCategory)

    def get_by_id(self, category_id: int) -> Optional[ResourceCategory]:
        return self.base.get_by_id(category_id)

    def get_by_entity_id(self, entity_id: int) -> List[ResourceCategory]:
        """Return active categories for the given entity, ordered by name."""
        stmt = (
            select(ResourceCategory)
            .where(
                ResourceCategory.entity_id == entity_id,
                ResourceCategory.is_active == True,
            )
            .order_by(ResourceCategory.name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, category: ResourceCategory) -> ResourceCategory:
        """Add category, commit, and refresh."""
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def soft_delete(self, category_id: int) -> bool:
        """Set is_active=False for the given category."""
        return self.base.soft_delete(category_id)


class ResourceRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Resource)

    def get_by_id(self, resource_id: int) -> Optional[Resource]:
        return self.base.get_by_id(resource_id)

    def get_by_id_with_relations(self, resource_id: int) -> Optional[Resource]:
        """Load resource with entity, category, and creator eagerly loaded."""
        stmt = (
            select(Resource)
            .options(
                joinedload(Resource.entity),
                joinedload(Resource.category),
                joinedload(Resource.creator),
            )
            .where(Resource.id == resource_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_filtered(
        self,
        accessible_ids: List[int],
        category_id: Optional[int] = None,
        resource_type: Optional[ResourceType] = None,
        tags: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Resource]:
        """Return filtered resources with eager-loaded relations."""
        stmt = (
            select(Resource)
            .options(
                joinedload(Resource.entity),
                joinedload(Resource.category),
                joinedload(Resource.creator),
            )
            .where(
                Resource.entity_id.in_(accessible_ids),
                Resource.is_active == True,
            )
        )

        if category_id is not None:
            stmt = stmt.where(Resource.category_id == category_id)

        if resource_type is not None:
            stmt = stmt.where(Resource.resource_type == resource_type)

        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            tag_conditions = [
                Resource.tags.ilike(f"%{tag}%") for tag in tag_list
            ]
            if tag_conditions:
                stmt = stmt.where(or_(*tag_conditions))

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Resource.title.ilike(pattern),
                    Resource.description.ilike(pattern),
                )
            )

        stmt = (
            stmt.order_by(Resource.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(self.db.execute(stmt).scalars().unique().all())

    def create(self, resource: Resource) -> Resource:
        """Add resource, flush, and refresh (caller must commit)."""
        return self.base.create(resource)

    def update(self, resource_id: int, data: dict) -> Optional[Resource]:
        """Update resource fields via SQLAlchemy update statement and flush."""
        if data:
            stmt = (
                update(Resource)
                .where(Resource.id == resource_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id(resource_id)

    def hard_delete(self, resource_id: int) -> None:
        """Delete the resource row permanently."""
        stmt = delete(Resource).where(Resource.id == resource_id)
        self.db.execute(stmt)
