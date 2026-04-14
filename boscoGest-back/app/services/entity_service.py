from typing import List
from datetime import datetime
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.permission_model import Permission
from app.models.relationships import entity_roles
from app.schemas.entity import EntityCreate, EntityUpdate
from app.schemas.role import RoleResponse
from app.repositories.entity_repository import EntityRepository
from app.repositories.membership_repository import MembershipRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db


class EntityService:
    def __init__(self, db: Session):
        self.db = db
        self.entity_repo = EntityRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)

    def get_membership_manageable_entities(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Entity]:
        user_memberships = self.db.execute(
            select(Membership)
            .options(joinedload(Membership.role).joinedload(Role.permissions))
            .where(
                Membership.user_id == current_user.id,
                Membership.is_active == True,
            )
        ).scalars().unique().all()

        allowed_entity_ids = set()
        for membership in user_memberships:
            for permission in membership.role.permissions:
                if (
                    permission.resource == "memberships"
                    and permission.action == "manage"
                ):
                    allowed_entity_ids.add(membership.entity_id)
                    break

        if not allowed_entity_ids:
            return []

        stmt = (
            select(Entity)
            .where(Entity.id.in_(allowed_entity_ids), Entity.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_admin_entities(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Entity]:
        user_memberships = self.db.execute(
            select(Membership)
            .options(joinedload(Membership.role).joinedload(Role.permissions))
            .where(
                Membership.user_id == current_user.id,
                Membership.is_active == True,
            )
        ).scalars().unique().all()

        allowed_entity_ids = set()
        for membership in user_memberships:
            for permission in membership.role.permissions:
                if (
                    permission.resource == "branding"
                    and permission.action
                    in ["read", "update", "manage_all"]
                ) or (
                    permission.resource == "views"
                    and permission.action
                    in ["read", "update", "manage_all"]
                ):
                    allowed_entity_ids.add(membership.entity_id)
                    break

        if not allowed_entity_ids:
            return []

        stmt = (
            select(Entity)
            .where(Entity.id.in_(allowed_entity_ids), Entity.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_entities(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Entity]:
        entity_ids = self.membership_repo.get_entity_ids_by_user(current_user.id)
        if not entity_ids:
            return []

        stmt = (
            select(Entity)
            .where(Entity.id.in_(entity_ids), Entity.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_entity_roles(
        self, entity_id: int, current_user: User
    ) -> List[RoleResponse]:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "entities", "read"
        )

        stmt = (
            select(Role)
            .join(entity_roles, entity_roles.c.role_id == Role.id)
            .where(entity_roles.c.entity_id == entity_id, Role.is_active == True)
        )
        roles = list(self.db.execute(stmt).scalars().all())

        # If user is admin (not superadmin) in this entity, filter out superadmin role
        direct_membership = self.membership_repo.get_by_user_and_entity(
            current_user.id, entity_id, active_only=True
        )
        if direct_membership:
            user_role = self.db.get(Role, direct_membership.role_id)
            if user_role and user_role.name == "admin":
                roles = [r for r in roles if r.name != "superadmin"]

        return [RoleResponse.model_validate(r) for r in roles]

    def get_entity(self, entity_id: int, current_user: User) -> Entity:
        entity = self.db.get(Entity, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        self.auth_service.check_entity_permission(
            current_user, entity_id, "entities", "read"
        )
        return entity

    def create_entity(
        self,
        entity_in: EntityCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Entity:
        parent_entity = self.db.get(Entity, entity_in.parent_id)
        if not parent_entity:
            raise HTTPException(
                status_code=400, detail="Parent entity does not exist"
            )

        self.auth_service.check_entity_permission(
            current_user, entity_in.parent_id, "entities", "create"
        )

        level = parent_entity.level + 1

        if level == 1:
            existing_level_1 = self.db.execute(
                select(Entity).where(Entity.level == 1)
            ).scalars().first()
            if existing_level_1:
                raise HTTPException(
                    status_code=400,
                    detail="Only one level-1 entity is allowed in the system",
                )

        entity = Entity(
            name=entity_in.name,
            level=level,
            parent_id=entity_in.parent_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(entity)
        self.db.flush()

        # Find or create admin role
        admin_role = self.db.execute(
            select(Role).where(Role.name == "admin")
        ).scalars().first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrator role with full permissions",
            )
            self.db.add(admin_role)
            self.db.flush()
            all_permissions = self.db.execute(select(Permission)).scalars().all()
            admin_role.permissions.extend(all_permissions)

        # Find or create socio role
        socio_role = self.db.execute(
            select(Role).where(Role.name == "socio")
        ).scalars().first()
        if not socio_role:
            socio_role = Role(
                name="socio",
                description="Member role with read-only permissions",
            )
            self.db.add(socio_role)
            self.db.flush()
            all_permissions = self.db.execute(select(Permission)).scalars().all()
            read_actions = ["read", "list", "view"]
            socio_permissions = [
                p for p in all_permissions if p.action in read_actions
            ]
            socio_role.permissions.extend(socio_permissions)

        entity.roles.extend([admin_role, socio_role])

        membership = Membership(
            user_id=current_user.id,
            role_id=admin_role.id,
            entity_id=entity.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        self.db.add(membership)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="entities",
            resource_id=entity.id,
            details={"name": entity.name, "level": entity.level},
            ip_address=ip_address,
        )

        return entity

    def update_entity(
        self,
        entity_id: int,
        entity_in: EntityUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> Entity:
        entity = self.db.get(Entity, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        self.auth_service.check_entity_permission(
            current_user, entity_id, "entities", "update"
        )

        update_data = entity_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        self.db.commit()
        self.db.refresh(entity)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="update",
            resource_type="entities",
            resource_id=entity.id,
            details=update_data,
            ip_address=ip_address,
        )

        return entity

    def delete_entity(
        self,
        entity_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        entity = self.db.get(Entity, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        self.auth_service.check_entity_permission(
            current_user, entity_id, "entities", "delete"
        )

        entity_name = entity.name
        entity_level = entity.level

        entity.is_active = False
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="entities",
            resource_id=entity_id,
            details={"name": entity_name, "level": entity_level},
            ip_address=ip_address,
        )

        return {"message": f"Entity '{entity_name}' deleted successfully"}


def get_entity_service(
    db: Session = Depends(get_sync_db),
) -> EntityService:
    return EntityService(db)
