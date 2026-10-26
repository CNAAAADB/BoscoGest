"""Self-service account deletion — DELETE /users/me.

Google Play requires an app with a public sign-up form to offer deletion from
inside the app, and the GDPR requires it of us regardless. The account is kept
as a stripped row rather than dropped: memberships, fees and audit entries
point at it and an association's books still have to add up afterwards.
"""

from datetime import datetime

import pytest

from app.models.membership_model import Membership
from app.models.notification_model import DeviceToken
from app.models.role_model import Role
from app.models.user_model import User
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture
def plain_member(db_session, test_entity):
    """A member whose role carries no manage_all — the ordinary case.

    The fixture user is an admin, and an admin who is the only one left is
    refused deletion, so most of these tests need somebody else.
    """
    user = User(
        email="member@example.com",
        password_hash=get_password_hash("Memberpass1"),
        name="Ordinary",
        surname="Member",
        phone="600999888",
        birthdate=datetime(1995, 3, 2).date(),
        dni="99999999X",
        address="Calle Falsa 123",
        iban="ES1234567890123456789012",
        hobbies="Senderismo",
        job_position="Monitora",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.flush()

    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    membership = Membership(
        user_id=user.id,
        entity_id=test_entity.id,
        role_id=socio_role.id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def plain_member_headers(plain_member, db_session):
    membership = (
        db_session.query(Membership).filter(Membership.user_id == plain_member.id).first()
    )
    token = create_access_token(
        {"sub": str(plain_member.id), "membership_id": membership.id}
    )
    return {"Authorization": f"Bearer {token}"}


def _delete(client, headers, password):
    # httpx's .delete() takes no body, so the request is built by hand.
    return client.request(
        "DELETE", "/users/me", json={"password": password}, headers=headers
    )


def test_requires_authentication(client):
    response = _delete(client, {}, "whatever")
    assert response.status_code == 401


def test_wrong_password_is_rejected(client, plain_member, plain_member_headers, db_session):
    response = _delete(client, plain_member_headers, "not-my-password")

    assert response.status_code == 401
    db_session.refresh(plain_member)
    assert plain_member.is_active is True
    assert plain_member.email == "member@example.com"


def test_deletes_and_anonymises_the_account(
    client, plain_member, plain_member_headers, db_session
):
    user_id = plain_member.id

    response = _delete(client, plain_member_headers, "Memberpass1")

    assert response.status_code == 200
    db_session.expire_all()
    deleted = db_session.query(User).filter(User.id == user_id).first()

    # The row survives — things point at it — but nothing on it identifies
    # anyone any more.
    assert deleted is not None
    assert deleted.is_active is False
    assert deleted.email is None
    assert deleted.phone is None
    assert deleted.address is None
    assert deleted.iban is None
    assert deleted.hobbies is None
    assert deleted.job_position is None
    assert deleted.name == "Cuenta"
    assert deleted.surname == "eliminada"
    # dni is unique and NOT NULL, so it takes a tombstone rather than a null.
    assert deleted.dni == f"DEL-{user_id}"
    assert deleted.birthdate.year == 1900


def test_old_password_no_longer_works(client, plain_member, plain_member_headers):
    _delete(client, plain_member_headers, "Memberpass1")

    response = client.post(
        "/auth/token",
        data={"identifier": "member@example.com", "password": "Memberpass1"},
    )
    assert response.status_code == 401


def test_memberships_are_deactivated(
    client, plain_member, plain_member_headers, db_session
):
    user_id = plain_member.id

    _delete(client, plain_member_headers, "Memberpass1")

    db_session.expire_all()
    memberships = db_session.query(Membership).filter(Membership.user_id == user_id).all()
    assert memberships  # kept, for the entity's records
    assert all(m.is_active is False for m in memberships)


def test_device_tokens_are_purged(
    client, plain_member, plain_member_headers, db_session
):
    """El token identifica el aparato, y ese móvil ya no es de nadie de la
    asociación: seguiría siendo un destinatario válido de notificaciones."""
    user_id = plain_member.id
    db_session.add(
        DeviceToken(user_id=user_id, token="movil-de-la-socia", platform="android")
    )
    db_session.commit()

    _delete(client, plain_member_headers, "Memberpass1")

    db_session.expire_all()
    assert db_session.query(DeviceToken).filter_by(user_id=user_id).count() == 0


def test_session_is_revoked(client, plain_member, plain_member_headers):
    """The token outlives the account unless it is revoked on the way out."""
    _delete(client, plain_member_headers, "Memberpass1")

    response = client.get("/users/me", headers=plain_member_headers)
    assert response.status_code == 401


def test_last_superadmin_cannot_delete_themselves(
    client, auth_headers, test_user, test_membership, db_session
):
    """Otherwise the installation is left with nobody able to administer it."""
    response = _delete(client, auth_headers, "testpassword")

    assert response.status_code == 409
    db_session.refresh(test_user)
    assert test_user.is_active is True


def test_superadmin_can_delete_when_another_one_remains(
    client, auth_headers, test_user, test_membership, test_entity, db_session
):
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    other_admin = User(
        email="otheradmin@example.com",
        password_hash=get_password_hash("Otherpass1"),
        name="Other",
        surname="Admin",
        phone="600111000",
        birthdate=datetime(1988, 7, 7).date(),
        dni="88888888B",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(other_admin)
    db_session.flush()
    db_session.add(
        Membership(
            user_id=other_admin.id,
            entity_id=test_entity.id,
            role_id=admin_role.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    response = _delete(client, auth_headers, "testpassword")

    assert response.status_code == 200
