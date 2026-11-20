"""Regression tests for deduplication, age boundary and incomplete profiles."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from app.api.v1.member_stats_router import _summarize


def person(id, birthdate):
    return SimpleNamespace(
        id=id, birthdate=birthdate, name="Nombre", surname="Apellido",
        email="socio@example.net", phone="600123123", dni=None,
    )


def test_age_is_strictly_under_thirty():
    today = date(2026, 11, 20)
    users = [person(1, date(1996, 11, 20)), person(2, date(1996, 11, 21))]
    with patch("app.api.v1.member_stats_router.requires_review", return_value=False):
        result = _summarize(users, set(), today)
    assert result["under_30"] == 1


def test_unique_people_are_counted_once_in_totals():
    today = date(2026, 11, 20)
    first = person(1, date(2004, 3, 1))
    with patch("app.api.v1.member_stats_router.requires_review", return_value=True):
        result = _summarize([first, first, person(2, date(1960, 1, 1))], {1}, today)
    assert result == {
        "registered": 2, "under_30": 1,
        "incomplete": 2, "active_30_days": 1,
    }


def test_statistics_is_disabled_by_default(client, test_entity, auth_headers):
    response = client.get(
        f"/member-stats/entity/{test_entity.id}", headers=auth_headers
    )
    assert response.status_code == 403


def test_statistics_for_enabled_entity(client, db_session, test_entity, test_user, test_membership, auth_headers):
    from app.models.entity_view_config_model import EntityViewConfig
    # The fixture's entity defaults to level 1; statistics list only locals.
    test_entity.level = 4
    db_session.add(EntityViewConfig(
        entity_id=test_entity.id, view_name="member_stats",
        display_name="Estadísticas de socios", is_enabled=True,
        display_order=2, icon="insights",
    ))
    db_session.commit()

    response = client.get(
        f"/member-stats/entity/{test_entity.id}", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["totals"]["registered"] == 1
    assert result["associations"][0]["entity_id"] == test_entity.id


def test_statistics_requires_authentication(client, test_entity):
    response = client.get(f"/member-stats/entity/{test_entity.id}")
    assert response.status_code == 401


def test_federation_cannot_read_sibling_federation(
    client, db_session, test_entity, test_role, test_user,
):
    from app.models.entity_model import Entity
    from app.models.user_model import User
    from app.models.membership_model import Membership
    from app.models.entity_view_config_model import EntityViewConfig
    from app.utils.auth import create_access_token

    conf = Entity(name="Demo confederation", level=2, parent_id=test_entity.id)
    db_session.add(conf)
    db_session.flush()
    fed_a = Entity(name="Demo federation A", level=3, parent_id=conf.id)
    fed_b = Entity(name="Demo federation B", level=3, parent_id=conf.id)
    db_session.add_all([fed_a, fed_b])
    db_session.flush()
    local_a = Entity(name="Demo local A", level=4, parent_id=fed_a.id)
    local_b = Entity(name="Demo local B", level=4, parent_id=fed_b.id)
    db_session.add_all([local_a, local_b])
    db_session.flush()

    def member(label, entity_id, role_id):
        user = User(
            email=label + "@example.com", password_hash="not-used",
            name="Persona", surname=label,
            birthdate=date(2000, 1, 1), is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(Membership(
            user_id=user.id, entity_id=entity_id, role_id=role_id,
            is_active=True,
        ))
        return user

    federation_admin = member("federation-admin", fed_a.id, test_role.id)
    other = member("other-local", local_b.id, test_role.id)
    member("our-local", local_a.id, test_role.id)
    for target in (fed_a, fed_b):
        db_session.add(EntityViewConfig(
            entity_id=target.id, view_name="member_stats",
            display_name="Estadísticas de socios", is_enabled=True,
            display_order=2,
        ))
    db_session.commit()
    headers = {"Authorization": "Bearer " + create_access_token(
        {"sub": str(federation_admin.id)}
    )}
    allowed = client.get(f"/member-stats/entity/{fed_a.id}", headers=headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["totals"]["registered"] == 1
    assert [x["entity_id"] for x in allowed.json()["associations"]] == [local_a.id]

    denied = client.get(f"/member-stats/entity/{fed_b.id}", headers=headers)
    assert denied.status_code == 403
