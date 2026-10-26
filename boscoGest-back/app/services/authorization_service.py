from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.role_model import Role
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
        1. manage_all shortcut
        2. Direct user permissions (entity-agnostic)
        3. Ancestor chain walk: direct membership gets all perms, ancestors only inheritable
        4. Group permissions (entity-agnostic)
        """
        # 1. manage_all shortcut
        for membership in user.memberships:
            if membership.is_active:
                for perm in membership.role.permissions:
                    if perm.resource == resource and perm.action == "manage_all":
                        return True

        # 2. Direct user permissions
        for perm in user.direct_permissions:
            if perm.resource == resource and perm.action == action:
                return True

        # 3. Ancestor chain walk
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
                if perm.resource == resource and perm.action == action:
                    if is_direct or perm.inheritable:
                        return True

        # 4. Group permissions
        for group in user.groups:
            for role in group.roles:
                for perm in role.permissions:
                    if perm.resource == resource and perm.action == action:
                        return True

        return False

    def has_global_permission(self, user: User, resource: str, action: str) -> bool:
        """Entity-agnostic check: the permission (or manage_all) present in any
        active membership role, group role, or direct permission. Used for
        cross-entity capabilities such as fee maintenance/monitoring."""
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
