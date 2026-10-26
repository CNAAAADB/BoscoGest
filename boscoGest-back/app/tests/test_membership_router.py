import pytest
from datetime import datetime


def test_create_membership(client, auth_headers, test_user, test_entity, test_role, db_session):
    """Test creating a membership - entity_id must be provided"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    new_user = User(
        email="newmember@example.com",
        password_hash=get_password_hash("Password123"),
        name="New",
        surname="Member",
        phone="999999999",
        birthdate=datetime(1998, 9, 9).date(),
        dni="55555555E",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    membership_data = {
        "user_id": new_user.id,
        "role_id": test_role.id,
        "entity_id": test_entity.id,
        "is_active": True
    }

    response = client.post("/memberships", json=membership_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == new_user.id
    assert data["entity_id"] == test_entity.id
    assert data["role_id"] == test_role.id
    assert data["is_active"] is True


def test_create_membership_invalid_user(client, auth_headers, test_role, test_entity):
    membership_data = {
        "user_id": 9999,
        "role_id": test_role.id,
        "entity_id": test_entity.id,
        "is_active": True
    }

    response = client.post("/memberships", json=membership_data, headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_membership_invalid_role(client, auth_headers, test_user, test_entity):
    membership_data = {
        "user_id": test_user.id,
        "role_id": 9999,
        "entity_id": test_entity.id,
        "is_active": True
    }

    response = client.post("/memberships", json=membership_data, headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_membership_unauthorized(client, test_user, test_role, test_entity):
    membership_data = {
        "user_id": test_user.id,
        "role_id": test_role.id,
        "entity_id": test_entity.id,
        "is_active": True
    }

    response = client.post("/memberships", json=membership_data)

    assert response.status_code == 401


def test_get_memberships(client, auth_headers, test_membership):
    response = client.get("/memberships", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(m["id"] == test_membership.id for m in data)


def test_get_memberships_includes_permissions(client, auth_headers, test_membership, test_role):
    """Test that GET /memberships/ includes role permissions in the response"""
    response = client.get("/memberships", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Find the test membership in the response
    membership = next((m for m in data if m["id"] == test_membership.id), None)
    assert membership is not None

    # Verify role is present
    assert "role" in membership
    assert membership["role"] is not None
    assert membership["role"]["id"] == test_role.id
    assert membership["role"]["name"] == test_role.name

    # Verify permissions are present
    assert "permissions" in membership["role"]
    assert isinstance(membership["role"]["permissions"], list)
    assert len(membership["role"]["permissions"]) > 0

    # Verify permission structure
    first_permission = membership["role"]["permissions"][0]
    assert "id" in first_permission
    assert "name" in first_permission
    assert "resource" in first_permission
    assert "action" in first_permission

    # Verify that the role has the expected permissions
    # The admin role should have all permissions
    permission_names = [p["name"] for p in membership["role"]["permissions"]]
    assert "memberships:list" in permission_names
    assert "users:manage" in permission_names


def test_get_memberships_only_current_user(client, auth_headers, test_membership, db_session, test_entity, test_role):
    """Test that get memberships only returns memberships for the current user"""
    from app.models.user_model import User
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash
    from datetime import datetime

    # Crear otro usuario con una membership
    other_user = User(
        email="otheruser@example.com",
        password_hash=get_password_hash("password"),
        name="Other",
        surname="User",
        phone="999999999",
        birthdate=datetime(1995, 5, 5).date(),
        dni="99999999Z",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Crear membership para el otro usuario
    other_membership = Membership(
        user_id=other_user.id,
        entity_id=test_entity.id,
        role_id=test_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_membership)
    db_session.commit()
    db_session.refresh(other_membership)

    response = client.get("/memberships", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar que solo se devuelven las memberships del usuario actual (test_user)
    user_ids = [m["user_id"] for m in data]
    assert all(user_id == test_membership.user_id for user_id in user_ids)
    assert other_user.id not in user_ids
    assert other_membership.id not in [m["id"] for m in data]


def test_get_memberships_unauthorized(client):
    response = client.get("/memberships")

    assert response.status_code == 401


def test_get_membership_by_id(client, auth_headers, test_membership):
    response = client.get(f"/memberships/{test_membership.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_membership.id
    assert data["user_id"] == test_membership.user_id
    assert data["entity_id"] == test_membership.entity_id
    assert data["role_id"] == test_membership.role_id


def test_get_membership_by_id_includes_permissions(client, auth_headers, test_membership, test_role):
    """Test that GET /memberships/{id} includes role permissions in the response"""
    response = client.get(f"/memberships/{test_membership.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify role is present
    assert "role" in data
    assert data["role"] is not None
    assert data["role"]["id"] == test_role.id
    assert data["role"]["name"] == test_role.name

    # Verify permissions are present
    assert "permissions" in data["role"]
    assert isinstance(data["role"]["permissions"], list)
    assert len(data["role"]["permissions"]) > 0

    # Verify permission structure
    first_permission = data["role"]["permissions"][0]
    assert "id" in first_permission
    assert "name" in first_permission
    assert "resource" in first_permission
    assert "action" in first_permission
    assert "description" in first_permission

    # Verify that we have various permissions
    permission_resources = [p["resource"] for p in data["role"]["permissions"]]
    assert "memberships" in permission_resources
    assert "users" in permission_resources


def test_get_membership_not_found(client, auth_headers):
    response = client.get("/memberships/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Membership not found" in response.json()["detail"]


def test_get_membership_no_access(client, auth_headers, db_session, test_entity, test_role):
    """Test that user cannot access membership that doesn't belong to them"""
    from app.models.user_model import User
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash
    from datetime import datetime

    # Crear otro usuario con una membership
    other_user = User(
        email="othermember@example.com",
        password_hash=get_password_hash("password"),
        name="Other",
        surname="Member",
        phone="888888888",
        birthdate=datetime(1992, 3, 3).date(),
        dni="88888888Y",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Crear membership para el otro usuario
    other_membership = Membership(
        user_id=other_user.id,
        entity_id=test_entity.id,
        role_id=test_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_membership)
    db_session.commit()
    db_session.refresh(other_membership)

    # Intentar acceder a la membership de otro usuario
    response = client.get(f"/memberships/{other_membership.id}", headers=auth_headers)

    assert response.status_code == 403
    assert "do not have access" in response.json()["detail"]


def test_update_membership(client, auth_headers, test_membership, test_role, db_session):
    """Test updating membership role"""
    from app.models.role_model import Role

    # Crear un rol diferente para actualizar
    new_role = db_session.query(Role).filter(Role.name == "socio").first()
    if not new_role:
        new_role = Role(
            name="socio",
            description="Member role"
        )
        db_session.add(new_role)
        db_session.commit()
        db_session.refresh(new_role)

    original_role_id = test_membership.role_id

    update_data = {
        "role_id": new_role.id
    }

    response = client.put(f"/memberships/{test_membership.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["role_id"] == new_role.id
    assert data["role_id"] != original_role_id or new_role.id == original_role_id


def test_update_membership_not_found(client, auth_headers):
    update_data = {
        "role_id": 1
    }

    response = client.put("/memberships/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "Membership not found" in response.json()["detail"]


def test_delete_membership(client, auth_headers, db_session, test_user, test_entity, test_role):
    from app.models.membership_model import Membership
    from app.models.entity_model import Entity

    # Crear una entidad diferente para evitar constraint UNIQUE
    different_entity = Entity(
        name="Different Entity for Delete",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(different_entity)
    db_session.flush()

    membership_to_delete = Membership(
        user_id=test_user.id,
        entity_id=different_entity.id,  # Usar entidad diferente
        role_id=test_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(membership_to_delete)
    db_session.commit()
    db_session.refresh(membership_to_delete)

    membership_id = membership_to_delete.id

    response = client.delete(f"/memberships/{membership_id}", headers=auth_headers)

    assert response.status_code == 204

    deleted_membership = db_session.get(Membership, membership_id)
    assert deleted_membership is not None
    assert deleted_membership.is_active is False


def test_delete_membership_not_found(client, auth_headers):
    response = client.delete("/memberships/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Membership not found" in response.json()["detail"]


def test_delete_membership_unauthorized(client, test_membership):
    response = client.delete(f"/memberships/{test_membership.id}")

    assert response.status_code == 401
