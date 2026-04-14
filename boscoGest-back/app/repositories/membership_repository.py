from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, update
from app.models.membership_model import Membership
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.repositories.base_repository import BaseRepository


class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Membership)

    def get_by_id(
        self, membership_id: int, options: list | None = None
    ) -> Optional[Membership]:
        return self.base.get_by_id(membership_id, options=options)

    def get_by_id_with_relations(
        self, membership_id: int
    ) -> Optional[Membership]:
        stmt = (
            select(Membership)
            .options(
                selectinload(Membership.role).selectinload(Role.permissions),
                selectinload(Membership.entity),
                selectinload(Membership.user),
            )
            .where(Membership.id == membership_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_user_memberships_with_relations(
        self, user_id: int
    ) -> List[Membership]:
        stmt = (
            select(Membership)
            .join(Entity, Membership.entity_id == Entity.id)
            .options(
                selectinload(Membership.role).selectinload(Role.permissions),
                selectinload(Membership.entity),
                selectinload(Membership.user),
            )
            .where(
                Membership.user_id == user_id,
                Membership.is_active == True,
                Entity.is_active == True,
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_user_and_entity(
        self,
        user_id: int,
        entity_id: int,
        role_id: int | None = None,
        active_only: bool = True,
    ) -> Optional[Membership]:
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.entity_id == entity_id,
        )
        if role_id is not None:
            stmt = stmt.where(Membership.role_id == role_id)
        if active_only:
            stmt = stmt.where(Membership.is_active == True)
        return self.db.execute(stmt).scalars().first()

    def get_user_memberships_with_role_permissions(
        self, user_id: int
    ) -> List[Membership]:
        stmt = (
            select(Membership)
            .options(
                joinedload(Membership.role).joinedload(Role.permissions),
            )
            .where(
                Membership.user_id == user_id,
                Membership.is_active == True,
            )
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def get_entity_ids_by_user(self, user_id: int) -> List[int]:
        stmt = select(Membership.entity_id).where(
            Membership.user_id == user_id
        )
        return [row[0] for row in self.db.execute(stmt).fetchall()]

    def create(self, membership: Membership) -> Membership:
        return self.base.create(membership)

    def update(
        self, membership_id: int, data: dict
    ) -> Optional[Membership]:
        if data:
            stmt = (
                update(Membership)
                .where(Membership.id == membership_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id_with_relations(membership_id)

    def soft_delete(self, membership_id: int) -> bool:
        return self.base.soft_delete(membership_id)
