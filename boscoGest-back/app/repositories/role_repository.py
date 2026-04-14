from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.relationships import entity_roles
from app.repositories.base_repository import BaseRepository


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Role)

    def get_by_id(self, role_id: int) -> Optional[Role]:
        return self.base.get_by_id(role_id)

    def get_by_id_with_permissions(self, role_id: int) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions))
            .where(Role.id == role_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_entity_id(
        self, entity_id: int, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        stmt = (
            select(Role)
            .join(entity_roles, entity_roles.c.role_id == Role.id)
            .where(entity_roles.c.entity_id == entity_id)
            .where(Role.is_active == True)
            .options(joinedload(Role.permissions))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def create(self, role: Role) -> Role:
        return self.base.create(role)

    def update(self, role_id: int, data: dict) -> Optional[Role]:
        if data:
            stmt = (
                update(Role)
                .where(Role.id == role_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id_with_permissions(role_id)

    def soft_delete(self, role_id: int) -> bool:
        return self.base.soft_delete(role_id)

    def get_entity_associations(self, role_id: int) -> List[int]:
        stmt = select(entity_roles.c.entity_id).where(
            entity_roles.c.role_id == role_id
        )
        return [row[0] for row in self.db.execute(stmt).fetchall()]

    def get_superadmin_role(self) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions))
            .where(Role.name == "superadmin")
        )
        return self.db.execute(stmt).scalars().first()
