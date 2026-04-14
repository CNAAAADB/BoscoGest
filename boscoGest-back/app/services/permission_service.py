from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.permission_model import Permission
from app.models.user_model import User
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.repositories.permission_repository import PermissionRepository
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db


class PermissionService:
    def __init__(self, db: Session):
        self.db = db
        self.permission_repo = PermissionRepository(db)
        self.audit_service = AuditService(db)

    def create_permission(
        self,
        permission_in: PermissionCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Permission:
        try:
            db_permission = Permission(**permission_in.model_dump())
            self.permission_repo.create(db_permission)
            self.db.commit()
            self.db.refresh(db_permission)
            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="permissions",
                resource_id=db_permission.id,
                details=permission_in.model_dump(),
                ip_address=ip_address,
            )
            return db_permission
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission with this resource and action already exists",
            )

    def list_permissions(self, skip: int = 0, limit: int = 100) -> List[Permission]:
        return self.permission_repo.get_all_active(skip=skip, limit=limit)

    def get_permission(self, permission_id: int) -> Permission:
        db_permission = self.permission_repo.get_by_id(permission_id)
        if db_permission is None:
            raise HTTPException(status_code=404, detail="Permission not found")
        return db_permission

    def update_permission(
        self,
        permission_id: int,
        permission_in: PermissionUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Permission:
        self.get_permission(permission_id)  # ensure exists
        update_data = permission_in.model_dump(exclude_unset=True)
        try:
            db_permission = self.permission_repo.update(permission_id, update_data)
            self.db.commit()
            self.db.refresh(db_permission)
            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="permissions",
                resource_id=permission_id,
                details=update_data,
                ip_address=ip_address,
            )
            return db_permission
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission with this resource and action already exists",
            )

    def delete_permission(
        self,
        permission_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        db_permission = self.get_permission(permission_id)
        details = {
            "name": db_permission.name,
            "resource": db_permission.resource,
            "action": db_permission.action,
        }
        self.permission_repo.soft_delete(permission_id)
        self.db.commit()
        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="permissions",
            resource_id=permission_id,
            details=details,
            ip_address=ip_address,
        )

    def assign_to_role(
        self,
        permission_id: int,
        role_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        db_permission = self.get_permission(permission_id)
        role = self.permission_repo.get_role_with_permissions(role_id)
        if role is None:
            raise HTTPException(status_code=404, detail="Role not found")

        if db_permission not in role.permissions:
            role.permissions.append(db_permission)
            self.db.commit()
            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="assign",
                resource_type="permissions",
                resource_id=permission_id,
                details={"role_id": role_id, "permission_id": permission_id},
                ip_address=ip_address,
            )

        return {
            "message": f"Permission '{db_permission.name}' assigned to role '{role.name}'"
        }


def get_permission_service(
    db: Session = Depends(get_sync_db),
) -> PermissionService:
    return PermissionService(db)
