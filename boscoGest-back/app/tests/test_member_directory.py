"""Member directory and administrator management scope regression tests."""
from datetime import date, datetime
from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.role_model import Role
from app.models.user_model import User
from app.utils.auth import get_password_hash


def test_directory_only_exposes_names_and_requires_login(
    client, auth_headers, db_session, test_entity,
):
    assert client.get("/users/directory").status_code == 401
    confed = Entity(name="Directory Confed", level=2, parent_id=test_entity.id)
    db_session.add(confed)
    db_session.flush()
    federation = Entity(name="Directory Fed", level=3, parent_id=confed.id)
    db_session.add(federation)
    db_session.flush()
    a = Entity(name="Directory Local A", level=4, parent_id=federation.id)
    b = Entity(name="Directory Local B", level=4, parent_id=federation.id)
    db_session.add_all([a, b])
    db_session.flush()
    socio = db_session.query(Role).filter_by(name="socio").one()
    for i, association in enumerate((a, b)):
        user = User(
            name=f"DirectoryUser{i}", surname="Visible", email=f"directory{i}@example.org",
            phone=f"6223344{i}0", dni=f"0000000{i}A",
            birthdate=date(1965, 1, 1), password_hash=get_password_hash("unused"),
            is_active=True, created_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(Membership(
            user_id=user.id, entity_id=association.id, role_id=socio.id,
            is_active=True, created_at=datetime.utcnow(),
        ))
    db_session.commit()

    response = client.get("/users/directory?search=DirectoryUser", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    for item in response.json()["items"]:
        assert set(item) == {"id", "name", "surname"}
        assert "email" not in item and "dni" not in item

    filtered = client.get(
        f"/users/directory?search=DirectoryUser&entity_id={a.id}",
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["name"] == "DirectoryUser0"

    parent = client.get(
        f"/users/directory?entity_id={federation.id}", headers=auth_headers,
    )
    assert parent.status_code == 400
