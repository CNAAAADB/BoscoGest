from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.role_model import Role
from app.models.entity_model import Entity
from app.repositories.entity_repository import EntityRepository
from app.utils.auth import get_sync_db


class AuthorizationService:
    def __init__(self, db: Session):
        self.db = db
        self.entity_repo = EntityRepository(db)

    def has_effective_permission(
        self,
        user: User,
        target_entity_id: int,
        resource: str,
        action: str,
    ) -> bool:
        """
        Check if user has permission for (resource, action) at target_entity_id,
        considering hierarchical inheritance.

        Resolution order:
        1. Direct user permissions (entity-agnostic)
        2. Ancestor chain walk: direct membership gets all perms, ancestors
           only inheritable. `manage_all` counts as any action on its
           resource, but only along this chain.
        3. Group permissions (entity-agnostic)

        `manage_all` used to be checked first, against every membership the
        user had, wherever it was. The admin role carries it for users,
        entities, resources, communications and comments, so the administrator
        of a single local association could manage those across the whole
        confederation. It now goes through the chain like any other
        permission: superadmin keeps everything because its membership is at
        the root, of which every entity is a descendant.
        """
        # 1. Direct user permissions
        for perm in user.direct_permissions:
            if perm.resource == resource and perm.action == action:
                return True

        # 2. Ancestor chain walk
        ancestor_chain = self.entity_repo.get_ancestor_chain(target_entity_id)
        memberships_in_chain = (
            self.db.execute(
                select(Membership)
                .options(joinedload(Membership.role).joinedload(Role.permissions))
                .where(
                    Membership.user_id == user.id,
                    Membership.entity_id.in_(ancestor_chain),
                    Membership.is_active == True,
                )
            )
            .scalars()
            .unique()
            .all()
        )
        membership_map = {m.entity_id: m for m in memberships_in_chain}

        for i, entity_id in enumerate(ancestor_chain):
            is_direct = i == 0
            membership = membership_map.get(entity_id)
            if not membership:
                continue
            for perm in membership.role.permissions:
                if perm.resource == resource and perm.action in (action, "manage_all"):
                    if is_direct or perm.inheritable:
                        return True

        # 3. Group permissions
        for group in user.groups:
            for role in group.roles:
                for perm in role.permissions:
                    if perm.resource == resource and perm.action == action:
                        return True

        return False

    def has_global_permission(self, user: User, resource: str, action: str) -> bool:
        """Entity-agnostic check: the permission (or manage_all) present in any
        active membership role, group role, or direct permission.

        Only for the visibility tier of user records (user_visibility), which
        is applied to users already within reach. It says nothing about where:
        anything that changes or reveals data across associations must use
        has_effective_permission, has_root_permission or can_reach_user."""
        def matches(perm) -> bool:
            return perm.resource == resource and perm.action in (action, "manage_all")

        for membership in user.memberships:
            if membership.is_active and any(matches(p) for p in membership.role.permissions):
                return True
        for perm in user.direct_permissions:
            if matches(perm):
                return True
        for group in user.groups:
            for role in group.roles:
                if any(matches(p) for p in role.permissions):
                    return True
        return False

    def root_entity_id(self) -> Optional[int]:
        return self.db.execute(
            select(Entity.id).where(Entity.level == 1)
        ).scalars().first()

    def has_root_permission(self, user: User, resource: str, action: str) -> bool:
        """The permission at the root entity, i.e. over the whole platform.

        For what is not scoped to an association — the permission catalogue,
        groups (whose permissions apply everywhere), the consent clause, fee
        maintenance. Holding the permission in some association is not enough:
        that is what let any local administrator rewrite them for everyone.
        """
        root_id = self.root_entity_id()
        if root_id is None:
            return False
        return self.has_effective_permission(user, root_id, resource, action)

    def can_reach_user(self, viewer: User, target: User, action: str) -> bool:
        """Whether `viewer` may perform `action` on users over `target`.

        Yes for oneself; for whoever holds it at the root; and otherwise only
        if `target` belongs to an association where `viewer` holds it. Before
        this, holding users:read anywhere was enough to read anyone by id:
        every member could fetch the name, email and phone of every other.
        """
        if viewer.id == target.id:
            return True
        if self.has_root_permission(viewer, "users", action):
            return True
        return any(
            m.is_active
            and self.has_effective_permission(viewer, m.entity_id, "users", action)
            for m in target.memberships
        )

    def check_entity_permission(
        self,
        user: User,
        target_entity_id: int,
        resource: str,
        action: str,
    ) -> None:
        """Raises HTTPException(403) if user lacks the effective permission."""
        if not self.has_effective_permission(user, target_entity_id, resource, action):
            raise HTTPException(status_code=403, detail="Permission denied")

    def get_accessible_entity_ids(self, user: User) -> List[int]:
        return self.entity_repo.get_accessible_entity_ids(user)


def get_authorization_service(
    db: Session = Depends(get_sync_db),
) -> AuthorizationService:
    return AuthorizationService(db)
