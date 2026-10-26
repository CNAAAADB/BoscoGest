"""Signing up from the app: POST /auth/register."""

import pytest


@pytest.fixture
def datos(test_entity):
    return {
        "name": "Clara",
        "surname": "Prueba",
        "email": "clara@ejemplo.com",
        "password": "Prueba-2026",
        "phone": "611000301",
        "birthdate": "1950-01-15",
        "dni": "30000001A",
        "address": "Calle Mayor 1",
        "entity_id": test_entity.id,
    }


def test_a_new_person_can_sign_up(client, datos):
    r = client.post("/auth/register", json=datos)

    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "pending"


@pytest.mark.parametrize(
    "campo, cambios, etiqueta",
    [
        ("email", {"phone": "611999999", "dni": "39999999Z"}, "email"),
        ("dni", {"email": "otra@ejemplo.com", "phone": "611999999"}, "DNI"),
        ("phone", {"email": "otra@ejemplo.com", "dni": "39999999Z"}, "teléfono"),
    ],
)
def test_a_repeated_value_says_which_one_instead_of_failing(
    client, datos, campo, cambios, etiqueta
):
    """A repeated DNI or phone used to reach the INSERT and come back as a 500."""
    assert client.post("/auth/register", json=datos).status_code == 201

    r = client.post("/auth/register", json={**datos, **cambios})

    assert r.status_code == 409, r.json()
    assert f"Ya existe una cuenta con ese {etiqueta}" in r.json()["detail"]
    assert "inicia sesión" in r.json()["detail"]


def test_the_same_dni_in_lower_case_is_the_same_dni(client, datos):
    assert client.post("/auth/register", json=datos).status_code == 201

    r = client.post(
        "/auth/register",
        json={**datos, "email": "otra@ejemplo.com", "phone": "611999999", "dni": "30000001a"},
    )

    assert r.status_code == 409
    assert "DNI" in r.json()["detail"]


def test_someone_already_added_by_an_administrator_is_told_to_sign_in(
    client, datos, test_user
):
    """The likely case: imported in bulk, then tries to sign up on their own."""
    r = client.post(
        "/auth/register",
        json={**datos, "email": "nueva@ejemplo.com", "phone": "611999999", "dni": test_user.dni},
    )

    assert r.status_code == 409
    assert "inicia sesión" in r.json()["detail"]


def test_nothing_is_left_behind_when_it_is_refused(client, db_session, datos):
    from app.models.membership_request_model import MembershipRequest
    from app.models.user_model import User

    client.post("/auth/register", json=datos)
    usuarios = db_session.query(User).count()
    solicitudes = db_session.query(MembershipRequest).count()

    client.post("/auth/register", json={**datos, "email": "otra@ejemplo.com"})

    assert db_session.query(User).count() == usuarios
    assert db_session.query(MembershipRequest).count() == solicitudes


def test_a_birthdate_that_is_not_a_date_is_a_clear_error(client, datos):
    r = client.post("/auth/register", json={**datos, "birthdate": ""})

    assert r.status_code == 422
    assert "fecha de nacimiento" in r.json()["detail"]
