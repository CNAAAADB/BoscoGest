from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.user_model import User
from app.models.relationships import entity_roles
from app.schemas.role import RoleCreate, RoleUpdate
from app.repositories.role_repository import RoleRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db


class RoleService:
    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.audit_service = AuditService(db)
        self.auth_service = AuthorizationService(db)

    def ensure_superadmin_has_all_permissions(self) -> None:
        """
        Ensure that the superadmin role has all available permissions.
        This is called automatically when retrieving the superadmin role.
        """
        superadmin_role = self.role_repo.get_superadmin_role()
        if not superadmin_role:
            return

        # Get all active permissions
        stmt = select(Permission).where(Permission.is_active == True)
        all_permissions = list(self.db.execute(stmt).scalars().all())

        # Determine missing permissions
        current_permission_ids = {p.id for p in superadmin_role.permissions}
        all_permission_ids = {p.id for p in all_permissions}
        missing_permission_ids = all_permission_ids - current_permission_ids

        if missing_permission_ids:
            missing_permissions = [
                p for p in all_permissions if p.id in missing_permission_ids
            ]
            superadmin_role.permissions.extend(missing_permissions)
            self.db.commit()

    def create_role(
        self,
        role_in: RoleCreate,
        current_user: User,
        current_membership: Membership,
        ip_address: str | None = None,
    ) -> Role:
        # Check hierarchical permission on the membership's entity
        self.auth_service.check_entity_permission(
            current_user, current_membership.entity_id, "roles", "create"
        )

        try:
            # Extract permission_ids before creating the role
            permission_ids = role_in.permission_ids
            role_data = role_in.model_dump(exclude={"permission_ids"})

            db_role = Role(**role_data)
            self.role_repo.create(db_role)

            # Associate role with the entity of the user's current membership
            stmt = select(Entity).where(Entity.id == current_membership.entity_id)
            entity = self.db.execute(stmt).scalars().first()
            if entity:
                entity.roles.append(db_role)

            # Assign permissions if provided
            if permission_ids:
                # Remove duplicates
                unique_permission_ids = list(set(permission_ids))

                stmt = select(Permission).where(
                    Permission.id.in_(unique_permission_ids)
                )
                permissions = list(self.db.execute(stmt).scalars().all())

                # Filter out manage_all permissions - exclusive to superadmin
                filtered_permissions = [
                    p for p in permissions if p.action != "manage_all"
                ]

                # Validate that all permission IDs exist
                if len(permissions) != len(unique_permission_ids):
                    self.db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or more permission IDs not found",
                    )

                db_role.permissions.extend(filtered_permissions)

            self.db.commit()
            self.db.refresh(db_role)

            # Reload with permissions
            db_role = self.role_repo.get_by_id_with_permissions(db_role.id)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="roles",
                resource_id=db_role.id,
                details=role_in.model_dump(),
                ip_address=ip_address,
            )

            return db_role
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role name already exists",
            )

    def list_roles(
        self,
        current_user: User,
        current_membership: Membership,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Role]:
        # Check hierarchical permission on the membership's entity
        self.auth_service.check_entity_permission(
            current_user, current_membership.entity_id, "roles", "list"
        )
        return self.role_repo.get_by_entity_id(
            current_membership.entity_id, skip=skip, limit=limit
        )

    def get_role(self, role_id: int) -> Role:
        # Ensure superadmin has all permissions before retrieval
        self.ensure_superadmin_has_all_permissions()

        db_role = self.role_repo.get_by_id_with_permissions(role_id)
        if not db_role:
            raise HTTPException(status_code=404, detail="Role not found")
        return db_role

    def update_role(
        self,
        role_id: int,
        role_update: RoleUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Role:
        db_role = self.role_repo.get_by_id_with_permissions(role_id)
        if not db_role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Prevent modification of superadmin role
        if db_role.name == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify superadmin role - it always has all permissions",
            )

        update_data = role_update.model_dump(exclude_unset=True)

        # Extract permission_ids before removing from update_data
        # None means not provided (keep existing), [] means clear all, [1,2] means replace
        permission_ids = (
            update_data.pop("permission_ids", None)
            if "permission_ids" in update_data
            else None
        )

        # Remove 'name' from update_data to prevent modification
        if "name" in update_data:
            del update_data["name"]

        try:
            # Update basic fields via repository
            if update_data:
                self.role_repo.update(role_id, update_data)

            # Handle permissions update if provided
            if permission_ids is not None:
                # Preserve manage_all permissions if they exist
                existing_manage_all_perms = [
                    p for p in db_role.permissions if p.action == "manage_all"
                ]

                # Clear existing permissions
                db_role.permissions.clear()

                # Re-add manage_all permissions (if they existed)
                if existing_manage_all_perms:
                    db_role.permissions.extend(existing_manage_all_perms)

                if permission_ids:  # Not empty list
                    # Remove duplicates
                    unique_permission_ids = list(set(permission_ids))

                    stmt = select(Permission).where(
                        Permission.id.in_(unique_permission_ids)
                    )
                    permissions = list(self.db.execute(stmt).scalars().all())

                    # Filter out manage_all permissions - exclusive to superadmin
                    filtered_permissions = [
                        p for p in permissions if p.action != "manage_all"
                    ]

                    # Validate that all permission IDs exist
                    if len(permissions) != len(unique_permission_ids):
                        self.db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="One or more permission IDs not found",
                        )

                    db_role.permissions.extend(filtered_permissions)

            self.db.commit()

            # Reload role with updated relations
            db_role = self.role_repo.get_by_id_with_permissions(role_id)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="roles",
                resource_id=role_id,
                details=role_update.model_dump(exclude_unset=True),
                ip_address=ip_address,
            )

            return db_role
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role name already exists",
            )

    def delete_role(
        self,
        role_id: int,
        current_user: User,
        current_membership: Membership,
        ip_address: str | None = None,
    ) -> dict:
        # Check hierarchical permission on the membership's entity
        self.auth_service.check_entity_permission(
            current_user, current_membership.entity_id, "roles", "delete"
        )

        db_role = self.role_repo.get_by_id(role_id)
        if not db_role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Check entity associations
        associated_entity_ids = self.role_repo.get_entity_associations(role_id)

        # Allow deletion only if:
        # 1. Role is not associated with any entity (len == 0)
        # 2. Role is associated ONLY with the current membership's entity
        if len(associated_entity_ids) == 0:
            pass  # No associations, allow deletion
        elif (
            len(associated_entity_ids) == 1
            and associated_entity_ids[0] == current_membership.entity_id
        ):
            pass  # Only associated with current entity, allow deletion
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete role: it is associated with other entities or multiple entities",
            )

        role_name = db_role.name

        # Soft delete
        self.role_repo.soft_delete(role_id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="roles",
            resource_id=role_id,
            details={"name": role_name},
            ip_address=ip_address,
        )

        return {"detail": "Role deleted successfully"}


def get_role_service(db: Session = Depends(get_sync_db)) -> RoleService:
    return RoleService(db)
