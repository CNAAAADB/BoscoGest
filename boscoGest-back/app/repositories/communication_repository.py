from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.communication_model import Communication
from app.models.membership_model import Membership
from app.repositories.base_repository import BaseRepository


class CommunicationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Communication)

    def get_by_id(self, communication_id: int) -> Optional[Communication]:
        return self.base.get_by_id(communication_id)

    def get_accessible_entity_ids(self, user_id: int) -> List[int]:
        stmt = select(Membership.entity_id).where(
            Membership.user_id == user_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_entity_ids(
        self,
        entity_ids: List[int],
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> List[Communication]:
        query = self.db.query(Communication).options(
            joinedload(Communication.entity)
        ).filter(
            Communication.entity_id.in_(entity_ids),
            Communication.is_active == True,
        )
        if status:
            query = query.filter(Communication.status == status)
        elif statuses:
            query = query.filter(Communication.status.in_(statuses))
        return (
            query.order_by(Communication.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_entity_ids(
        self,
        entity_ids: List[int],
        status: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> int:
        query = self.db.query(Communication).filter(
            Communication.entity_id.in_(entity_ids),
            Communication.is_active == True,
        )
        if status:
            query = query.filter(Communication.status == status)
        elif statuses:
            query = query.filter(Communication.status.in_(statuses))
        return query.count()

    def create(self, communication: Communication) -> Communication:
        return self.base.create(communication)

    def soft_delete(self, communication_id: int) -> bool:
        return self.base.soft_delete(communication_id)
