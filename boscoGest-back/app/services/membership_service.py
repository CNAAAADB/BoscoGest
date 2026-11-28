from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.models.membership_model import Membership
from app.models.user_model import User
from app.models.role_model import Role
from app.models.entity_model import Entity
from app.repositories.membership_repository import MembershipRepository
from app.repositories.entity_repository import EntityRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.schemas.permission import PermissionResponse
from app.utils.auth import get_sync_db, is_root_superadmin


class MembershipService:
    def __init__(self, db: Session):
        self.db = db
        self.membership_repo = MembershipRepository(db)
        self.entity_repo = EntityRepository(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    def create_membership(
        self,
        membership_in,
        current_user: User,
        ip_address: str | None = None,
    ) -> Membership:
        self.auth_service.check_entity_permission(
            current_user, membership_in.entity_id, "memberships", "create"
        )

        try:
            user = self.db.get(User, membership_in.user_id)
            role = self.db.get(Role, membership_in.role_id)
            entity = self.db.get(Entity, membership_in.entity_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {membership_in.user_id} not found",
                )
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with id {membership_in.role_id} not found",
                )
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Entity with id {membership_in.entity_id} not found",
                )

            self.auth_service.check_superadmin_assignment(current_user, entity, role)

            existing = self.membership_repo.get_by_user_and_entity(
                membership_in.user_id,
                membership_in.entity_id,
                role_id=membership_in.role_id,
                active_only=True,
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Active membership already exists for user {membership_in.user_id} "
                    f"in entity {membership_in.entity_id} with role {membership_in.role_id}",
                )

            db_membership = Membership(**membership_in.model_dump())
            self.db.add(db_membership)
            self.db.commit()
            self.db.refresh(db_membership)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="memberships",
                resource_id=db_membership.id,
                details={
                    "user_id": membership_in.user_id,
                    "role_id": membership_in.role_id,
                    "entity_id": membership_in.entity_id,
                },
                ip_address=ip_address,
            )

            self.notification_service.notify(
                event_type=EventType.MEMBERSHIP_CREATED,
                entity_id=membership_in.entity_id,
                actor=current_user,
                resource_type="memberships",
                resource_id=db_membership.id,
                title=f"Nueva membresía en {entity.name}",
                recipient_ids=[membership_in.user_id],
            )

            self.create_parent_memberships(
                membership_in.user_id,
                membership_in.entity_id,
                current_user,
                ip_address=ip_address,
            )

            return db_membership

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership already exists or violates database constraints",
            )

    def create_parent_memberships(
        self,
        user_id: int,
        entity_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        """Create memberships for all parent entities with 'socio' role.
        This consolidates the duplicated parent-membership logic from
        user_router and membership_router."""
        parent_entity_ids = self.entity_repo.get_parent_entity_ids(entity_id)
        if not parent_entity_ids:
            return

        socio_role = self.db.execute(
            select(Role).where(Role.name == "socio", Role.is_active == True)
        ).scalars().first()

        if not socio_role:
            return

        created_any = False
        for parent_entity_id in parent_entity_ids:
            existing = self.membership_repo.get_by_user_and_entity(
                user_id, parent_entity_id, active_only=True
            )
            if not existing:
                parent_membership = Membership(
                    user_id=user_id,
                    entity_id=parent_entity_id,
                    role_id=socio_role.id,
                    is_active=True,
                )
                self.db.add(parent_membership)
                created_any = True

        if created_any:
            self.db.commit()
            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="memberships",
                resource_id=None,
                details={
                    "user_id": user_id,
                    "parent_entity_ids": parent_entity_ids,
                    "role": "socio",
                    "auto_created": True,
                    "reason": "parent_entity_memberships",
                },
                ip_address=ip_address,
            )

    def list_memberships(self, current_user: User) -> list:
        memberships = self.membership_repo.get_user_memberships_with_relations(
            current_user.id
        )

        response_data = []
        for m in memberships:
            membership_dict = {
                "id": m.id,
                "user_id": m.user_id,
                "role_id": m.role_id,
                "entity_id": m.entity_id,
                "is_active": m.is_active,
                "created_at": m.created_at,
                "user": m.user,
                "entity": m.entity,
                "role": None,
            }
            if m.role:
                membership_dict["role"] = {
                    "id": m.role.id,
                    "name": m.role.name,
                    "description": m.role.description,
                    "is_active": m.role.is_active,
                    "permissions": [
                        PermissionResponse.model_validate(p).model_dump()
                        for p in m.role.permissions
                    ],
                }
            response_data.append(membership_dict)

        return response_data

    def get_membership(self, membership_id: int, current_user: User) -> dict:
        membership = self.membership_repo.get_by_id_with_relations(membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        if membership.user_id != current_user.id and not is_root_superadmin(current_user):
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this membership",
            )

        membership_dict = {
            "id": membership.id,
            "user_id": membership.user_id,
            "role_id": membership.role_id,
            "entity_id": membership.entity_id,
            "is_active": membership.is_active,
            "created_at": membership.created_at,
            "user": membership.user,
            "entity": membership.entity,
            "role": None,
        }
        if membership.role:
            membership_dict["role"] = {
                "id": membership.role.id,
                "name": membership.role.name,
                "description": membership.role.description,
                "is_active": membership.role.is_active,
                "permissions": [
                    PermissionResponse.model_validate(p).model_dump()
                    for p in membership.role.permissions
                ],
            }

        return membership_dict

    def update_membership(
        self,
        membership_id: int,
        membership_update,
        current_user: User,
        ip_address: str | None = None,
    ) -> Membership:
        db_membership = self.membership_repo.get_by_id(membership_id)
        if not db_membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        self.auth_service.check_entity_permission(
            current_user, db_membership.entity_id, "memberships", "update"
        )

        update_data = membership_update.model_dump(exclude_unset=True)
        if db_membership.role.name == "superadmin" and not is_root_superadmin(current_user):
            raise HTTPException(status_code=403, detail="No puedes modificar una membresía Superadmin")
        if update_data.get("role_id") is not None:
            role = self.db.get(Role, update_data["role_id"])
            if role is not None:
                self.auth_service.check_superadmin_assignment(current_user, db_membership.entity, role)
        try:
            if update_data:
                self.membership_repo.update(membership_id, update_data)
                self.db.commit()

            self.db.refresh(db_membership)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="memberships",
                resource_id=membership_id,
                details=update_data,
                ip_address=ip_address,
            )

            return db_membership

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=409, detail="Conflict updating membership"
            )

    def delete_membership(
        self,
        membership_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        membership = self.membership_repo.get_by_id(membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        self.auth_service.check_entity_permission(
            current_user, membership.entity_id, "memberships", "delete"
        )

        if membership.role.name == "superadmin" and not is_root_superadmin(current_user):
            raise HTTPException(status_code=403, detail="No puedes eliminar una membresía Superadmin")
        membership.is_active = False
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="memberships",
            resource_id=membership_id,
            details={
                "user_id": membership.user_id,
                "entity_id": membership.entity_id,
            },
            ip_address=ip_address,
        )


def get_membership_service(
    db: Session = Depends(get_sync_db),
) -> MembershipService:
    return MembershipService(db)
