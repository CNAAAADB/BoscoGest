import pytest
from datetime import datetime


def test_login_success(client, test_user, test_membership):
    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }

    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    login_data = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }

    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_user_not_found(client):
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password"
    }

    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_inactive_user(client, db_session):
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    inactive_user = User(
        email="inactive@example.com",
        password_hash=get_password_hash("Password123"),
        name="Inactive",
        surname="User",
        phone="888888888",
        birthdate=datetime(1991, 2, 2).date(),
        dni="99999999Z",
        is_active=False,
        created_at=datetime.utcnow()
    )
    db_session.add(inactive_user)
    db_session.commit()

    login_data = {
        "email": "inactive@example.com",
        "password": "Password123"
    }

    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 401


def test_login_no_membership(client, db_session):
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    user_no_membership = User(
        email="nomembership@example.com",
        password_hash=get_password_hash("Password123"),
        name="No",
        surname="Membership",
        phone="111111111",
        birthdate=datetime(1994, 5, 5).date(),
        dni="00000000A",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user_no_membership)
    db_session.commit()

    login_data = {
        "email": "nomembership@example.com",
        "password": "Password123"
    }

    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 403
    assert "no active memberships" in response.json()["detail"]


def test_check_permission_with_permission(client, auth_headers, test_user, test_role):
    response = client.get(
        "/auth/check-permission?resource=users&action=create",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "has_permission" in data


def test_check_permission_without_permission(client, auth_headers, db_session):
    response = client.get(
        "/auth/check-permission?resource=nonexistent&action=nonexistent",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "has_permission" in data
    assert data["has_permission"] is False


def test_check_permission_unauthorized(client):
    response = client.get("/auth/check-permission?resource=users&action=create")

    assert response.status_code == 401
