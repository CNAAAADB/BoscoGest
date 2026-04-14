from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository providing common CRUD operations."""

    def __init__(self, db: Session, model_class: Type[T]):
        self.db = db
        self.model_class = model_class

    def get_by_id(self, id: int, options: list | None = None) -> Optional[T]:
        stmt = select(self.model_class).where(self.model_class.id == id)
        if options:
            for opt in options:
                stmt = stmt.options(opt)
        return self.db.execute(stmt).scalars().first()

    def get_all(
        self,
        filters: Dict[str, Any] | None = None,
        options: list | None = None,
        skip: int = 0,
        limit: int | None = None,
        order_by=None,
    ) -> List[T]:
        stmt = select(self.model_class)
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model_class, key) == value)
        if options:
            for opt in options:
                stmt = stmt.options(opt)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, entity: T) -> T:
        """Add entity and flush (caller must commit)."""
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def soft_delete(self, id: int) -> bool:
        stmt = (
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(is_active=False)
        )
        result = self.db.execute(stmt)
        return result.rowcount > 0

    def hard_delete(self, entity: T) -> None:
        self.db.delete(entity)

    def count(self, filters: Dict[str, Any] | None = None) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model_class)
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model_class, key) == value)
        return self.db.execute(stmt).scalar() or 0
