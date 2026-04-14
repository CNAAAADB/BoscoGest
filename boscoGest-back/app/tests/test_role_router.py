import pytest


def test_create_role(client, auth_headers):
    role_data = {
        "name": "test_role",
        "description": "A test role"
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_role"
    assert data["description"] == "A test role"
    assert "id" in data


def test_create_role_duplicate_name(client, auth_headers, test_role):
    # Los roles son globales con nombres únicos
    role_data = {
        "name": test_role.name,
        "description": "Duplicate role"
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    # No debe permitirse crear roles con el mismo nombre (son únicos globalmente)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_role_unauthorized(client):
    role_data = {
        "name": "unauthorized_role",
        "description": "Should not be created"
    }

    response = client.post("/roles/", json=role_data)

    assert response.status_code == 401


def test_get_roles(client, auth_headers, test_role):
    response = client.get("/roles/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(role["name"] == test_role.name for role in data)


def test_get_roles_with_pagination(client, auth_headers):
    response = client.get("/roles/?skip=0&limit=5", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_roles_unauthorized(client):
    response = client.get("/roles/")

    assert response.status_code == 401


def test_get_role_by_id(client, auth_headers, test_role):
    response = client.get(f"/roles/{test_role.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_role.id
    assert data["name"] == test_role.name
    assert data["description"] == test_role.description
    # Verify that permissions field is present (even if empty)
    assert "permissions" in data
    assert isinstance(data["permissions"], list)


def test_get_role_not_found(client, auth_headers):
    response = client.get("/roles/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Role not found" in response.json()["detail"]


def test_get_role_with_permissions(client, auth_headers, db_session, test_permissions):
    """Test that get_role endpoint returns role with its associated permissions"""
    from app.models.role_model import Role
    from app.models.permission_model import Permission
    from sqlalchemy import select

    # Get some permissions to assign
    stmt = select(Permission).where(Permission.name.in_(["users:read", "users:update", "users:delete"]))
    result = db_session.execute(stmt)
    permissions = result.scalars().all()

    # Create a role with permissions
    role = Role(name="test_role_with_perms_get", description="Role with permissions for GET test")
    role.permissions.extend(permissions)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    # Get the role via API
    response = client.get(f"/roles/{role.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == role.id
    assert data["name"] == role.name
    assert "permissions" in data
    assert len(data["permissions"]) == 3

    # Verify permission details
    returned_perm_names = {p["name"] for p in data["permissions"]}
    expected_perm_names = {"users:read", "users:update", "users:delete"}
    assert returned_perm_names == expected_perm_names

    # Verify permission structure
    for perm in data["permissions"]:
        assert "id" in perm
        assert "name" in perm
        assert "resource" in perm
        assert "action" in perm


def test_update_role(client, auth_headers, test_role):
    original_name = test_role.name
    update_data = {
        "name": "updated_role_name",  # This should be ignored
        "description": "Updated description"
    }

    response = client.put(f"/roles/{test_role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == original_name  # Name should not change (hardcoded in app)
    assert data["description"] == "Updated description"


def test_update_role_not_found(client, auth_headers):
    update_data = {
        "name": "updated_role"
    }

    response = client.put("/roles/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "Role not found" in response.json()["detail"]


def test_update_role_duplicate_name(client, auth_headers, test_role, db_session):
    """Test that name cannot be changed (it's ignored in updates)"""
    from app.models.role_model import Role

    other_role = Role(
        name="other_role",
        description="Another role"
    )
    db_session.add(other_role)
    db_session.commit()
    db_session.refresh(other_role)

    update_data = {
        "name": test_role.name,  # This should be ignored
        "description": "Updated description"
    }

    response = client.put(f"/roles/{other_role.id}", json=update_data, headers=auth_headers)

    # Name changes are ignored, so this should succeed
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "other_role"  # Name should remain unchanged
    assert data["description"] == "Updated description"


def test_delete_role(client, auth_headers, db_session):
    from app.models.role_model import Role

    role_to_delete = Role(
        name="role_to_delete",
        description="Will be deleted"
    )
    db_session.add(role_to_delete)
    db_session.commit()
    db_session.refresh(role_to_delete)

    role_id = role_to_delete.id

    response = client.delete(f"/roles/{role_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify soft delete: role exists but is_active is False
    deleted_role = db_session.get(Role, role_id)
    assert deleted_role is not None
    assert deleted_role.is_active == False


def test_delete_role_not_found(client, auth_headers):
    response = client.delete("/roles/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Role not found" in response.json()["detail"]


def test_delete_role_unauthorized(client, test_role):
    response = client.delete(f"/roles/{test_role.id}")

    assert response.status_code == 401


def test_create_role_associates_with_current_membership_entity(client, auth_headers, test_membership, db_session):
    """Test that a newly created role is automatically associated with the entity of the user's current membership"""
    from app.models.role_model import Role
    from app.models.relationships import entity_roles
    from sqlalchemy import select

    role_data = {
        "name": "new_entity_role",
        "description": "Should be associated with current membership entity"
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    role_id = data["id"]

    # Verify the role exists
    role = db_session.get(Role, role_id)
    assert role is not None
    assert role.name == "new_entity_role"

    # Verify the role is associated with the entity through entity_roles
    stmt = select(entity_roles).where(
        entity_roles.c.role_id == role_id,
        entity_roles.c.entity_id == test_membership.entity_id
    )
    result = db_session.execute(stmt).first()
    assert result is not None, "Role should be associated with the current membership's entity"


def test_get_roles_returns_only_roles_from_current_entity(client, auth_headers, test_membership, db_session):
    """Test that get_roles only returns roles associated with the current membership's entity"""
    from app.models.role_model import Role
    from app.models.entity_model import Entity
    from datetime import datetime

    # Create another entity
    other_entity = Entity(
        name="Other Organization",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create a role and associate it with the other entity (not the current membership's entity)
    other_role = Role(
        name="other_entity_role",
        description="Role for other entity"
    )
    db_session.add(other_role)
    db_session.flush()
    other_entity.roles.append(other_role)
    db_session.commit()

    # Get roles with current membership context
    response = client.get("/roles/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify that the other_role is NOT in the response
    role_names = [role["name"] for role in data]
    assert "other_entity_role" not in role_names, "Should not return roles from other entities"

    # Verify that roles from current entity ARE in the response
    assert any(role["name"] == "admin" for role in data), "Should return roles from current entity"


def test_create_multiple_roles_all_associate_with_entity(client, auth_headers, test_membership, db_session):
    """Test that multiple roles created by the same user all get associated with the current entity"""
    from app.models.relationships import entity_roles
    from sqlalchemy import select

    role_names = ["role_one", "role_two", "role_three"]
    created_role_ids = []

    # Create multiple roles
    for name in role_names:
        role_data = {
            "name": name,
            "description": f"Test role {name}"
        }
        response = client.post("/roles/", json=role_data, headers=auth_headers)
        assert response.status_code == 201
        created_role_ids.append(response.json()["id"])

    # Verify all roles are associated with the current entity
    for role_id in created_role_ids:
        stmt = select(entity_roles).where(
            entity_roles.c.role_id == role_id,
            entity_roles.c.entity_id == test_membership.entity_id
        )
        result = db_session.execute(stmt).first()
        assert result is not None, f"Role {role_id} should be associated with entity {test_membership.entity_id}"


def test_delete_role_associated_with_current_entity(client, auth_headers, test_membership, db_session):
    """Test that a role associated only with current entity can be deleted (soft delete)"""
    from app.models.role_model import Role

    # Create a role via API (will be associated with current entity)
    role_data = {
        "name": "deletable_role",
        "description": "Can be deleted"
    }
    response = client.post("/roles/", json=role_data, headers=auth_headers)
    assert response.status_code == 201
    role_id = response.json()["id"]

    # Delete the role
    response = client.delete(f"/roles/{role_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify soft delete: role exists but is_active is False
    deleted_role = db_session.get(Role, role_id)
    assert deleted_role is not None
    assert deleted_role.is_active == False


def test_delete_role_associated_with_multiple_entities(client, auth_headers, test_membership, db_session):
    """Test that a role associated with multiple entities cannot be deleted"""
    from app.models.role_model import Role
    from app.models.entity_model import Entity
    from datetime import datetime

    # Create another entity
    other_entity = Entity(
        name="Another Organization",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create a role and associate it with both current entity and other entity
    multi_entity_role = Role(
        name="multi_entity_role",
        description="Associated with multiple entities"
    )
    db_session.add(multi_entity_role)
    db_session.flush()

    # Get current entity and associate role with both entities
    from app.models.entity_model import Entity
    current_entity = db_session.get(Entity, test_membership.entity_id)
    current_entity.roles.append(multi_entity_role)
    other_entity.roles.append(multi_entity_role)
    db_session.commit()
    db_session.refresh(multi_entity_role)

    # Attempt to delete the role
    response = client.delete(f"/roles/{multi_entity_role.id}", headers=auth_headers)

    assert response.status_code == 403
    assert "associated with other entities or multiple entities" in response.json()["detail"]

    # Verify role still exists
    role = db_session.get(Role, multi_entity_role.id)
    assert role is not None


def test_delete_role_associated_with_different_entity(client, auth_headers, test_membership, db_session):
    """Test that a role associated with a different entity cannot be deleted"""
    from app.models.role_model import Role
    from app.models.entity_model import Entity
    from datetime import datetime

    # Create another entity
    other_entity = Entity(
        name="Different Organization",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create a role and associate it only with the other entity
    other_entity_role = Role(
        name="other_entity_only_role",
        description="Associated with different entity"
    )
    db_session.add(other_entity_role)
    db_session.flush()
    other_entity.roles.append(other_entity_role)
    db_session.commit()
    db_session.refresh(other_entity_role)

    # Attempt to delete the role
    response = client.delete(f"/roles/{other_entity_role.id}", headers=auth_headers)

    assert response.status_code == 403
    assert "associated with other entities or multiple entities" in response.json()["detail"]

    # Verify role still exists
    role = db_session.get(Role, other_entity_role.id)
    assert role is not None


def test_create_role_with_permissions(client, auth_headers, db_session, test_permissions):
    """Test creating a role with permissions assigned at creation time"""
    from app.models.permission_model import Permission
    from sqlalchemy import select

    # Use existing permissions from fixture
    stmt = select(Permission).where(Permission.name.in_(["users:read", "users:update"]))
    result = db_session.execute(stmt)
    permissions = result.scalars().all()

    permission1, permission2 = permissions[0], permissions[1]

    # Create role with permissions
    role_data = {
        "name": "test_role_with_perms",
        "description": "A test role with permissions",
        "permission_ids": [permission1.id, permission2.id]
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_role_with_perms"
    assert data["description"] == "A test role with permissions"
    assert "id" in data

    # Verify permissions were assigned
    from app.models.role_model import Role
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select

    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == data["id"])
    result = db_session.execute(stmt)
    role = result.scalars().first()

    assert role is not None
    assert len(role.permissions) == 2
    permission_ids = {perm.id for perm in role.permissions}
    assert permission1.id in permission_ids
    assert permission2.id in permission_ids


def test_create_role_without_permissions(client, auth_headers):
    """Test creating a role without permissions (backward compatibility)"""
    role_data = {
        "name": "test_role_no_perms",
        "description": "A test role without permissions"
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_role_no_perms"
    assert data["description"] == "A test role without permissions"
    assert "id" in data


def test_create_role_with_empty_permission_list(client, auth_headers):
    """Test creating a role with an empty permission list"""
    role_data = {
        "name": "test_role_empty_perms",
        "description": "A test role with empty permission list",
        "permission_ids": []
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_role_empty_perms"


def test_create_role_with_invalid_permission_ids(client, auth_headers):
    """Test creating a role with non-existent permission IDs"""
    role_data = {
        "name": "test_role_invalid_perms",
        "description": "Should fail due to invalid permissions",
        "permission_ids": [9999, 8888]
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 404
    assert "permission IDs not found" in response.json()["detail"]


def test_create_role_with_partial_invalid_permission_ids(client, auth_headers, db_session, test_permissions):
    """Test creating a role with mix of valid and invalid permission IDs"""
    from app.models.permission_model import Permission
    from sqlalchemy import select

    # Use existing permission from fixture
    stmt = select(Permission).where(Permission.name == "entities:read")
    result = db_session.execute(stmt)
    valid_permission = result.scalars().first()

    # Try to create role with one valid and one invalid permission ID
    role_data = {
        "name": "test_role_partial_invalid",
        "description": "Should fail due to one invalid permission",
        "permission_ids": [valid_permission.id, 9999]
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    assert response.status_code == 404
    assert "permission IDs not found" in response.json()["detail"]

    # Verify role was not created (transaction rolled back)
    from app.models.role_model import Role
    from sqlalchemy import select

    stmt = select(Role).where(Role.name == "test_role_partial_invalid")
    result = db_session.execute(stmt)
    role = result.scalars().first()
    assert role is None


def test_create_role_with_duplicate_permission_ids(client, auth_headers, db_session, test_permissions):
    """Test creating a role with duplicate permission IDs in the list"""
    from app.models.permission_model import Permission
    from sqlalchemy import select

    # Use existing permission from fixture
    stmt = select(Permission).where(Permission.name == "roles:create")
    result = db_session.execute(stmt)
    permission = result.scalars().first()

    # Create role with duplicate permission IDs
    role_data = {
        "name": "test_role_duplicate_perms",
        "description": "Role with duplicate permission IDs",
        "permission_ids": [permission.id, permission.id, permission.id]
    }

    response = client.post("/roles/", json=role_data, headers=auth_headers)

    # Should succeed - SQLAlchemy handles duplicates gracefully
    assert response.status_code == 201
    data = response.json()

    # Verify only one instance of the permission is assigned
    from app.models.role_model import Role
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select

    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == data["id"])
    result = db_session.execute(stmt)
    role = result.scalars().first()

    assert role is not None
    # Permission should appear only once despite duplicates in request
    assert len(role.permissions) == 1
    assert role.permissions[0].id == permission.id


def test_update_role_with_permissions(client, auth_headers, db_session, test_permissions):
    """Test updating a role and adding permissions"""
    from app.models.role_model import Role
    from app.models.permission_model import Permission
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    # Create a role without permissions
    role = Role(name="test_role_for_update", description="Will be updated")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    # Get some permissions to assign
    stmt = select(Permission).where(Permission.name.in_(["users:create", "users:delete"]))
    result = db_session.execute(stmt)
    permissions = result.scalars().all()
    perm_ids = [p.id for p in permissions]

    # Update the role with permissions
    update_data = {
        "description": "Updated with permissions",
        "permission_ids": perm_ids
    }

    response = client.put(f"/roles/{role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated with permissions"

    # Verify permissions were assigned
    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == role.id)
    result = db_session.execute(stmt)
    updated_role = result.scalars().first()

    assert len(updated_role.permissions) == 2
    assigned_perm_ids = {p.id for p in updated_role.permissions}
    assert assigned_perm_ids == set(perm_ids)


def test_update_role_replace_permissions(client, auth_headers, db_session, test_permissions):
    """Test updating a role and replacing existing permissions with new ones"""
    from app.models.role_model import Role
    from app.models.permission_model import Permission
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    # Create a role with initial permissions
    stmt = select(Permission).where(Permission.name.in_(["users:read", "users:update"]))
    result = db_session.execute(stmt)
    initial_permissions = result.scalars().all()

    role = Role(name="test_role_replace_perms", description="Has initial permissions")
    role.permissions.extend(initial_permissions)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    initial_perm_count = len(role.permissions)
    assert initial_perm_count == 2

    # Get different permissions to replace with
    stmt = select(Permission).where(Permission.name.in_(["entities:create", "entities:update", "entities:delete"]))
    result = db_session.execute(stmt)
    new_permissions = result.scalars().all()
    new_perm_ids = [p.id for p in new_permissions]

    # Update the role with new permissions (should replace old ones)
    update_data = {
        "permission_ids": new_perm_ids
    }

    response = client.put(f"/roles/{role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200

    # Verify old permissions were replaced with new ones
    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == role.id)
    result = db_session.execute(stmt)
    updated_role = result.scalars().first()

    assert len(updated_role.permissions) == 3
    assigned_perm_ids = {p.id for p in updated_role.permissions}
    assert assigned_perm_ids == set(new_perm_ids)


def test_update_role_clear_permissions(client, auth_headers, db_session, test_permissions):
    """Test updating a role and clearing all permissions with empty list"""
    from app.models.role_model import Role
    from app.models.permission_model import Permission
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    # Create a role with permissions
    stmt = select(Permission).where(Permission.name.in_(["roles:read", "roles:update"]))
    result = db_session.execute(stmt)
    initial_permissions = result.scalars().all()

    role = Role(name="test_role_clear_perms", description="Has permissions to clear")
    role.permissions.extend(initial_permissions)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    assert len(role.permissions) == 2

    # Update with empty permission list (should clear all)
    update_data = {
        "permission_ids": []
    }

    response = client.put(f"/roles/{role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200

    # Verify all permissions were cleared
    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == role.id)
    result = db_session.execute(stmt)
    updated_role = result.scalars().first()

    assert len(updated_role.permissions) == 0


def test_update_role_without_permission_ids_keeps_existing(client, auth_headers, db_session, test_permissions):
    """Test updating a role without providing permission_ids keeps existing permissions"""
    from app.models.role_model import Role
    from app.models.permission_model import Permission
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    # Create a role with permissions
    stmt = select(Permission).where(Permission.name.in_(["memberships:read", "memberships:create"]))
    result = db_session.execute(stmt)
    initial_permissions = result.scalars().all()

    role = Role(name="test_role_keep_perms", description="Initial description")
    role.permissions.extend(initial_permissions)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    initial_perm_ids = {p.id for p in role.permissions}
    assert len(initial_perm_ids) == 2

    # Update only description, do NOT provide permission_ids
    update_data = {
        "description": "Updated description only"
    }

    response = client.put(f"/roles/{role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description only"

    # Verify permissions were kept unchanged
    stmt = select(Role).options(joinedload(Role.permissions)).where(Role.id == role.id)
    result = db_session.execute(stmt)
    updated_role = result.scalars().first()

    assert len(updated_role.permissions) == 2
    kept_perm_ids = {p.id for p in updated_role.permissions}
    assert kept_perm_ids == initial_perm_ids


def test_update_role_with_invalid_permission_ids(client, auth_headers, test_role, db_session):
    """Test updating a role with invalid permission IDs"""
    update_data = {
        "description": "Should fail",
        "permission_ids": [9999, 8888]
    }

    response = client.put(f"/roles/{test_role.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "permission IDs not found" in response.json()["detail"]

    # Verify role was not modified (transaction rolled back)
    from app.models.role_model import Role
    role = db_session.get(Role, test_role.id)
    assert role.description == test_role.description  # Original description unchanged
