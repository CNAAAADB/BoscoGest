import pytest


def test_create_group(client, auth_headers):
    group_data = {
        "name": "Test Group",
        "description": "A test group"
    }

    response = client.post("/groups/", json=group_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Group"
    assert data["description"] == "A test group"
    assert "id" in data


def test_create_group_duplicate_name(client, auth_headers, db_session):
    from app.models.group_model import Group

    existing_group = Group(name="Existing Group", description="Already exists")
    db_session.add(existing_group)
    db_session.commit()

    group_data = {
        "name": "Existing Group",
        "description": "Duplicate"
    }

    response = client.post("/groups/", json=group_data, headers=auth_headers)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_group_unauthorized(client):
    group_data = {
        "name": "Unauthorized Group"
    }

    response = client.post("/groups/", json=group_data)

    assert response.status_code == 401


def test_get_groups(client, auth_headers, db_session):
    from app.models.group_model import Group

    group = Group(name="List Group", description="For listing")
    db_session.add(group)
    db_session.commit()

    response = client.get("/groups/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_groups_with_pagination(client, auth_headers):
    response = client.get("/groups/?skip=0&limit=5", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_groups_unauthorized(client):
    response = client.get("/groups/")

    assert response.status_code == 401


def test_get_group_by_id(client, auth_headers, db_session):
    from app.models.group_model import Group

    group = Group(name="Get Group", description="For getting")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.get(f"/groups/{group.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group.id
    assert data["name"] == group.name


def test_get_group_not_found(client, auth_headers):
    response = client.get("/groups/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Group not found" in response.json()["detail"]


def test_update_group(client, auth_headers, db_session):
    from app.models.group_model import Group

    group = Group(name="Update Group", description="To be updated")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    update_data = {
        "name": "Updated Group Name",
        "description": "Updated description"
    }

    response = client.put(f"/groups/{group.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Group Name"
    assert data["description"] == "Updated description"


def test_update_group_not_found(client, auth_headers):
    update_data = {
        "name": "Updated"
    }

    response = client.put("/groups/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "Group not found" in response.json()["detail"]


def test_delete_group(client, auth_headers, db_session):
    from app.models.group_model import Group

    group_to_delete = Group(name="Delete Group", description="Will be deleted")
    db_session.add(group_to_delete)
    db_session.commit()
    db_session.refresh(group_to_delete)

    group_id = group_to_delete.id

    response = client.delete(f"/groups/{group_id}", headers=auth_headers)

    assert response.status_code == 204

    deleted_group = db_session.get(Group, group_id)
    assert deleted_group is not None
    assert deleted_group.is_active is False


def test_delete_group_not_found(client, auth_headers):
    response = client.delete("/groups/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Group not found" in response.json()["detail"]


def test_add_user_to_group(client, auth_headers, test_user, db_session):
    from app.models.group_model import Group

    group = Group(name="User Group", description="For user assignment")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/add-user/{test_user.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "added to group" in response.json()["message"]

    db_session.refresh(group)
    assert test_user in group.users


def test_add_user_to_group_group_not_found(client, auth_headers, test_user):
    response = client.post(
        f"/groups/9999/add-user/{test_user.id}",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Group not found" in response.json()["detail"]


def test_add_user_to_group_user_not_found(client, auth_headers, db_session):
    from app.models.group_model import Group

    group = Group(name="User Group", description="For user assignment")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/add-user/9999",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_remove_user_from_group(client, auth_headers, test_user, db_session):
    from app.models.group_model import Group

    group = Group(name="User Group", description="For user removal")
    db_session.add(group)
    db_session.flush()

    group.users.append(test_user)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/remove-user/{test_user.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "removed from group" in response.json()["message"]

    db_session.refresh(group)
    assert test_user not in group.users


def test_assign_role_to_group(client, auth_headers, test_role, db_session):
    from app.models.group_model import Group

    group = Group(name="Role Group", description="For role assignment")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/assign-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "assigned to group" in response.json()["message"]

    db_session.refresh(group)
    assert test_role in group.roles


def test_assign_role_to_group_group_not_found(client, auth_headers, test_role):
    response = client.post(
        f"/groups/9999/assign-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Group not found" in response.json()["detail"]


def test_assign_role_to_group_role_not_found(client, auth_headers, db_session):
    from app.models.group_model import Group

    group = Group(name="Role Group", description="For role assignment")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/assign-role/9999",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Role not found" in response.json()["detail"]


def test_remove_role_from_group(client, auth_headers, test_role, db_session):
    from app.models.group_model import Group

    group = Group(name="Role Group", description="For role removal")
    db_session.add(group)
    db_session.flush()

    group.roles.append(test_role)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/groups/{group.id}/remove-role/{test_role.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "removed from group" in response.json()["message"]

    db_session.refresh(group)
    assert test_role not in group.roles
