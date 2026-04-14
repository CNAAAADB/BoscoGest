from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete
from app.models.magazine_model import Magazine
from app.repositories.base_repository import BaseRepository


class MagazineRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Magazine)

    def get_by_id(self, magazine_id: int) -> Optional[Magazine]:
        return self.base.get_by_id(magazine_id)

    def get_by_id_with_entity(self, magazine_id: int) -> Optional[Magazine]:
        stmt = (
            select(Magazine)
            .options(joinedload(Magazine.entity))
            .where(Magazine.id == magazine_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_entity_ids(
        self, entity_ids: List[int], skip: int = 0, limit: int = 100
    ) -> List[Magazine]:
        stmt = (
            select(Magazine)
            .options(joinedload(Magazine.entity))
            .where(Magazine.entity_id.in_(entity_ids))
            .order_by(Magazine.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, magazine: Magazine) -> Magazine:
        return self.base.create(magazine)

    def update(self, magazine_id: int, data: dict) -> Optional[Magazine]:
        if data:
            stmt = (
                update(Magazine)
                .where(Magazine.id == magazine_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id(magazine_id)

    def hard_delete(self, magazine_id: int) -> None:
        stmt = delete(Magazine).where(Magazine.id == magazine_id)
        self.db.execute(stmt)
