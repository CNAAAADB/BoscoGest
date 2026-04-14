from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from app.models.group_model import Group
from app.repositories.base_repository import BaseRepository


class GroupRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Group)

    def get_by_id(self, group_id: int) -> Optional[Group]:
        return self.base.get_by_id(group_id)

    def get_by_id_with_relations(self, group_id: int) -> Optional[Group]:
        """Load group with users and roles eagerly loaded."""
        stmt = (
            select(Group)
            .options(joinedload(Group.users), joinedload(Group.roles))
            .where(Group.id == group_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_active(
        self, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        """Return active groups with users and roles eagerly loaded."""
        stmt = (
            select(Group)
            .where(Group.is_active == True)
            .options(joinedload(Group.users), joinedload(Group.roles))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def create(self, group: Group) -> Group:
        return self.base.create(group)

    def update(self, group_id: int, data: dict) -> Optional[Group]:
        if data:
            stmt = (
                update(Group)
                .where(Group.id == group_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id(group_id)

    def soft_delete(self, group_id: int) -> bool:
        return self.base.soft_delete(group_id)
