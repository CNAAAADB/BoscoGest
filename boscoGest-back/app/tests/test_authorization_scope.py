"""What an administrator or a member can reach outside their own association.

Before: manage_all counted wherever the membership was, the routes by user id
only asked for the permission somewhere, and so did platform-wide settings.
The administrator of one local association could manage the whole
confederation, and any member could read the name, email and phone of anyone
by trying ids.
"""

from datetime import date, datetime

import pytest

from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.permission_model import Permission
from app.models.role_model import Role
from app.models.user_model import User
from app.utils.auth import create_access_token, get_password_hash


def _user(db, n):
    u = User(
        email=f"persona{n}@ejemplo.com", password_hash=get_password_hash("x"),
        name=f"Persona{n}", surname="Prueba", phone=f"60000000{n}",
        birthdate=date(1960, 1, 1), dni=f"0000000{n}X", is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.flush()
    return u


def _member(db, user, entity, role):
    m = Membership(user_id=user.id, entity_id=entity.id, role_id=role.id,
                   is_active=True, created_at=datetime.utcnow())
    db.add(m)
    db.flush()
    return m


def _headers(user, membership):
    token = create_access_token({"sub": str(user.id), "membership_id": membership.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mundo(db_session, test_entity, test_user, test_membership):
    """Root (test_entity, where test_user is admin) with two sibling associations."""
    db = db_session
    admin = db.query(Role).filter_by(name="admin").one()
    socio = db.query(Role).filter_by(name="socio").one()
    # As in production: admin carries users:manage_all and consent:manage.
    for resource, action in (("users", "manage_all"), ("consent", "manage")):
        perm = db.query(Permission).filter_by(resource=resource, action=action).first()
        if perm is None:
            perm = Permission(name=f"{resource}:{action}", resource=resource,
                              action=action, inheritable=True)
            db.add(perm)
            db.flush()
        admin.permissions.append(perm)

    a = Entity(name="Asociación A", level=2, parent_id=test_entity.id, created_at=datetime.utcnow())
    b = Entity(name="Asociación B", level=2, parent_id=test_entity.id, created_at=datetime.utcnow())
    db.add_all([a, b])
    db.flush()
    a.roles.extend([admin, socio])
    b.roles.extend([admin, socio])

    admin_a, socio_a, socio_b, sin_asociacion = (_user(db, i) for i in range(1, 5))
    m_admin_a = _member(db, admin_a, a, admin)
    m_socio_a = _member(db, socio_a, a, socio)
    _member(db, socio_b, b, socio)
    db.commit()

    return {
        "a": a, "b": b, "root": test_entity,
        "admin_a": admin_a, "socio_a": socio_a, "socio_b": socio_b,
        "sin_asociacion": sin_asociacion, "superadmin": test_user,
        "h_admin_a": _headers(admin_a, m_admin_a),
        "h_socio_a": _headers(socio_a, m_socio_a),
        "h_super": _headers(test_user, test_membership),
    }


# ── manage_all ───────────────────────────────────────────────────────────────

def test_manage_all_only_counts_within_the_membership_hierarchy(db_session, mundo):
    from app.services.authorization_service import AuthorizationService

    auth = AuthorizationService(db_session)
    assert auth.has_effective_permission(mundo["admin_a"], mundo["a"].id, "users", "update")
    # The admin role has users:manage_all; it used to grant this everywhere.
    assert not auth.has_effective_permission(mundo["admin_a"], mundo["b"].id, "users", "update")
    assert not auth.has_effective_permission(mundo["admin_a"], mundo["root"].id, "users", "update")
    # Superadmin's membership is at the root, so it still reaches everything.
    assert auth.has_effective_permission(mundo["superadmin"], mundo["b"].id, "users", "update")


# ── Users by id ──────────────────────────────────────────────────────────────

def test_a_member_cannot_read_people_of_another_association(client, mundo):
    r = client.get(f"/users/{mundo['socio_b'].id}", headers=mundo["h_socio_a"])

    # Not found rather than forbidden: trying ids must not reveal which exist.
    assert r.status_code == 404


def test_a_member_can_read_people_of_their_own_association(client, mundo):
    r = client.get(f"/users/{mundo['admin_a'].id}", headers=mundo["h_socio_a"])

    assert r.status_code == 200
    assert r.json()["name"] == "Persona1"


def test_everyone_can_read_themselves(client, mundo):
    r = client.get(f"/users/{mundo['socio_a'].id}", headers=mundo["h_socio_a"])

    assert r.status_code == 200


def test_searching_by_email_or_dni_does_not_leave_the_association(client, mundo):
    otra = mundo["socio_b"]

    by_email = client.get(f"/users/search/email/{otra.email}", headers=mundo["h_socio_a"])
    by_dni = client.get(f"/users/search/dni/{otra.dni}", headers=mundo["h_socio_a"])

    assert by_email.status_code == 404
    assert by_dni.status_code == 404


def test_a_local_admin_cannot_edit_or_delete_people_of_another_association(client, db_session, mundo):
    otra = mundo["socio_b"]

    put = client.put(f"/users/{otra.id}", json={"name": "Cambiado"}, headers=mundo["h_admin_a"])
    delete = client.delete(f"/users/{otra.id}", headers=mundo["h_admin_a"])

    assert put.status_code == 404
    assert delete.status_code == 404
    db_session.refresh(otra)
    assert otra.name == "Persona3"
    assert otra.is_active is True


def test_a_local_admin_can_edit_people_of_their_association(client, mundo):
    r = client.put(f"/users/{mundo['socio_a'].id}", json={"name": "Cambiado"},
                   headers=mundo["h_admin_a"])

    assert r.status_code == 200
    assert r.json()["name"] == "Cambiado"


def test_superadmin_still_reaches_everyone(client, mundo):
    for target in ("socio_b", "socio_a", "sin_asociacion"):
        r = client.get(f"/users/{mundo[target].id}", headers=mundo["h_super"])
        assert r.status_code == 200, target


def test_the_users_list_was_already_scoped_and_stays_so(client, mundo):
    r = client.get("/users", headers=mundo["h_socio_a"])

    nombres = {u["name"] for u in r.json()["items"]}
    assert "Persona3" not in nombres
    assert {"Persona1", "Persona2"} <= nombres


# ── Platform-wide settings ───────────────────────────────────────────────────

@pytest.mark.parametrize("method, path, body", [
    ("post", "/permissions", {"name": "x:y", "resource": "x", "action": "y"}),
    ("post", "/groups", {"name": "Grupo"}),
    ("get", "/consent-clauses", None),
    ("get", "/fees/maintenance/runs", None),
])
def test_platform_settings_are_not_for_local_admins(client, mundo, method, path, body):
    kwargs = {"headers": mundo["h_admin_a"]}
    if body is not None:
        kwargs["json"] = body

    r = getattr(client, method)(path, **kwargs)

    assert r.status_code == 403, r.json()


def test_platform_settings_stay_available_to_superadmin(client, mundo):
    assert client.get("/consent-clauses", headers=mundo["h_super"]).status_code == 200
    assert client.get("/fees/maintenance/runs", headers=mundo["h_super"]).status_code == 200


def test_the_permission_catalogue_can_still_be_read_by_local_admins(client, mundo):
    """The role form needs it to offer permissions."""
    assert client.get("/permissions", headers=mundo["h_admin_a"]).status_code == 200


# ── Roles ────────────────────────────────────────────────────────────────────

def test_a_local_admin_cannot_rewrite_a_role_shared_with_other_associations(client, db_session, mundo):
    socio = db_session.query(Role).filter_by(name="socio").one()
    antes = {p.id for p in socio.permissions}

    r = client.put(f"/roles/{socio.id}", json={"permission_ids": []}, headers=mundo["h_admin_a"])

    assert r.status_code == 403
    db_session.refresh(socio)
    assert {p.id for p in socio.permissions} == antes


def test_a_local_admin_can_edit_a_role_of_their_own_association(client, db_session, mundo):
    propio = Role(name="Tesorero A", description="")
    db_session.add(propio)
    db_session.flush()
    mundo["a"].roles.append(propio)
    db_session.commit()

    r = client.put(f"/roles/{propio.id}", json={"description": "Lleva las cuotas"},
                   headers=mundo["h_admin_a"])

    assert r.status_code == 200, r.json()


# Regression coverage for data tiers and scoped content/finance access.

def test_financial_records_are_for_authorized_treasurers_only(client, mundo):
    entity_id = mundo["a"].id
    created = client.post("/fees", headers=mundo["h_admin_a"], json={
        "name": "Cuota de prueba", "periodicity": "annual", "entity_ids": [entity_id],
        "amount": 50, "valid_from": str(date.today()),
    })
    assert created.status_code == 201, created.text
    fee_id = created.json()[0]["id"]
    for path in (
        f"/fees/assignments?entity_id={entity_id}",
        f"/fees/members-preview?fee_id={fee_id}",
        f"/fees/{fee_id}/subscriptions",
    ):
        assert client.get(path, headers=mundo["h_socio_a"]).status_code == 403, path
        assert client.get(path, headers=mundo["h_admin_a"]).status_code == 200, path
    assert client.get("/fees/assignments/mine", headers=mundo["h_socio_a"]).status_code == 200


def test_sensitive_fields_and_search_are_limited_to_the_authorized_entity(client, db_session, mundo):
    admin = db_session.query(Role).filter_by(name="admin").one()
    socio = db_session.query(Role).filter_by(name="socio").one()
    p = Permission(name="users:read_sensitive", resource="users", action="read_sensitive", inheritable=False)
    db_session.add(p)
    db_session.flush()
    admin.permissions.append(p)
    _member(db_session, mundo["admin_a"], mundo["root"], socio)
    _member(db_session, mundo["socio_b"], mundo["root"], socio)
    db_session.commit()
    headers = mundo["h_admin_a"]
    own = client.get(f"/users/{mundo['socio_a'].id}", headers=headers)
    assert own.status_code == 200 and own.json()["dni"] == mundo["socio_a"].dni
    other = client.get(f"/users/{mundo['socio_b'].id}", headers=headers)
    assert other.status_code == 200
    assert other.json()["dni"] is None and other.json()["birthdate"] is None
    for membership in other.json()["memberships"]:
        assert membership["user"] is None or membership["user"]["dni"] is None
    assert client.get(f"/users/search/dni/{mundo['socio_b'].dni}", headers=headers).status_code == 404
    result = client.get("/users", params={"search": mundo["socio_b"].dni}, headers=headers)
    assert result.status_code == 200 and result.json()["total"] == 0
    assert client.get(f"/users/{mundo['socio_a'].id}", headers=mundo["h_socio_a"]).json()["dni"] == mundo["socio_a"].dni


def test_communications_drafts_and_comments_are_scoped(client, db_session, mundo):
    from app.models.communication_model import Communication
    from app.models.comment_model import Comment

    socio = db_session.query(Role).filter_by(name="socio").one()
    for user in (mundo["admin_a"], mundo["socio_a"]):
        _member(db_session, user, mundo["root"], socio)
    own_comment = db_session.query(Permission).filter_by(resource="comment", action="delete").one()
    socio.permissions.append(own_comment)
    root_draft = Communication(title="Borrador nacional", content="Privado", entity_id=mundo["root"].id,
                               created_by_id=mundo["superadmin"].id, status="draft")
    local_draft = Communication(title="Borrador local", content="Privado", entity_id=mundo["a"].id,
                                created_by_id=mundo["admin_a"].id, status="draft")
    published = Communication(title="Comunicado nacional", content="Visible", entity_id=mundo["root"].id,
                              created_by_id=mundo["superadmin"].id, status="published")
    db_session.add_all([root_draft, local_draft, published])
    db_session.flush()
    comment = Comment(content="Comentario ajeno", communication_id=published.id, user_id=mundo["superadmin"].id)
    db_session.add(comment)
    db_session.commit()
    headers = mundo["h_admin_a"]
    result = client.get("/communications?status=draft", headers=headers)
    assert result.status_code == 200
    assert {row["id"] for row in result.json()} == {local_draft.id}
    assert client.get("/communications/count?status=draft", headers=headers).json()["total"] == 1
    assert client.get(f"/communications/{root_draft.id}", headers=headers).status_code == 404
    assert client.get("/communications?status=draft", headers=mundo["h_socio_a"]).json() == []
    detail = client.get(f"/communications/{published.id}", headers=headers)
    assert detail.status_code == 200 and not detail.json()["permissions"]["delete"]
    assert client.put(f"/comments/comments/{comment.id}", json={"content": "No"}, headers=headers).status_code == 403
    assert client.delete(f"/comments/comments/{comment.id}", headers=headers).status_code == 403
    assert client.delete(f"/comments/comments/{comment.id}", headers=mundo["h_super"]).status_code == 200


def test_content_actions_do_not_inherit_upwards(client, db_session, mundo):
    from app.models.resource_model import Resource, ResourceType
    from app.models.magazine_model import Magazine

    socio = db_session.query(Role).filter_by(name="socio").one()
    admin = db_session.query(Role).filter_by(name="admin").one()
    _member(db_session, mundo["admin_a"], mundo["root"], socio)
    for action in ("read", "update", "delete"):
        perm = Permission(name=f"magazines:{action}", resource="magazines", action=action, inheritable=True)
        db_session.add(perm)
        db_session.flush()
        admin.permissions.append(perm)
        if action == "read":
            socio.permissions.append(perm)
    resource = Resource(title="Recurso nacional", resource_type=ResourceType.LINK, url="https://example.com",
                        entity_id=mundo["root"].id, created_by=mundo["superadmin"].id)
    magazine = Magazine(title="Revista nacional", file_path="test.pdf", entity_id=mundo["root"].id)
    db_session.add_all([resource, magazine])
    db_session.commit()
    headers = mundo["h_admin_a"]
    for prefix, row in (("resources", resource), ("magazines", magazine)):
        path = f"/{prefix}/{row.id}"
        detail = client.get(path, headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["permissions"] == {"update": False, "delete": False}
        assert client.put(path, json={"title": "No"}, headers=headers).status_code == 403
        assert client.delete(path, headers=headers).status_code == 403


def test_shared_scope_rejects_inactive_memberships_and_unscoped_grants(db_session, mundo):
    from app.services.scoped_permissions import ScopedPermissions

    user = mundo["admin_a"]
    permission = db_session.query(Permission).filter_by(resource="resources", action="update").one()
    user.direct_permissions.append(permission)
    db_session.commit()
    assert not ScopedPermissions(db_session).allows(user, mundo["b"].id, "resources", "update")
    assert ScopedPermissions(db_session).allows(user, mundo["a"].id, "resources", "update")
    for membership in user.memberships:
        membership.is_active = False
    db_session.commit()
    assert not ScopedPermissions(db_session).allows(user, mundo["a"].id, "resources", "update")
