import pytest
from datetime import datetime, timedelta
from io import BytesIO


def test_create_activity(client, auth_headers, test_entity):
    """Test creating activity with entity_id"""
    activity_data = {
        "title": "Test Activity",
        "description": "A test activity",
        "date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "capacity": 20,
        "price": 10.0,
        "allow_waitlist": True,
        "entity_id": test_entity.id
    }

    response = client.post("/activities/", json=activity_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Activity"
    assert data["entity_id"] == test_entity.id  # Auto-assigned from active membership
    assert data["capacity"] == 20


def test_create_activity_without_active_membership(client, db_session, test_entity):
    """Test that creating activity fails when user has no active membership"""
    from app.models.user_model import User
    from app.utils.auth import get_password_hash, create_access_token

    # Crear usuario sin memberships activos
    user = User(
        email="noactivemembership@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="ActiveMembership",
        phone="333333333",
        birthdate=datetime(1990, 1, 1).date(),
        dni="33333333C",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Crear token sin membership_id
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    activity_data = {
        "title": "Should Fail Activity",
        "description": "Should fail",
        "date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "capacity": 20,
        "price": 10.0,
        "allow_waitlist": True,
        "entity_id": test_entity.id
    }

    response = client.post("/activities/", json=activity_data, headers=headers)

    # Sin membership activo con esa entidad, debe fallar con 403
    assert response.status_code == 403


def test_create_activity_unauthorized(client):
    """Test that creating activity requires authentication"""
    activity_data = {
        "title": "Unauthorized Activity",
        "description": "Should fail",
        "date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "capacity": 20,
        "price": 10.0,
        "allow_waitlist": True
    }

    response = client.post("/activities/", json=activity_data)

    assert response.status_code == 401


def test_list_activities(client, auth_headers, db_session, test_entity, test_user):
    """Test listing activities - should only show activities from user's entities"""
    from app.models.activity_model import Activity
    from app.models.entity_model import Entity

    # Actividad en la entidad del usuario
    activity_in_user_entity = Activity(
        title="User Entity Activity",
        description="In user's entity",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity_in_user_entity)

    # Crear otra entidad donde el usuario NO es miembro
    other_entity = Entity(
        name="Other Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Actividad en entidad donde el usuario NO es miembro
    activity_in_other_entity = Activity(
        title="Other Entity Activity",
        description="Not in user's entity",
        entity_id=other_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity_in_other_entity)
    db_session.commit()

    response = client.get("/activities/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Solo debe aparecer la actividad de la entidad del usuario
    activity_ids = [a["id"] for a in data]
    assert activity_in_user_entity.id in activity_ids
    assert activity_in_other_entity.id not in activity_ids


def test_get_activity(client, db_session, test_entity, test_user):
    from app.models.activity_model import Activity

    activity = Activity(
        title="Get Test Activity",
        description="For getting",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    response = client.get(f"/activities/{activity.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == activity.id
    assert data["title"] == activity.title


def test_get_activity_not_found(client):
    response = client.get("/activities/9999")

    assert response.status_code == 404


def test_update_activity(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity

    activity = Activity(
        title="Update Test Activity",
        description="To be updated",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    update_data = {
        "title": "Updated Activity Title",
        "capacity": 30
    }

    response = client.put(f"/activities/{activity.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Activity Title"
    assert data["capacity"] == 30


def test_update_activity_not_found(client, auth_headers):
    update_data = {
        "title": "Updated"
    }

    response = client.put("/activities/9999", json=update_data, headers=auth_headers)

    assert response.status_code == 404


def test_delete_activity(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity

    activity = Activity(
        title="Delete Test Activity",
        description="To be deleted",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    activity_id = activity.id

    response = client.delete(f"/activities/{activity_id}", headers=auth_headers)

    assert response.status_code == 200

    deleted_activity = db_session.get(Activity, activity_id)
    assert deleted_activity is not None
    assert deleted_activity.is_active is False


def test_delete_activity_not_found(client, auth_headers):
    response = client.delete("/activities/9999", headers=auth_headers)

    assert response.status_code == 404


def test_register_activity(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity

    activity = Activity(
        title="Registration Test Activity",
        description="For registration",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        allow_waitlist=True,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    response = client.post(f"/activities/{activity.id}/register", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["activity_id"] == activity.id
    assert data["user_id"] == test_user.id
    assert data["status"] == "accepted"


def test_register_activity_already_registered(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity
    from app.models.activity_registration_model import ActivityRegistration

    activity = Activity(
        title="Duplicate Registration Test",
        description="For testing duplicate registration",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    registration = ActivityRegistration(
        activity_id=activity.id,
        user_id=test_user.id,
        status="accepted"
    )
    db_session.add(registration)
    db_session.commit()

    response = client.post(f"/activities/{activity.id}/register", headers=auth_headers)

    assert response.status_code == 400
    assert "Ya estás inscrito" in response.json()["detail"]


def test_register_activity_waitlist(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity
    from app.models.activity_registration_model import ActivityRegistration
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    activity = Activity(
        title="Waitlist Test Activity",
        description="For waitlist",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=1,
        price=0.0,
        allow_waitlist=True,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    other_user = User(
        email="other@example.com",
        password_hash=get_password_hash("Password123"),
        name="Other",
        surname="User",
        phone="333333333",
        birthdate=datetime(1996, 7, 7).date(),
        dni="77777777G",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_user)
    db_session.commit()

    registration = ActivityRegistration(
        activity_id=activity.id,
        user_id=other_user.id,
        status="accepted"
    )
    db_session.add(registration)
    db_session.commit()

    response = client.post(f"/activities/{activity.id}/register", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "waitlist"


def test_list_registrations(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity
    from app.models.activity_registration_model import ActivityRegistration

    activity = Activity(
        title="List Registrations Test",
        description="For listing registrations",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    registration = ActivityRegistration(
        activity_id=activity.id,
        user_id=test_user.id,
        status="accepted"
    )
    db_session.add(registration)
    db_session.commit()

    response = client.get(f"/activities/{activity.id}/registrations", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_accept_registration(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity
    from app.models.activity_registration_model import ActivityRegistration
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    activity = Activity(
        title="Accept Registration Test",
        description="For accepting registration",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    other_user = User(
        email="waitlist@example.com",
        password_hash=get_password_hash("Password123"),
        name="Waitlist",
        surname="User",
        phone="444444444",
        birthdate=datetime(1997, 8, 8).date(),
        dni="88888888H",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(other_user)
    db_session.commit()

    registration = ActivityRegistration(
        activity_id=activity.id,
        user_id=other_user.id,
        status="waitlist"
    )
    db_session.add(registration)
    db_session.commit()

    response = client.post(
        f"/activities/{activity.id}/registrations/{other_user.id}/accept",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


def test_reject_registration(client, auth_headers, db_session, test_entity, test_user):
    from app.models.activity_model import Activity
    from app.models.activity_registration_model import ActivityRegistration

    activity = Activity(
        title="Reject Registration Test",
        description="For rejecting registration",
        entity_id=test_entity.id,
        date=datetime.utcnow() + timedelta(days=1),
        capacity=10,
        price=0.0,
        created_by_id=test_user.id
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    registration = ActivityRegistration(
        activity_id=activity.id,
        user_id=test_user.id,
        status="waitlist"
    )
    db_session.add(registration)
    db_session.commit()

    response = client.post(
        f"/activities/{activity.id}/registrations/{test_user.id}/reject",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
