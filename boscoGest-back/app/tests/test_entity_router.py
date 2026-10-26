import pytest
from datetime import datetime


def test_get_entities(client, auth_headers, test_entity, test_membership):
    """Test that GET /entities returns only entities where user has membership"""
    response = client.get("/entities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Verificar que la entidad del test está en la lista
    assert any(entity["id"] == test_entity.id for entity in data)


def test_get_entities_unauthorized(client):
    """Test that GET /entities requires authentication"""
    response = client.get("/entities")

    assert response.status_code == 401


def test_get_entity_by_id(client, auth_headers, test_entity):
    """Test getting a specific entity by ID"""
    response = client.get(f"/entities/{test_entity.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_entity.id
    assert data["name"] == test_entity.name


def test_get_entity_not_found(client, auth_headers):
    """Test getting a non-existent entity"""
    response = client.get("/entities/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Entity not found" in response.json()["detail"]


def test_get_entity_no_access(client, db_session, test_entity):
    """Test that user without manage_all cannot access entity they are not member of"""
    from app.models.entity_model import Entity
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token

    # Create a separate entity
    other_entity = Entity(
        name="Other Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create user with socio role (no manage_all) in test_entity only
    user = User(
        email="noaccess_entity@example.com",
        password_hash=get_password_hash("password"),
        name="No", surname="Access", phone="999999999",
        birthdate=datetime(1990, 1, 1).date(), dni="99999999Z",
        is_active=True, created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.flush()

    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    membership = Membership(
        user_id=user.id, entity_id=test_entity.id, role_id=socio_role.id,
        is_active=True, created_at=datetime.utcnow()
    )
    db_session.add(membership)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "membership_id": membership.id})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/entities/{other_entity.id}", headers=headers)

    assert response.status_code == 403


def test_get_entities_empty_for_user_without_memberships(client, db_session):
    """Test that users without active memberships get 403 Forbidden"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash, create_access_token

    # Crear usuario sin memberships
    user = User(
        email="nomembership@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="Membership",
        phone="111111111",
        birthdate=datetime(1990, 1, 1).date(),
        dni="11111111A",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Crear token sin membership_id (usuario sin memberships activos)
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/entities", headers=headers)

    # Sin membership activo, el require_permission devuelve 403
    assert response.status_code == 403


def test_create_entity(client, auth_headers, db_session, test_permissions, test_entity):
    """Test creating a child entity based on user's current membership"""
    entity_data = {
        "name": "Child Organization",
        "parent_id": test_entity.id
    }

    response = client.post("/entities", json=entity_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Child Organization"
    assert data["level"] == 2  # parent is level 1, so child is level 2
    assert data["parent_id"] == test_entity.id
    assert "id" in data


def test_create_entity_without_active_membership(client, db_session):
    """Test that creating entity fails when user has no active membership"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash, create_access_token

    # Crear usuario sin memberships activos
    user = User(
        email="noactive@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="Active",
        phone="222222222",
        birthdate=datetime(1990, 1, 1).date(),
        dni="22222222B",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Crear token sin membership_id
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    entity_data = {
        "name": "Should Fail",
        "parent_id": 1  # dummy parent_id — permission check happens before entity validation
    }

    response = client.post("/entities", json=entity_data, headers=headers)

    # Without active membership, check_entity_permission returns 403
    assert response.status_code in (400, 403)  # 400 if parent not found, 403 if permission denied


def test_create_entity_creates_admin_and_socio_roles(client, auth_headers, db_session, test_permissions, test_entity):
    """Test that entity creation associates global admin and socio roles"""
    from app.models.role_model import Role
    from app.models.entity_model import Entity

    entity_data = {
        "name": "Test Child Org",
        "parent_id": test_entity.id
    }

    response = client.post("/entities", json=entity_data, headers=auth_headers)

    assert response.status_code == 201
    entity_id = response.json()["id"]

    # Verificar que existen roles globales admin y socio
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    socio_role = db_session.query(Role).filter(Role.name == "socio").first()

    assert admin_role is not None
    assert socio_role is not None
    assert admin_role.description == "Administrator role with full permissions"
    assert socio_role.description == "Member role with read-only permissions"
    assert len(admin_role.permissions) > 0
    assert len(socio_role.permissions) > 0
    assert len(admin_role.permissions) > len(socio_role.permissions)

    # Verificar que los roles están asociados a la entidad creada
    entity = db_session.query(Entity).filter(Entity.id == entity_id).first()
    assert admin_role in entity.roles
    assert socio_role in entity.roles


def test_create_entity_unauthorized(client):
    """Test that creating entity requires authentication"""
    entity_data = {
        "name": "Unauthorized Entity"
    }

    response = client.post("/entities", json=entity_data)

    assert response.status_code == 401


def test_update_entity(client, auth_headers, test_entity):
    update_data = {
        "name": "Updated Organization"
    }

    response = client.put(f"/entities/{test_entity.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Organization"
    assert data["id"] == test_entity.id


def test_update_entity_not_found(client, auth_headers):
    update_data = {
        "name": "Updated Organization"
    }

    response = client.put("/entities/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "Entity not found" in response.json()["detail"]


def test_update_entity_invalid_parent(client, auth_headers, test_entity):
    """Test that parent_id cannot be updated (it's ignored in updates)"""
    update_data = {
        "parent_id": 9999,  # Este campo será ignorado por EntityUpdate
        "name": "Updated Name"
    }

    response = client.put(f"/entities/{test_entity.id}", json=update_data, headers=auth_headers)

    # El update debe ser exitoso porque parent_id es ignorado
    assert response.status_code == 200
    data = response.json()
    # Verificar que el parent_id no cambió
    assert data["parent_id"] == test_entity.parent_id
    # Pero el name sí se actualizó
    assert data["name"] == "Updated Name"


def test_delete_entity(client, auth_headers, db_session, test_entity):
    """Test deleting an entity"""
    from app.models.entity_model import Entity

    # Crear una entidad hija para eliminar
    child_entity = Entity(
        name="Entity to Delete",
        level=2,
        parent_id=test_entity.id,
        created_at=datetime.utcnow()
    )
    db_session.add(child_entity)
    db_session.commit()
    db_session.refresh(child_entity)

    response = client.delete(f"/entities/{child_entity.id}", headers=auth_headers)

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verificar que la entidad fue eliminada
    deleted_entity = db_session.get(Entity, child_entity.id)
    assert deleted_entity is not None
    assert deleted_entity.is_active is False


def test_delete_entity_not_found(client, auth_headers):
    """Test deleting a non-existent entity"""
    response = client.delete("/entities/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Entity not found" in response.json()["detail"]


def test_delete_entity_unauthorized(client):
    """Test that deleting entity requires authentication"""
    response = client.delete("/entities/1")

    assert response.status_code == 401


def test_get_admin_entities(client, auth_headers, test_entity, test_membership):
    """Test GET /entities/admin returns entities where user is admin or superadmin"""
    response = client.get("/entities/admin", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should include test_entity where user has admin role
    assert len(data) >= 1
    assert any(entity["id"] == test_entity.id for entity in data)


def test_get_admin_entities_only_admin_superadmin(client, db_session, test_entity, test_permissions):
    """Test that /entities/admin only returns entities where user has admin or superadmin role"""
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear usuario con rol socio (no admin)
    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    socio_user = User(
        email="socio@example.com",
        password_hash=get_password_hash("password"),
        name="Socio",
        surname="User",
        phone="123123123",
        birthdate=datetime(1990, 1, 1).date(),
        dni="12312312A",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(socio_user)
    db_session.flush()

    # Crear membership con rol socio
    socio_membership = Membership(
        user_id=socio_user.id,
        entity_id=test_entity.id,
        role_id=socio_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(socio_membership)
    db_session.commit()

    # Crear token para socio user
    token = create_access_token({
        "sub": str(socio_user.id),
        "membership_id": socio_membership.id
    })
    socio_headers = {"Authorization": f"Bearer {token}"}

    # Llamar a /entities/admin como socio debería devolver lista vacía
    response = client.get("/entities/admin", headers=socio_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0  # Socio no tiene entidades admin


def test_get_membership_manageable_entities(client, auth_headers, test_entity):
    """Test GET /entities/membership-manageable returns entities where user can manage memberships"""
    response = client.get("/entities/membership-manageable", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should include test_entity where user has manage memberships permission
    assert len(data) >= 1
    assert any(entity["id"] == test_entity.id for entity in data)


def test_get_membership_manageable_entities_requires_permission(client, db_session, test_entity, test_permissions):
    """Test that /entities/membership-manageable only returns entities with manage permission"""
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear rol sin permiso de manage memberships
    limited_role = Role(
        name="limited",
        description="Limited role without membership management",
        is_active=True
    )
    db_session.add(limited_role)
    db_session.flush()

    # Solo añadir permisos de lectura
    read_permissions = [p for p in test_permissions if p.action in ["read", "list"]]
    limited_role.permissions.extend(read_permissions)
    db_session.commit()

    # Crear usuario con rol limitado
    limited_user = User(
        email="limited@example.com",
        password_hash=get_password_hash("password"),
        name="Limited",
        surname="User",
        phone="456456456",
        birthdate=datetime(1991, 2, 2).date(),
        dni="45645645B",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(limited_user)
    db_session.flush()

    # Asociar rol limitado a la entidad
    test_entity.roles.append(limited_role)
    db_session.commit()

    # Crear membership con rol limitado
    limited_membership = Membership(
        user_id=limited_user.id,
        entity_id=test_entity.id,
        role_id=limited_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(limited_membership)
    db_session.commit()

    # Crear token para limited user
    token = create_access_token({
        "sub": str(limited_user.id),
        "membership_id": limited_membership.id
    })
    limited_headers = {"Authorization": f"Bearer {token}"}

    # Llamar a /entities/membership-manageable como usuario limitado debería devolver 403
    response = client.get("/entities/membership-manageable", headers=limited_headers)

    # Sin permiso de manage memberships, el endpoint devuelve 403 Forbidden
    assert response.status_code == 403


def test_get_entity_roles(client, auth_headers, test_entity, test_role):
    """Test GET /entities/{id}/roles returns roles for the entity"""
    response = client.get(f"/entities/{test_entity.id}/roles", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Should include admin and socio roles
    role_names = [role["name"] for role in data]
    assert "admin" in role_names
    assert "socio" in role_names


def test_get_entity_roles_filters_superadmin_for_admin(client, db_session, test_entity, test_permissions):
    """Test that admin users don't see superadmin role in entity roles"""
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear rol superadmin
    superadmin_role = db_session.query(Role).filter(Role.name == "superadmin").first()
    if not superadmin_role:
        superadmin_role = Role(
            name="superadmin",
            description="Super administrator role",
            is_active=True
        )
        db_session.add(superadmin_role)
        db_session.flush()
        superadmin_role.permissions.extend(test_permissions)
        db_session.commit()

    # Asociar superadmin role a test_entity
    if superadmin_role not in test_entity.roles:
        test_entity.roles.append(superadmin_role)
        db_session.commit()

    # Crear usuario con rol admin (no superadmin)
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    admin_user = User(
        email="admin@example.com",
        password_hash=get_password_hash("password"),
        name="Admin",
        surname="User",
        phone="789789789",
        birthdate=datetime(1992, 3, 3).date(),
        dni="78978978C",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(admin_user)
    db_session.flush()

    # Crear membership con rol admin
    admin_membership = Membership(
        user_id=admin_user.id,
        entity_id=test_entity.id,
        role_id=admin_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(admin_membership)
    db_session.commit()

    # Crear token para admin user
    token = create_access_token({
        "sub": str(admin_user.id),
        "membership_id": admin_membership.id
    })
    admin_headers = {"Authorization": f"Bearer {token}"}

    # Llamar a /entities/{id}/roles como admin
    response = client.get(f"/entities/{test_entity.id}/roles", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    role_names = [role["name"] for role in data]
    # Admin debería ver admin y socio, pero NO superadmin
    assert "admin" in role_names
    assert "socio" in role_names
    assert "superadmin" not in role_names


def test_get_entity_roles_superadmin_sees_all(client, db_session, test_entity, test_permissions):
    """Test that superadmin users see all roles including superadmin role"""
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear rol superadmin si no existe
    superadmin_role = db_session.query(Role).filter(Role.name == "superadmin").first()
    if not superadmin_role:
        superadmin_role = Role(
            name="superadmin",
            description="Super administrator role",
            is_active=True
        )
        db_session.add(superadmin_role)
        db_session.flush()
        superadmin_role.permissions.extend(test_permissions)
        db_session.commit()

    # Asociar superadmin role a test_entity
    if superadmin_role not in test_entity.roles:
        test_entity.roles.append(superadmin_role)
        db_session.commit()

    # Crear usuario con rol superadmin
    superadmin_user = User(
        email="superadmin@example.com",
        password_hash=get_password_hash("password"),
        name="Super",
        surname="Admin",
        phone="321321321",
        birthdate=datetime(1988, 4, 4).date(),
        dni="32132132D",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(superadmin_user)
    db_session.flush()

    # Crear membership con rol superadmin
    superadmin_membership = Membership(
        user_id=superadmin_user.id,
        entity_id=test_entity.id,
        role_id=superadmin_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(superadmin_membership)
    db_session.commit()

    # Crear token para superadmin user
    token = create_access_token({
        "sub": str(superadmin_user.id),
        "membership_id": superadmin_membership.id
    })
    superadmin_headers = {"Authorization": f"Bearer {token}"}

    # Llamar a /entities/{id}/roles como superadmin
    response = client.get(f"/entities/{test_entity.id}/roles", headers=superadmin_headers)

    assert response.status_code == 200
    data = response.json()
    role_names = [role["name"] for role in data]
    # Superadmin debería ver TODOS los roles incluyendo superadmin
    assert "admin" in role_names
    assert "socio" in role_names
    assert "superadmin" in role_names


def test_get_entity_roles_requires_membership(client, db_session, test_entity):
    """Test that getting entity roles requires membership in that entity"""
    from app.models.entity_model import Entity
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear entidad donde el usuario no es miembro
    other_entity = Entity(
        name="Other Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create user with socio role (no manage_all) in test_entity only
    user = User(
        email="noaccess_roles@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="Access",
        phone="777777777",
        birthdate=datetime(1990, 1, 1).date(),
        dni="77777777G",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.flush()

    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    membership = Membership(
        user_id=user.id,
        entity_id=test_entity.id,
        role_id=socio_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(membership)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "membership_id": membership.id})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/entities/{other_entity.id}/roles", headers=headers)

    assert response.status_code == 403


def test_delete_entity_ends_its_memberships(
    client, auth_headers, db_session, test_entity, test_user, test_role
):
    """Deleting an association ends the memberships inside it.

    They used to stay active, leaving members belonging to something that no
    longer existed and still showing up in listings.
    """
    from app.models.entity_model import Entity
    from app.models.membership_model import Membership

    doomed = Entity(
        name="Asociación con socios",
        level=2,
        parent_id=test_entity.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(doomed)
    db_session.commit()
    db_session.refresh(doomed)

    membership = Membership(
        user_id=test_user.id,
        entity_id=doomed.id,
        role_id=test_role.id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)

    response = client.delete(f"/entities/{doomed.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["memberships_ended"] == 1

    db_session.refresh(membership)
    assert membership.is_active is False


def test_delete_entity_refuses_when_it_has_children(
    client, auth_headers, db_session, test_entity
):
    """An association with associations under it cannot be removed.

    They would stay active with a deleted parent, still inheriting permissions
    through it.
    """
    from app.models.entity_model import Entity

    parent = Entity(
        name="Federación con hijas",
        level=2,
        parent_id=test_entity.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(parent)
    db_session.commit()
    db_session.refresh(parent)

    child = Entity(
        name="Asociación hija",
        level=3,
        parent_id=parent.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(child)
    db_session.commit()

    response = client.delete(f"/entities/{parent.id}", headers=auth_headers)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Asociación hija" in detail

    db_session.refresh(parent)
    assert parent.is_active is True


def test_deletion_impact_reports_what_would_be_affected(
    client, auth_headers, db_session, test_entity, test_user, test_role
):
    """The interface asks first so it can warn before deleting, not after."""
    from app.models.entity_model import Entity
    from app.models.membership_model import Membership

    target = Entity(
        name="Asociación a consultar",
        level=2,
        parent_id=test_entity.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    db_session.add(
        Membership(
            user_id=test_user.id,
            entity_id=target.id,
            role_id=test_role.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    response = client.get(
        f"/entities/{target.id}/deletion-impact", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["can_delete"] is True
    assert data["member_count"] == 1
    assert data["child_count"] == 0

    child = Entity(
        name="Hija sobrevenida",
        level=3,
        parent_id=target.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(child)
    db_session.commit()

    response = client.get(
        f"/entities/{target.id}/deletion-impact", headers=auth_headers
    )
    data = response.json()
    assert data["can_delete"] is False
    assert data["child_count"] == 1
    assert data["child_names"] == ["Hija sobrevenida"]
