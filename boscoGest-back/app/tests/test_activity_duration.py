"""Activities that last: a start and, optionally, an end."""

from datetime import datetime, timedelta


def _datos(entity_id, inicio, fin=None):
    datos = {
        "title": "Campamento",
        "description": "Tres días en la sierra",
        "date": inicio.isoformat(),
        "capacity": 20,
        "price": 0.0,
        "allow_waitlist": False,
        "entity_id": entity_id,
    }
    if fin is not None:
        datos["end_date"] = fin.isoformat()
    return datos


def _actividad(db_session, test_entity, test_user, inicio, fin=None):
    from app.models.activity_model import Activity

    actividad = Activity(
        title="Campamento",
        description="Tres días en la sierra",
        entity_id=test_entity.id,
        date=inicio,
        end_date=fin,
        capacity=10,
        price=0.0,
        created_by_id=test_user.id,
    )
    db_session.add(actividad)
    db_session.commit()
    db_session.refresh(actividad)
    return actividad


INICIO = datetime(2026, 11, 13, 17, 0)


def test_an_activity_can_span_several_days(client, auth_headers, test_entity):
    fin = INICIO + timedelta(days=2, hours=1)
    r = client.post("/activities", json=_datos(test_entity.id, INICIO, fin), headers=auth_headers)

    assert r.status_code == 200, r.json()
    assert r.json()["end_date"].startswith("2026-11-15T18:00")


def test_the_end_is_optional(client, auth_headers, test_entity):
    """A one-off meeting, and every activity created before this existed."""
    r = client.post("/activities", json=_datos(test_entity.id, INICIO), headers=auth_headers)

    assert r.status_code == 200, r.json()
    assert r.json()["end_date"] is None


def test_an_end_before_the_start_is_rejected(client, auth_headers, test_entity):
    r = client.post(
        "/activities",
        json=_datos(test_entity.id, INICIO, INICIO - timedelta(hours=1)),
        headers=auth_headers,
    )

    assert r.status_code == 422
    assert "terminar después de empezar" in str(r.json())


def test_an_end_equal_to_the_start_is_rejected(client, auth_headers, test_entity):
    r = client.post("/activities", json=_datos(test_entity.id, INICIO, INICIO), headers=auth_headers)

    assert r.status_code == 422


def test_an_end_can_be_added_to_an_existing_activity(
    client, auth_headers, db_session, test_entity, test_user
):
    actividad = _actividad(db_session, test_entity, test_user, INICIO)

    r = client.put(
        f"/activities/{actividad.id}",
        json={"end_date": (INICIO + timedelta(days=2)).isoformat()},
        headers=auth_headers,
    )

    assert r.status_code == 200, r.json()
    assert r.json()["end_date"].startswith("2026-11-15")


def test_moving_the_start_past_the_stored_end_is_rejected(
    client, auth_headers, db_session, test_entity, test_user
):
    """Only the start changes, so the check has to look at the end already saved."""
    actividad = _actividad(
        db_session, test_entity, test_user, INICIO, INICIO + timedelta(days=2)
    )

    r = client.put(
        f"/activities/{actividad.id}",
        json={"date": (INICIO + timedelta(days=3)).isoformat()},
        headers=auth_headers,
    )

    assert r.status_code == 422
    db_session.refresh(actividad)
    assert actividad.date == INICIO


def test_an_end_given_with_a_zone_compares_with_a_stored_start_without_one(
    client, auth_headers, db_session, test_entity, test_user
):
    """The app sends UTC with "Z"; what the database hands back has no zone."""
    actividad = _actividad(db_session, test_entity, test_user, INICIO)

    r = client.put(
        f"/activities/{actividad.id}",
        json={"end_date": "2026-11-15T18:00:00.000Z"},
        headers=auth_headers,
    )

    assert r.status_code == 200, r.json()


def test_the_end_can_be_removed(
    client, auth_headers, db_session, test_entity, test_user
):
    actividad = _actividad(
        db_session, test_entity, test_user, INICIO, INICIO + timedelta(days=2)
    )

    r = client.put(f"/activities/{actividad.id}", json={"end_date": None}, headers=auth_headers)

    assert r.status_code == 200, r.json()
    assert r.json()["end_date"] is None


def test_times_go_out_marked_as_utc(client, auth_headers, test_entity):
    """Without the offset the browser read them as local time: an hour early in
    Spain in winter, two in summer."""
    r = client.post(
        "/activities",
        json={**_datos(test_entity.id, INICIO), "date": "2026-11-13T16:00:00.000Z",
              "end_date": "2026-11-15T17:00:00.000Z"},
        headers=auth_headers,
    )

    d = r.json()
    assert d["date"] == "2026-11-13T16:00:00+00:00"
    assert d["end_date"] == "2026-11-15T17:00:00+00:00"
    assert d["created_at"].endswith("+00:00")


def test_times_with_another_offset_are_stored_in_utc(
    client, auth_headers, db_session, test_entity
):
    """17:00 in Madrid is 16:00 UTC, whatever zone the database session uses."""
    from app.models.activity_model import Activity

    r = client.post(
        "/activities",
        json={**_datos(test_entity.id, INICIO), "date": "2026-11-13T17:00:00+01:00"},
        headers=auth_headers,
    )

    guardada = db_session.get(Activity, r.json()["id"])
    assert guardada.date == datetime(2026, 11, 13, 16, 0)


def test_saving_an_activity_unchanged_does_not_move_it(
    client, auth_headers, db_session, test_entity, test_user
):
    """What the app reads is what it sends back on save. It used to come back an
    hour earlier each time."""
    actividad = _actividad(
        db_session, test_entity, test_user, INICIO, INICIO + timedelta(days=2)
    )
    leida = client.get(f"/activities/{actividad.id}", headers=auth_headers).json()

    r = client.put(
        f"/activities/{actividad.id}",
        json={"date": leida["date"], "end_date": leida["end_date"]},
        headers=auth_headers,
    )

    assert r.json()["date"] == leida["date"]
    db_session.refresh(actividad)
    assert actividad.date == INICIO
