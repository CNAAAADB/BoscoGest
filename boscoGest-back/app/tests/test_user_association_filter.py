"""Association selectors must exclude federations and preserve user scope."""
from datetime import datetime

from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.role_model import Role


def _local_entities(db, parent):
    confederation = Entity(
        name="Confederacion filtro", level=2, parent_id=parent.id,
        created_at=datetime.utcnow(),
    )
    db.add(confederation)
    db.flush()
    federation = Entity(
        name="Federacion filtro", level=3, parent_id=confederation.id,
        created_at=datetime.utcnow(),
    )
    db.add(federation)
    db.flush()
    a = Entity(name="Asociacion local Uno", level=4, parent_id=federation.id, created_at=datetime.utcnow())
    b = Entity(name="Asociacion local Dos", level=4, parent_id=federation.id, created_at=datetime.utcnow())
    db.add_all([a, b])
    db.flush()
    return confederation, federation, a, b


def test_local_association_directory_excludes_higher_levels(
    client, auth_headers, db_session, test_entity,
):
    higher, federation, a, b = _local_entities(db_session, test_entity)
    db_session.commit()
    response = client.get("/entities/associations", headers=auth_headers)
    assert response.status_code == 200
    ids = {x["id"] for x in response.json()}
    assert {a.id, b.id} <= ids
    assert higher.id not in ids
    assert federation.id not in ids
    assert test_entity.id not in ids


def test_managed_users_can_combine_local_association_and_review_filter(
    client, auth_headers, db_session, test_entity, test_user,
):
    from app.models.user_model import User
    from app.utils.auth import get_password_hash
    from datetime import date

    _, federation, a, b = _local_entities(db_session, test_entity)
    socio = db_session.query(Role).filter_by(name="socio").first()
    for n, association in enumerate((a, b), start=1):
        member = User(
            email=None, phone=None, dni=None,
            password_hash=get_password_hash("unused"),
            name=f"MiembroFiltro{n}", surname="Visible",
            birthdate=date(1965, 1, 1), is_active=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(member)
        db_session.flush()
        db_session.add(Membership(
            user_id=member.id, entity_id=association.id,
            role_id=socio.id, is_active=True, created_at=datetime.utcnow(),
        ))
    db_session.commit()

    first = client.get(
        f"/users/managed?entity_id={a.id}&review_only=true",
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    assert [u["name"] for u in first.json()["items"]] == ["MiembroFiltro1"]
    assert first.json()["total"] == 1

    second = client.get(
        f"/users?entity_id={b.id}&search=MiembroFiltro",
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert [u["name"] for u in second.json()["items"]] == ["MiembroFiltro2"]

    forbidden_parent = client.get(
        f"/users/managed?entity_id={federation.id}", headers=auth_headers,
    )
    assert forbidden_parent.status_code == 403


def test_unauthorized_local_association_is_rejected(
    client, auth_headers, db_session, test_entity,
):
    other = Entity(
        name="Asociacion fuera del alcance", level=4,
        parent_id=None, created_at=datetime.utcnow(),
    )
    db_session.add(other)
    db_session.commit()
    assert client.get(
        f"/users/managed?entity_id={other.id}", headers=auth_headers,
    ).status_code == 403


def test_expired_membership_does_not_appear_in_association(
    client, auth_headers, db_session, test_entity,
):
    from datetime import date
    from app.models.user_model import User
    from app.utils.auth import get_password_hash

    _, _, local, _ = _local_entities(db_session, test_entity)
    socio = db_session.query(Role).filter_by(name="socio").first()
    former = User(
        email=None, phone=None, dni=None,
        password_hash=get_password_hash("unused"),
        name="AntiguoSocio", surname="Fuera",
        birthdate=date(1960, 1, 1), is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(former)
    db_session.flush()
    db_session.add(Membership(
        user_id=former.id, entity_id=local.id, role_id=socio.id,
        is_active=False, created_at=datetime.utcnow(),
    ))
    db_session.commit()

    result = client.get(
        f"/users/managed?entity_id={local.id}&search=AntiguoSocio",
        headers=auth_headers,
    )
    assert result.status_code == 200, result.text
    assert result.json()["items"] == []
    assert result.json()["total"] == 0
