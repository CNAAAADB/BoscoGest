import pytest
from fastapi import HTTPException
from datetime import datetime

from app.models.user_model import User
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.membership_model import Membership
from app.models.group_model import Group
from app.utils.auth import (
    get_entity_ancestor_chain,
    has_effective_permission,
    check_entity_permission,
    get_password_hash,
)


# --- Helper to create a user quickly ---

def _make_user(db_session, email="hier@test.com"):
    user = User(
        email=email,
        password_hash=get_password_hash("password"),
        name="Hier",
        surname="Test",
        phone="000000000",
        birthdate=datetime(1990, 1, 1).date(),
        dni=f"00000000{email[0].upper()}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_role(db_session, name, permissions):
    role = Role(name=name, description=f"{name} role")
    db_session.add(role)
    db_session.flush()
    role.permissions.extend(permissions)
    db_session.commit()
    return role


def _make_membership(db_session, user, entity, role, is_active=True):
    m = Membership(
        user_id=user.id,
        entity_id=entity.id,
        role_id=role.id,
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(user)
    return m


# ============================================================
# 1. Ancestor chain: correct order
# ============================================================

def test_ancestor_chain_order(db_session, entity_hierarchy):
    h = entity_hierarchy
    chain = get_entity_ancestor_chain(db_session, h["local"].id)
    assert chain == [h["local"].id, h["federation"].id, h["confederation"].id, h["superentity"].id]


# ============================================================
# 2. Ancestor chain: root entity returns only itself
# ============================================================

def test_ancestor_chain_root(db_session, entity_hierarchy):
    h = entity_hierarchy
    chain = get_entity_ancestor_chain(db_session, h["superentity"].id)
    assert chain == [h["superentity"].id]


# ============================================================
# 3. Direct membership grants ALL permissions (including non-inheritable)
# ============================================================

def test_direct_membership_all_perms(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h3", [p[("entities", "delete")], p[("users", "create")]])
    _make_membership(db_session, user, h["federation"], role)

    # Non-inheritable permission works at the direct entity
    assert has_effective_permission(db_session, user, h["federation"].id, "entities", "delete") is True
    # Inheritable permission also works at the direct entity
    assert has_effective_permission(db_session, user, h["federation"].id, "users", "create") is True


# ============================================================
# 4. Inheritable permission cascades to descendant
# ============================================================

def test_inheritable_cascades_down(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h4", [p[("users", "create")]])
    _make_membership(db_session, user, h["federation"], role)

    # users:create is inheritable -> should work at Local (child of Federation)
    assert has_effective_permission(db_session, user, h["local"].id, "users", "create") is True


# ============================================================
# 5. Non-inheritable permission does NOT cascade
# ============================================================

def test_non_inheritable_blocked_down(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h5", [p[("entities", "delete")]])
    _make_membership(db_session, user, h["federation"], role)

    # entities:delete is NOT inheritable -> blocked at Local
    assert has_effective_permission(db_session, user, h["local"].id, "entities", "delete") is False


# ============================================================
# 6. No ancestor membership -> denied
# ============================================================

def test_no_ancestor_membership_denied(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    # Create a separate branch: another confederation under the superentity
    conf_b = Entity(name="Confederation B", level=2, parent_id=h["superentity"].id, created_at=datetime.utcnow())
    db_session.add(conf_b)
    db_session.flush()
    fed_b = Entity(name="Federation B", level=3, parent_id=conf_b.id, created_at=datetime.utcnow())
    db_session.add(fed_b)
    db_session.flush()
    db_session.commit()

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h6", [p[("users", "read")]])
    # Membership in Confederation A branch only
    _make_membership(db_session, user, h["confederation"], role)

    # Check against Confederation B branch -> denied (no ancestry relation)
    assert has_effective_permission(db_session, user, fed_b.id, "users", "read") is False


# ============================================================
# 7. manage_all bypasses hierarchy
# ============================================================

def test_manage_all_bypasses(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "superadmin_h7", [p[("entities", "manage_all")]])
    _make_membership(db_session, user, h["superentity"], role)

    # entities:manage_all should grant access even for non-inheritable entities:delete
    assert has_effective_permission(db_session, user, h["local"].id, "entities", "delete") is True


# ============================================================
# 8. Direct membership at lower level overrides ancestor
# ============================================================

def test_direct_overrides_ancestor(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)

    # Socio role at Federation (L3) -> only read permissions
    socio_role = _make_role(db_session, "socio_h8", [p[("users", "read")]])
    _make_membership(db_session, user, h["federation"], socio_role)

    # Admin role at Local (L4) -> has create
    admin_role = _make_role(db_session, "admin_h8", [p[("users", "create")]])
    _make_membership(db_session, user, h["local"], admin_role)

    # Direct membership at Local grants users:create
    assert has_effective_permission(db_session, user, h["local"].id, "users", "create") is True


# ============================================================
# 9. Inactive membership is ignored
# ============================================================

def test_inactive_membership_ignored(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h9", [p[("users", "read")]])
    _make_membership(db_session, user, h["federation"], role, is_active=False)

    # Inactive membership -> should not grant inherited permission
    assert has_effective_permission(db_session, user, h["local"].id, "users", "read") is False
    # Also not at the direct entity
    assert has_effective_permission(db_session, user, h["federation"].id, "users", "read") is False


# ============================================================
# 10. Group permissions still work (entity-agnostic)
# ============================================================

def test_group_permissions_work(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)

    role = _make_role(db_session, "group_role_h10", [p[("users", "read")]])
    group = Group(name="test_group_h10")
    db_session.add(group)
    db_session.flush()
    group.roles.append(role)
    user.groups.append(group)
    db_session.commit()
    db_session.refresh(user)

    # Group permission is entity-agnostic -> works anywhere
    assert has_effective_permission(db_session, user, h["local"].id, "users", "read") is True


# ============================================================
# 11. Direct user permissions still work (entity-agnostic)
# ============================================================

def test_direct_user_permissions_work(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    user.direct_permissions.append(p[("activities", "create")])
    db_session.commit()
    db_session.refresh(user)

    # Direct permission is entity-agnostic
    assert has_effective_permission(db_session, user, h["local"].id, "activities", "create") is True


# ============================================================
# 12. check_entity_permission raises HTTPException 403
# ============================================================

def test_check_entity_permission_403(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy

    user = _make_user(db_session)
    # No memberships, no permissions

    with pytest.raises(HTTPException) as exc_info:
        check_entity_permission(db_session, user, h["local"].id, "users", "delete")
    assert exc_info.value.status_code == 403


# ============================================================
# 13. Branding non-inheritable: works at direct, blocked at child
# ============================================================

def test_branding_non_inheritable(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h13", [p[("branding", "update")]])
    _make_membership(db_session, user, h["federation"], role)

    # Direct entity -> allowed
    assert has_effective_permission(db_session, user, h["federation"].id, "branding", "update") is True
    # Child entity -> blocked (non-inheritable)
    assert has_effective_permission(db_session, user, h["local"].id, "branding", "update") is False


# ============================================================
# 14. Multi-level inheritance (L2 -> L4, skipping L3)
# ============================================================

def test_multi_level_inheritance(db_session, entity_hierarchy, hierarchy_permissions):
    h = entity_hierarchy
    p = hierarchy_permissions

    user = _make_user(db_session)
    role = _make_role(db_session, "admin_h14", [p[("users", "list")]])
    # Membership at Confederation (L2) only
    _make_membership(db_session, user, h["confederation"], role)

    # users:list is inheritable -> should cascade to Local (L4), skipping Federation (L3)
    assert has_effective_permission(db_session, user, h["local"].id, "users", "list") is True


# Root superadmin must not depend on the role's stored permission catalogue.
def test_root_superadmin_without_permissions_can_manage_all_levels(db_session, entity_hierarchy):
    from app.services.authorization_service import AuthorizationService
    from app.utils.auth import has_permission, is_root_superadmin, require_permission

    user = _make_user(db_session)
    role = _make_role(db_session, "superadmin", [])
    membership = _make_membership(db_session, user, entity_hierarchy["superentity"], role)
    auth = AuthorizationService(db_session)
    assert is_root_superadmin(user)
    for entity in entity_hierarchy.values():
        for resource, action in (("memberships", "review"), ("roles", "assign"),
                                 ("branding", "update"), ("future_resource", "manage")):
            assert auth.has_effective_permission(user, entity.id, resource, action)
    assert auth.has_root_permission(user, "views", "update")
    assert auth.has_global_permission(user, "users", "read_sensitive")
    assert has_permission(user, "fees", "create")
    assert require_permission("fees", "create")(user) is user

    membership.is_active = False
    db_session.commit()
    assert not is_root_superadmin(user)
    assert not auth.has_root_permission(user, "views", "update")
    assert not auth.has_effective_permission(user, entity_hierarchy["local"].id, "memberships", "review")


def test_superadmin_name_at_lower_level_is_not_platform_authority(db_session, entity_hierarchy):
    from app.services.authorization_service import AuthorizationService
    from app.utils.auth import is_root_superadmin

    user = _make_user(db_session)
    role = _make_role(db_session, "superadmin", [])
    _make_membership(db_session, user, entity_hierarchy["federation"], role)
    auth = AuthorizationService(db_session)
    assert not is_root_superadmin(user)
    assert not auth.has_root_permission(user, "views", "update")
    assert not auth.has_effective_permission(user, entity_hierarchy["local"].id, "memberships", "review")
    with pytest.raises(HTTPException) as exc:
        auth.check_superadmin_assignment(user, entity_hierarchy["superentity"], role)
    assert exc.value.status_code == 403


def test_only_root_superadmin_can_assign_reserved_role(db_session, entity_hierarchy, hierarchy_permissions):
    from app.services.authorization_service import AuthorizationService

    auth = AuthorizationService(db_session)
    user = _make_user(db_session)
    role = _make_role(db_session, "superadmin", [])
    _make_membership(db_session, user, entity_hierarchy["superentity"], role)
    auth.check_superadmin_assignment(user, entity_hierarchy["superentity"], role)
    with pytest.raises(HTTPException):
        auth.check_superadmin_assignment(user, entity_hierarchy["local"], role)
