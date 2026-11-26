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

    response = client.post("/activities", json=activity_data, headers=auth_headers)

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
    token = create_access_token({"sub": str(user.id)})
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

    response = client.post("/activities", json=activity_data, headers=headers)

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

    response = client.post("/activities", json=activity_data)

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

    response = client.get("/activities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Solo debe aparecer la actividad de la entidad del usuario
    activity_ids = [a["id"] for a in data]
    assert activity_in_user_entity.id in activity_ids
    assert activity_in_other_entity.id not in activity_ids


def test_get_activity(client, auth_headers, db_session, test_entity, test_user):
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

    assert client.get(f"/activities/{activity.id}").status_code == 401
    response = client.get(f"/activities/{activity.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == activity.id
    assert data["title"] == activity.title


def test_get_activity_not_found(client, auth_headers):
    response = client.get("/activities/9999", headers=auth_headers)

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


@pytest.mark.parametrize(
    "allowed, guests, capacity, waitlist, expected",
    [
        (False, 1, 3, True, 400),
        (True, -1, 3, False, 422),
        (True, 1.5, 3, False, 422),
        (True, 2, 3, False, "accepted"),
        (True, 2, 2, False, 400),
        (True, 2, 2, True, "waitlist"),
    ],
)
def test_register_with_guests(client, auth_headers, test_entity, allowed, guests, capacity, waitlist, expected):
    activity = client.post("/activities", headers=auth_headers, json={
        "title": "Visita", "description": "Visita en grupo", "date": datetime.utcnow().isoformat(),
        "capacity": capacity, "price": 0, "allow_waitlist": waitlist,
        "allow_guests": allowed, "entity_id": test_entity.id,
    }).json()
    url = f"/activities/{activity['id']}"
    result = client.post(f"{url}/register", headers=auth_headers, json={"guest_count": guests})
    if isinstance(expected, int):
        assert result.status_code == expected
        assert client.get(f"{url}/my-registration", headers=auth_headers).json() is None
        return
    assert result.status_code == 200
    assert result.json()["status"] == expected
    assert client.get(f"{url}/my-registration", headers=auth_headers).json()["guest_count"] == guests
    registration = client.get(f"{url}/registrations", headers=auth_headers).json()[0]
    assert registration["guest_count"] == guests
    if waitlist:
        accept = client.post(f"{url}/registrations/{registration['user_id']}/accept", headers=auth_headers)
        assert accept.status_code == 400


def test_activity_admin_permissions_are_scoped_to_the_organizing_entity(
    client, auth_headers, db_session, test_entity, test_user, test_role
):
    from app.models.activity_model import Activity
    from app.models.entity_model import Entity
    from app.models.membership_model import Membership
    from app.models.permission_model import Permission
    from app.models.role_model import Role
    from app.models.user_model import User
    from app.utils.auth import create_access_token, get_password_hash

    db = db_session
    socio = db.query(Role).filter_by(name="socio").one()

    def entity(name, level, parent):
        row = Entity(name=name, level=level, parent_id=parent.id)
        db.add(row)
        db.flush()
        return row

    conf = entity("Confederación", 2, test_entity)
    fed = entity("Federación", 3, conf)
    atocha = entity("Atocha", 4, fed)
    other = entity("Otra asociación", 4, fed)
    other_fed = entity("Otra federación", 3, conf)
    outside = entity("Fuera de la federación", 4, other_fed)

    def actor(n, admin_at, parents):
        user = User(
            email=f"activity-scope-{n}@example.com",
            password_hash=get_password_hash("password"),
            name=f"Admin {n}", surname="Prueba",
            phone=f"60000000{n}", dni=f"1000000{n}X",
            birthdate=datetime(1990, 1, 1).date(), is_active=True,
        )
        db.add(user)
        db.flush()
        member = Membership(user_id=user.id, entity_id=admin_at.id,
                            role_id=test_role.id, is_active=True)
        db.add(member)
        for parent in parents:
            db.add(Membership(user_id=user.id, entity_id=parent.id,
                              role_id=socio.id, is_active=True))
        db.flush()
        token = create_access_token({"sub": str(user.id), "membership_id": member.id})
        return user, member, {"Authorization": f"Bearer {token}"}

    local_user, local_membership, local_headers = actor(1, atocha, [fed, conf, test_entity])
    _, _, federal_headers = actor(2, fed, [conf, test_entity])
    _, _, confederal_headers = actor(3, conf, [test_entity])
    # Unscoped direct grants must not turn a local appointment into a global one.
    local_user.direct_permissions.append(db.query(Permission).filter_by(
        resource="activities", action="update"
    ).one())

    def activity(owner, name):
        row = Activity(title=name, description="Test", entity_id=owner.id,
                       date=datetime.utcnow() + timedelta(days=1), capacity=20,
                       price=0, created_by_id=test_user.id)
        db.add(row)
        db.flush()
        return row

    national = activity(conf, "Actividad confederal")
    local = activity(atocha, "Actividad Atocha")
    sibling = activity(other, "Actividad otra asociación")
    unrelated = activity(outside, "Actividad otra federación")
    db.commit()
    national_url = f"/activities/{national.id}"
    local_url = f"/activities/{local.id}"

    assert client.get(national_url).status_code == 401
    detail = client.get(national_url, headers=local_headers)
    assert detail.status_code == 200
    assert detail.json()["permissions"] == {
        "can_edit": False, "can_delete": False, "can_manage_registrations": False,
        "can_create_chat_group": False, "can_register": True,
    }
    assert client.put(national_url, json={"title": "No autorizado"}, headers=local_headers).status_code == 403
    assert client.delete(national_url, headers=local_headers).status_code == 403
    assert client.get(f"{national_url}/registrations", headers=local_headers).status_code == 403
    assert client.post(f"{national_url}/chat-group", headers=local_headers).status_code == 403
    assert client.post(f"{national_url}/upload-image", headers=local_headers,
                       files={"file": ("test.png", BytesIO(b"test"), "image/png")}).status_code == 403
    assert client.post(f"{national_url}/register", headers=local_headers).status_code == 200
    for action in ("accept", "reject"):
        assert client.post(f"{national_url}/registrations/{local_user.id}/{action}",
                           headers=local_headers).status_code == 403

    assert client.get(f"/activities/{sibling.id}", headers=local_headers).status_code == 404
    assert client.put(f"/activities/{sibling.id}", json={"title": "No"}, headers=local_headers).status_code == 403
    assert client.get(local_url, headers=local_headers).json()["permissions"]["can_edit"] is True
    assert client.put(local_url, json={"title": "Editada en Atocha"}, headers=local_headers).status_code == 200

    assert client.put(local_url, json={"title": "Editada desde federación"}, headers=federal_headers).status_code == 200
    assert client.get(f"/activities/{unrelated.id}", headers=federal_headers).status_code == 404
    assert client.put(national_url, json={"title": "No"}, headers=federal_headers).status_code == 403
    assert client.put(national_url, json={"title": "Editada desde Confederación"}, headers=confederal_headers).status_code == 200
    assert client.put(local_url, json={"title": "Editada desde raíz"}, headers=auth_headers).status_code == 200

    create_entities = client.get("/activities/entities-with-permissions", headers=local_headers).json()
    assert {row["id"] for row in create_entities} == {atocha.id}

    local_membership.is_active = False
    db.commit()
    assert client.get(local_url, headers=local_headers).status_code == 404
    assert client.post(f"{local_url}/register", headers=local_headers).status_code == 403
    assert client.put(local_url, json={"title": "No"}, headers=local_headers).status_code == 403
    assert local.id not in {row["id"] for row in client.get("/activities", headers=local_headers).json()}
