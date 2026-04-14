from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.models.membership_request_model import MembershipRequest
from app.repositories.base_repository import BaseRepository


class MembershipRequestRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, MembershipRequest)

    def get_by_id(self, request_id: int) -> Optional[MembershipRequest]:
        return self.base.get_by_id(request_id)

    def get_pending_by_user_and_entity(
        self, user_id: int, entity_id: int
    ) -> Optional[MembershipRequest]:
        stmt = select(MembershipRequest).where(
            MembershipRequest.user_id == user_id,
            MembershipRequest.entity_id == entity_id,
            MembershipRequest.status == "pending",
        )
        return self.db.execute(stmt).scalars().first()

    def has_any_pending(self, user_id: int) -> bool:
        stmt = select(MembershipRequest.id).where(
            MembershipRequest.user_id == user_id,
            MembershipRequest.status == "pending",
        )
        return self.db.execute(stmt).scalars().first() is not None

    def list_by_entity(
        self, entity_id: int, status: Optional[str] = None
    ) -> List[MembershipRequest]:
        stmt = (
            select(MembershipRequest)
            .where(MembershipRequest.entity_id == entity_id)
            .order_by(MembershipRequest.created_at.asc())
        )
        if status:
            stmt = stmt.where(MembershipRequest.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_user(self, user_id: int) -> List[MembershipRequest]:
        stmt = (
            select(MembershipRequest)
            .where(MembershipRequest.user_id == user_id)
            .order_by(MembershipRequest.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, request: MembershipRequest) -> MembershipRequest:
        return self.base.create(request)

    def update_status(
        self,
        request_id: int,
        status: str,
        reviewed_by_id: Optional[int] = None,
        rejection_reason: Optional[str] = None,
    ) -> Optional[MembershipRequest]:
        values: dict = {"status": status}
        if reviewed_by_id is not None:
            values["reviewed_by_id"] = reviewed_by_id
            values["reviewed_at"] = datetime.utcnow()
        if rejection_reason is not None:
            values["rejection_reason"] = rejection_reason

        stmt = (
            update(MembershipRequest)
            .where(MembershipRequest.id == request_id)
            .values(**values)
        )
        self.db.execute(stmt)
        self.db.flush()
        return self.get_by_id(request_id)

    def hard_delete(self, request_id: int) -> bool:
        req = self.get_by_id(request_id)
        if req:
            self.db.delete(req)
            self.db.flush()
            return True
        return False
