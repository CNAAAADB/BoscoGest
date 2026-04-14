from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.permission_model import Permission
from app.models.role_model import Role
from app.repositories.base_repository import BaseRepository


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Permission)

    def get_by_id(self, permission_id: int) -> Optional[Permission]:
        return self.base.get_by_id(permission_id)

    def get_all_active(self, skip: int = 0, limit: int = 100) -> List[Permission]:
        return self.base.get_all(
            filters={"is_active": True}, skip=skip, limit=limit
        )

    def create(self, permission: Permission) -> Permission:
        return self.base.create(permission)

    def update(self, permission_id: int, data: dict) -> Optional[Permission]:
        if data:
            stmt = (
                update(Permission)
                .where(Permission.id == permission_id)
                .values(**data)
            )
            self.db.execute(stmt)
            self.db.flush()
        return self.get_by_id(permission_id)

    def soft_delete(self, permission_id: int) -> bool:
        return self.base.soft_delete(permission_id)

    def get_role_with_permissions(self, role_id: int) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions))
            .where(Role.id == role_id)
        )
        return self.db.execute(stmt).scalars().first()
