from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.group_model import Group
from app.models.user_model import User
from app.models.role_model import Role
from app.schemas.group import GroupCreate
from app.repositories.group_repository import GroupRepository
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db


class GroupService:
    def __init__(self, db: Session):
        self.db = db
        self.group_repo = GroupRepository(db)
        self.audit_service = AuditService(db)

    def create_group(
        self,
        group_in: GroupCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Group:
        try:
            db_group = Group(**group_in.model_dump())
            self.group_repo.create(db_group)
            self.db.commit()
            self.db.refresh(db_group)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="groups",
                resource_id=db_group.id,
                details=group_in.model_dump(),
                ip_address=ip_address,
            )

            return db_group
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Group name already exists",
            )

    def list_groups(self, skip: int = 0, limit: int = 100) -> List[Group]:
        return self.group_repo.get_all_active(skip=skip, limit=limit)

    def get_group(self, group_id: int) -> Group:
        db_group = self.group_repo.get_by_id_with_relations(group_id)
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")
        return db_group

    def update_group(
        self,
        group_id: int,
        group_update: GroupCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Group:
        db_group = self.group_repo.get_by_id(group_id)
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")

        update_data = group_update.model_dump(exclude_unset=True)

        try:
            if update_data:
                self.group_repo.update(group_id, update_data)

            self.db.commit()

            # Reload the updated group
            db_group = self.group_repo.get_by_id(group_id)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="groups",
                resource_id=group_id,
                details=update_data,
                ip_address=ip_address,
            )

            return db_group
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Group name already exists",
            )

    def delete_group(
        self,
        group_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        db_group = self.group_repo.get_by_id(group_id)
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")

        group_name = db_group.name

        self.group_repo.soft_delete(group_id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="groups",
            resource_id=group_id,
            details={"name": group_name},
            ip_address=ip_address,
        )

    def add_user_to_group(
        self,
        group_id: int,
        user_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        group = self.group_repo.get_by_id_with_relations(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user not in group.users:
            group.users.append(user)
            self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="assign",
                resource_type="groups",
                resource_id=group_id,
                details={"user_id": user_id},
                ip_address=ip_address,
            )

        return {"message": f"User '{user.email}' added to group '{group.name}'"}

    def remove_user_from_group(
        self,
        group_id: int,
        user_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        group = self.group_repo.get_by_id_with_relations(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user in group.users:
            group.users.remove(user)
            self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="remove",
                resource_type="groups",
                resource_id=group_id,
                details={"user_id": user_id},
                ip_address=ip_address,
            )

        return {"message": f"User '{user.email}' removed from group '{group.name}'"}

    def assign_role_to_group(
        self,
        group_id: int,
        role_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        group = self.group_repo.get_by_id_with_relations(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        role = self.db.get(Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        if role not in group.roles:
            group.roles.append(role)
            self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="assign",
                resource_type="groups",
                resource_id=group_id,
                details={"role_id": role_id},
                ip_address=ip_address,
            )

        return {"message": f"Role '{role.name}' assigned to group '{group.name}'"}

    def remove_role_from_group(
        self,
        group_id: int,
        role_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        group = self.group_repo.get_by_id_with_relations(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        role = self.db.get(Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        if role in group.roles:
            group.roles.remove(role)
            self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="remove",
                resource_type="groups",
                resource_id=group_id,
                details={"role_id": role_id},
                ip_address=ip_address,
            )

        return {"message": f"Role '{role.name}' removed from group '{group.name}'"}


def get_group_service(db: Session = Depends(get_sync_db)) -> GroupService:
    return GroupService(db)
