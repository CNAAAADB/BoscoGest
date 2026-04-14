from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.role_model import Role
from app.repositories.base_repository import BaseRepository


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, User)

    # ---- common eager-loading options --------------------------------

    @staticmethod
    def _base_eager_options() -> list:
        """Options shared by list/search queries (groups, permissions, memberships)."""
        return [
            joinedload(User.groups),
            joinedload(User.direct_permissions),
            joinedload(User.memberships),
        ]

    @staticmethod
    def _detail_eager_options() -> list:
        """Options for the detail view (includes entity and role.permissions on each membership)."""
        return [
            joinedload(User.groups),
            joinedload(User.direct_permissions),
            joinedload(User.memberships).joinedload(Membership.entity),
            joinedload(User.memberships).joinedload(Membership.role).joinedload(Role.permissions),
        ]

    # ---- delegates to BaseRepository ---------------------------------

    def get_by_id(self, user_id: int, options: list | None = None) -> Optional[User]:
        return self.base.get_by_id(user_id, options=options)

    def create(self, user: User) -> User:
        return self.base.create(user)

    def soft_delete(self, user_id: int) -> bool:
        return self.base.soft_delete(user_id)

    # ---- user-specific queries ---------------------------------------

    def get_by_id_with_details(self, user_id: int) -> Optional[User]:
        """Fetch a single user with full relationship detail (groups, permissions,
        memberships with their entity and role.permissions)."""
        stmt = (
            select(User)
            .options(*self._detail_eager_options())
            .where(User.id == user_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_email(self, email: str, active_only: bool = True) -> Optional[User]:
        """Look up a user by email, eagerly loading core relationships."""
        stmt = (
            select(User)
            .options(*self._base_eager_options())
            .where(User.email == email)
        )
        if active_only:
            stmt = stmt.where(User.is_active == True)
        return self.db.execute(stmt).scalars().first()

    def get_by_dni(self, dni: str, active_only: bool = True) -> Optional[User]:
        """Look up a user by DNI, eagerly loading core relationships."""
        stmt = (
            select(User)
            .options(*self._base_eager_options())
            .where(User.dni == dni)
        )
        if active_only:
            stmt = stmt.where(User.is_active == True)
        return self.db.execute(stmt).scalars().first()

    def get_by_entity_ids(
        self,
        entity_ids: List[int],
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """Return distinct active users who hold a membership in any of the
        given entity IDs, with base eager loading applied."""
        stmt = (
            select(User)
            .join(User.memberships)
            .where(Membership.entity_id.in_(entity_ids))
            .where(User.is_active == True)
            .options(*self._base_eager_options())
            .offset(skip)
            .limit(limit)
            .distinct()
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def update(self, user_id: int, data: dict) -> None:
        """Bulk-update columns via an UPDATE statement and flush."""
        if not data:
            return
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**data)
        )
        self.db.execute(stmt)
        self.db.flush()
