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
