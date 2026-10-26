import pytest


def test_create_permission(client, auth_headers):
    permission_data = {
        "name": "test:action",
        "resource": "test",
        "action": "action",
        "description": "Test permission"
    }

    response = client.post("/permissions", json=permission_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test:action"
    assert data["resource"] == "test"
    assert data["action"] == "action"
    assert data["description"] == "Test permission"


def test_create_permission_with_conditions(client, auth_headers):
    permission_data = {
        "name": "test:conditional",
        "resource": "test",
        "action": "conditional",
        "description": "Conditional permission",
        "conditions": {"time_between": ["09:00", "17:00"]}
    }

    response = client.post("/permissions", json=permission_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["conditions"] == {"time_between": ["09:00", "17:00"]}


def test_create_permission_duplicate(client, auth_headers, test_permissions):
    existing = test_permissions[0]
    permission_data = {
        "name": existing.name,
        "resource": existing.resource,
        "action": existing.action,
        "description": "Duplicate"
    }

    response = client.post("/permissions", json=permission_data, headers=auth_headers)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_permission_unauthorized(client):
    permission_data = {
        "name": "unauthorized:test",
        "resource": "test",
        "action": "test"
    }

    response = client.post("/permissions", json=permission_data)

    assert response.status_code == 401


def test_get_permissions(client, auth_headers, test_permissions):
    response = client.get("/permissions", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= len(test_permissions)


def test_get_permissions_with_pagination(client, auth_headers):
    response = client.get("/permissions?skip=0&limit=10", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_get_permissions_unauthorized(client):
    response = client.get("/permissions")

    assert response.status_code == 401


def test_get_permission_by_id(client, auth_headers, test_permissions):
    permission = test_permissions[0]
    response = client.get(f"/permissions/{permission.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == permission.id
    assert data["name"] == permission.name
    assert data["resource"] == permission.resource
    assert data["action"] == permission.action


def test_get_permission_not_found(client, auth_headers):
    response = client.get("/permissions/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Permission not found" in response.json()["detail"]


def test_update_permission(client, auth_headers, test_permissions):
    permission = test_permissions[0]
    update_data = {
        "description": "Updated description"
    }

    response = client.put(f"/permissions/{permission.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


def test_update_permission_not_found(client, auth_headers):
    update_data = {
        "description": "Updated"
    }

    response = client.put("/permissions/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "Permission not found" in response.json()["detail"]


def test_delete_permission(client, auth_headers, db_session):
    from app.models.permission_model import Permission

    permission_to_delete = Permission(
        name="delete:test",
        resource="test",
        action="delete",
        description="Will be deleted"
    )
    db_session.add(permission_to_delete)
    db_session.commit()
    db_session.refresh(permission_to_delete)

    permission_id = permission_to_delete.id

    response = client.delete(f"/permissions/{permission_id}", headers=auth_headers)

    assert response.status_code == 204

    deleted_permission = db_session.get(Permission, permission_id)
    assert deleted_permission is not None
    assert deleted_permission.is_active is False


def test_delete_permission_not_found(client, auth_headers):
    response = client.delete("/permissions/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Permission not found" in response.json()["detail"]


def test_assign_permission_to_role(client, auth_headers, test_role, db_session):
    from app.models.permission_model import Permission

    new_permission = Permission(
        name="assign:test",
        resource="assign",
        action="test",
        description="For assignment test"
    )
    db_session.add(new_permission)
    db_session.commit()
    db_session.refresh(new_permission)

    response = client.post(
        f"/permissions/{new_permission.id}/assign-to-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "assigned to role" in response.json()["message"]

    db_session.refresh(test_role)
    assert new_permission in test_role.permissions


def test_assign_permission_to_role_permission_not_found(client, auth_headers, test_role):
    response = client.post(
        f"/permissions/9999/assign-to-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Permission not found" in response.json()["detail"]


def test_assign_permission_to_role_role_not_found(client, auth_headers, test_permissions):
    permission = test_permissions[0]
    response = client.post(
        f"/permissions/{permission.id}/assign-to-role/9999",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Role not found" in response.json()["detail"]


def test_assign_permission_already_assigned(client, auth_headers, test_role, test_permissions):
    permission = test_permissions[0]

    response = client.post(
        f"/permissions/{permission.id}/assign-to-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "assigned to role" in response.json()["message"]
