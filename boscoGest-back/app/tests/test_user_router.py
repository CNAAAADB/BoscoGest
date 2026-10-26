import pytest
from datetime import date


def test_create_user(client, auth_headers):
    user_data = {
        "email": "newuser@example.com",
        "name": "John",
        "surname": "Doe",
        # Not the fixture user's number: phone is unique as well.
        "phone": "600111222",
        "address": "123 Main St",
        "birthdate": "1990-01-01",
        "dni": "11111111A",
        "photo": None,
        "iban": "ES1234567890123456789012",
        "size": "M",
        "hobbies": "Reading, Swimming, Photography",
        "job_position": "Software Engineer"
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "John"
    assert data["surname"] == "Doe"
    assert data["dni"] == "11111111A"
    assert data["hobbies"] == "Reading, Swimming, Photography"
    assert data["job_position"] == "Software Engineer"
    assert "password" not in data


def test_create_user_without_optional_fields(client, auth_headers):
    """Test creating user without hobbies and job_position (optional fields)"""
    user_data = {
        "email": "minimal@example.com",
        "name": "Minimal",
        "surname": "User",
        "phone": "111111111",
        "birthdate": "1992-05-15",
        "dni": "10101010A"
        # No hobbies ni job_position
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "minimal@example.com"
    assert data["name"] == "Minimal"
    assert data["hobbies"] is None
    assert data["job_position"] is None


def test_create_user_duplicate_email(client, auth_headers, test_user):
    user_data = {
        "email": test_user.email,
        "name": "Jane",
        "surname": "Doe",
        "phone": "987654321",
        "birthdate": "1995-05-05",
        "dni": "22222222B"
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un usuario con ese email"


def test_create_user_duplicate_dni(client, auth_headers, test_user):
    user_data = {
        "email": "different@example.com",
        "name": "Jane",
        "surname": "Doe",
        "phone": "987654321",
        "birthdate": "1995-05-05",
        "dni": test_user.dni
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un usuario con ese DNI"


def test_create_user_unauthorized(client):
    user_data = {
        "email": "unauthorized@example.com",
        "name": "Unauthorized",
        "surname": "User",
        "phone": "555555555",
        "birthdate": "1990-01-01",
        "dni": "99999999Z"
    }

    response = client.post("/users", json=user_data)

    assert response.status_code == 401


def test_get_users(client, auth_headers, test_user):
    response = client.get("/users", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(user["email"] == test_user.email for user in data["items"])


def test_get_users_with_pagination(client, auth_headers):
    response = client.get("/users?skip=0&limit=5", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert len(data["items"]) <= 5


def test_get_users_unauthorized(client):
    response = client.get("/users")

    assert response.status_code == 401


def test_get_user_by_id(client, auth_headers, test_user):
    response = client.get(f"/users/{test_user.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


def test_get_user_not_found(client, auth_headers):
    response = client.get("/users/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_update_user(client, auth_headers, test_user):
    update_data = {
        "name": "Updated",
        "surname": "Name"
    }

    response = client.put(f"/users/{test_user.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["surname"] == "Name"


def test_update_user_email(client, auth_headers, test_user):
    update_data = {
        "email": "newemail@example.com"
    }

    response = client.put(f"/users/{test_user.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newemail@example.com"


def test_update_user_hobbies_and_job_position(client, auth_headers, test_user):
    """Test updating hobbies and job_position fields"""
    update_data = {
        "hobbies": "Cycling, Cooking, Gaming",
        "job_position": "Senior Developer"
    }

    response = client.put(f"/users/{test_user.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["hobbies"] == "Cycling, Cooking, Gaming"
    assert data["job_position"] == "Senior Developer"
    # Verify other fields remain unchanged
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


def test_update_user_partial_new_fields(client, auth_headers, test_user):
    """Test updating only hobbies without job_position"""
    update_data = {
        "hobbies": "Tennis, Music"
    }

    response = client.put(f"/users/{test_user.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["hobbies"] == "Tennis, Music"
    # job_position should remain unchanged (likely None/null)


def test_update_user_not_found(client, auth_headers):
    update_data = {
        "name": "Updated"
    }

    response = client.put("/users/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_update_user_duplicate_email(client, auth_headers, test_user, db_session):
    from app.models.user_model import User
    from app.utils.auth import get_password_hash
    from datetime import datetime

    other_user = User(
        email="other@example.com",
        password_hash=get_password_hash("Password123"),
        name="Other",
        surname="User",
        phone="666666666",
        birthdate=datetime(1992, 3, 3).date(),
        dni="33333333C",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    update_data = {
        "email": test_user.email
    }

    response = client.put(f"/users/{other_user.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un usuario con ese email"


def test_delete_user(client, auth_headers, db_session):
    from app.models.user_model import User
    from app.utils.auth import get_password_hash
    from datetime import datetime

    user_to_delete = User(
        email="delete@example.com",
        password_hash=get_password_hash("Password123"),
        name="Delete",
        surname="Me",
        phone="777777777",
        birthdate=datetime(1993, 4, 4).date(),
        dni="44444444D",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user_to_delete)
    db_session.commit()
    db_session.refresh(user_to_delete)

    user_id = user_to_delete.id

    response = client.delete(f"/users/{user_id}", headers=auth_headers)

    assert response.status_code == 204

    deleted_user = db_session.get(User, user_id)
    assert deleted_user is not None
    assert deleted_user.is_active is False


def test_delete_user_not_found(client, auth_headers):
    response = client.delete("/users/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_delete_user_unauthorized(client, test_user):
    response = client.delete(f"/users/{test_user.id}")

    assert response.status_code == 401


def test_create_user_with_entity_and_role(client, auth_headers, test_entity, test_role):
    """Test creating user with explicit entity_id and role_id creates membership"""
    user_data = {
        "email": "user_with_membership@example.com",
        "name": "Member",
        "surname": "User",
        "phone": "111222333",
        "birthdate": "1992-06-15",
        "dni": "55555555E",
        "entity_id": test_entity.id,
        "role_id": test_role.id
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user_with_membership@example.com"
    assert data["name"] == "Member"


def test_create_user_without_entity_creates_default_membership(client, auth_headers, db_session, test_membership):
    """Test that creating user without entity_id/role_id creates default membership with socio role"""
    from app.models.membership_model import Membership
    from app.models.role_model import Role

    user_data = {
        "email": "default_member@example.com",
        "name": "Default",
        "surname": "Member",
        "phone": "444555666",
        "birthdate": "1993-08-20",
        "dni": "66666666F"
        # No entity_id ni role_id
    }

    response = client.post("/users", json=user_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "default_member@example.com"

    # Verificar que se creó una membresía con rol socio
    user_id = data["id"]
    membership = db_session.query(Membership).filter(
        Membership.user_id == user_id
    ).first()

    assert membership is not None
    assert membership.entity_id == test_membership.entity_id  # Misma entidad que el creador

    # Verificar que el rol es "socio"
    role = db_session.get(Role, membership.role_id)
    assert role.name == "socio"


def test_get_managed_users(client, auth_headers, test_user, db_session):
    """Test GET /users/managed returns users from entities where current user has manage permission"""
    response = client.get("/users/managed", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    # The endpoint returns a page envelope so the client can tell when results
    # have been cut off; it used to return a bare list capped at 100.
    assert set(data) == {"items", "total", "skip", "limit"}
    assert len(data["items"]) >= 1
    assert data["total"] >= 1
    assert any(user["email"] == test_user.email for user in data["items"])


def test_get_managed_users_with_multiple_entities(client, auth_headers, db_session, test_user, test_permissions):
    """Test that managed users includes users from all entities where user has manage permission"""
    from app.models.entity_model import Entity
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.models.user_model import User
    from app.utils.auth import get_password_hash, create_access_token
    from datetime import datetime

    # Crear segunda entidad
    second_entity = Entity(
        name="Second Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(second_entity)
    db_session.flush()

    # Crear usuario en la segunda entidad
    second_user = User(
        email="second@example.com",
        password_hash=get_password_hash("password"),
        name="Second",
        surname="User",
        phone="777888999",
        birthdate=datetime(1994, 5, 10).date(),
        dni="77777777G",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(second_user)
    db_session.flush()

    # Obtener el rol admin
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    # Crear membership del test_user como admin en segunda entidad
    second_membership = Membership(
        user_id=test_user.id,
        entity_id=second_entity.id,
        role_id=admin_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(second_membership)
    db_session.commit()

    # Ahora llamar a /users/managed debería incluir usuarios de ambas entidades
    response = client.get("/users/managed", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    # Debe incluir tanto test_user como second_user
    emails = [user["email"] for user in data["items"]]
    assert test_user.email in emails
    # second_user podría no estar si no tiene membership, pero al menos test_user debe estar


def test_get_managed_users_unauthorized(client):
    """Test that /users/managed requires authentication"""
    response = client.get("/users/managed")

    assert response.status_code == 401


def test_search_user_by_email(client, auth_headers, test_user):
    """Test searching for a user by email address"""
    response = client.get(f"/users/search/email/{test_user.email}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id
    assert data["name"] == test_user.name
    assert data["dni"] == test_user.dni


def test_search_user_by_email_not_found(client, auth_headers):
    """Test searching for a non-existent email returns 404"""
    response = client.get("/users/search/email/nonexistent@example.com", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_user_by_email_inactive_user(client, auth_headers, db_session):
    """Test that searching for an inactive user returns 404"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash
    from datetime import datetime

    inactive_user = User(
        email="inactive@example.com",
        password_hash=get_password_hash("Password123"),
        name="Inactive",
        surname="User",
        phone="888888888",
        birthdate=datetime(1991, 2, 2).date(),
        dni="88888888H",
        is_active=False,
        created_at=datetime.utcnow()
    )
    db_session.add(inactive_user)
    db_session.commit()

    response = client.get("/users/search/email/inactive@example.com", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_user_by_email_unauthorized(client, test_user):
    """Test that searching by email requires authentication"""
    response = client.get(f"/users/search/email/{test_user.email}")

    assert response.status_code == 401


def test_search_user_by_dni(client, auth_headers, test_user):
    """Test searching for a user by DNI"""
    response = client.get(f"/users/search/dni/{test_user.dni}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["dni"] == test_user.dni
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


def test_search_user_by_dni_not_found(client, auth_headers):
    """Test searching for a non-existent DNI returns 404"""
    response = client.get("/users/search/dni/99999999Z", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_user_by_dni_inactive_user(client, auth_headers, db_session):
    """Test that searching for an inactive user by DNI returns 404"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash
    from datetime import datetime

    inactive_user = User(
        email="inactive_dni@example.com",
        password_hash=get_password_hash("Password123"),
        name="Inactive",
        surname="DNI",
        phone="999999999",
        birthdate=datetime(1991, 3, 3).date(),
        dni="00000000I",
        is_active=False,
        created_at=datetime.utcnow()
    )
    db_session.add(inactive_user)
    db_session.commit()

    response = client.get("/users/search/dni/00000000I", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_search_user_by_dni_unauthorized(client, test_user):
    """Test that searching by DNI requires authentication"""
    response = client.get(f"/users/search/dni/{test_user.dni}")

    assert response.status_code == 401
