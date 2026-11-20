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
