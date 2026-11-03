"""Choosing a new password through a link, for someone who forgot theirs."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import importlib

import pytest

from app.models.activation_token_model import ActivationToken
from app.services import activation_service, email_service

# The module, not the router: app.api.v1 re-exports a router of the same name.
auth_router = importlib.import_module("app.api.v1.auth_router")

NEW = "NuevaClave123"


@pytest.fixture
def sent(monkeypatch):
    """The emails the endpoint would send, as (address, name, url)."""
    calls = []
    monkeypatch.setattr(
        auth_router, "send_password_reset_email", lambda *a: calls.append(a)
    )
    return calls


def _forgot(client, identifier):
    return client.post("/auth/password/forgot", json={"identifier": identifier})


def _reset(client, token, password=NEW, confirm=None):
    return client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": password,
              "confirm_password": confirm or password},
    )


def _token_from(url):
    return url.split("token=", 1)[1]


def _login(client, password):
    return client.post("/auth/token", data={"identifier": "test@example.com",
                                            "password": password})


# ── Asking for the link ──────────────────────────────────────────────────────

def test_asking_sends_a_link_to_the_account_email(client, test_user, sent):
    r = _forgot(client, test_user.email)

    assert r.status_code == 202
    assert len(sent) == 1
    address, name, url = sent[0]
    assert address == test_user.email
    assert name == "Test User"
    assert "/restablecer?token=" in url


def test_the_phone_or_a_capitalised_email_also_find_the_account(client, test_user, sent, db_session):
    _forgot(client, test_user.phone)
    db_session.query(ActivationToken).update({"created_at": datetime.utcnow() - timedelta(hours=1)})
    db_session.commit()
    _forgot(client, "TEST@Example.com")

    assert [s[0] for s in sent] == [test_user.email, test_user.email]


def test_the_answer_is_the_same_for_an_unknown_address(client, test_user, sent):
    """Otherwise the form would tell anyone whether an address is a member."""
    known = _forgot(client, test_user.email)
    unknown = _forgot(client, "nadie@ejemplo.com")

    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(sent) == 1


def test_the_answer_says_what_to_do_without_email(client):
    assert "teléfono" in _forgot(client, "600000000").json()["message"]


def test_nothing_is_sent_to_a_deactivated_account(client, db_session, test_user, sent):
    test_user.is_active = False
    db_session.commit()

    _forgot(client, test_user.email)

    assert sent == []


def test_asking_again_straight_away_sends_nothing_new(client, test_user, sent):
    """The form is public; it must not be a way to flood someone's inbox."""
    _forgot(client, test_user.email)
    _forgot(client, test_user.email)

    assert len(sent) == 1


def test_after_the_pause_a_new_link_replaces_the_old(client, db_session, test_user, sent):
    _forgot(client, test_user.email)
    db_session.query(ActivationToken).update({"created_at": datetime.utcnow() - timedelta(minutes=3)})
    db_session.commit()
    _forgot(client, test_user.email)

    assert len(sent) == 2
    old, new = (_token_from(s[2]) for s in sent)
    assert _reset(client, old).json()["detail"]["reason"] == "used"
    assert _reset(client, new).status_code == 200


def test_the_link_lasts_two_hours(client, db_session, test_user, sent):
    _forgot(client, test_user.email)
    token = db_session.query(ActivationToken).filter_by(user_id=test_user.id).one()

    assert token.purpose == "reset"
    remaining = token.expires_at - datetime.utcnow()
    assert timedelta(hours=1, minutes=59) < remaining <= timedelta(hours=2)


# ── Using it ─────────────────────────────────────────────────────────────────

def test_the_link_sets_the_new_password_and_signs_in(client, test_user, sent):
    _forgot(client, test_user.email)

    r = _reset(client, _token_from(sent[0][2]))

    assert r.status_code == 200
    assert r.json()["access_token"]
    assert _login(client, NEW).status_code == 200
    assert _login(client, "testpassword").status_code != 200


def test_the_link_works_only_once(client, test_user, sent):
    _forgot(client, test_user.email)
    token = _token_from(sent[0][2])
    _reset(client, token)

    again = _reset(client, token, password="OtraClave456")

    assert again.status_code == 410
    assert again.json()["detail"]["reason"] == "used"
    assert _login(client, NEW).status_code == 200


def test_an_expired_link_is_refused_and_changes_nothing(client, db_session, test_user, sent):
    _forgot(client, test_user.email)
    db_session.query(ActivationToken).update({"expires_at": datetime.utcnow() - timedelta(minutes=1)})
    db_session.commit()

    r = _reset(client, _token_from(sent[0][2]))

    assert r.status_code == 410
    assert r.json()["detail"]["reason"] == "expired"
    assert "2 horas" in r.json()["detail"]["message"]
    assert _login(client, "testpassword").status_code == 200


def test_a_weak_password_is_refused_without_spending_the_link(client, test_user, sent):
    _forgot(client, test_user.email)
    token = _token_from(sent[0][2])

    weak = _reset(client, token, password="corta")
    mismatch = _reset(client, token, password=NEW, confirm="OtraClave456")

    assert weak.status_code == 422
    assert mismatch.status_code == 422
    assert _reset(client, token).status_code == 200


def test_a_made_up_token_is_refused(client):
    r = _reset(client, "x" * 43)

    assert r.status_code == 400
    assert r.json()["detail"]["reason"] == "invalid"


def test_a_welcome_link_is_not_taken_on_the_reset_screen(client, db_session, test_user):
    raw = activation_service.issue_token(db_session, test_user)

    assert _reset(client, raw).json()["detail"]["reason"] == "invalid"


def test_a_reset_link_does_not_sign_in_without_a_new_password(client, test_user, sent):
    """Otherwise the link alone would be a way in, password unchanged."""
    _forgot(client, test_user.email)

    r = client.post("/auth/activate", json={"token": _token_from(sent[0][2])})

    assert r.status_code == 400
    assert r.json()["detail"]["reason"] == "invalid"


def test_it_also_works_for_someone_who_never_chose_a_password(client, db_session, test_user, sent):
    """And then they are no longer asked to choose one on entering."""
    test_user.must_change_password = True
    db_session.commit()
    _forgot(client, test_user.email)

    _reset(client, _token_from(sent[0][2]))

    db_session.refresh(test_user)
    assert test_user.must_change_password is False


def test_resetting_burns_the_welcome_links_too(client, db_session, test_user, sent):
    welcome = activation_service.issue_token(db_session, test_user)
    _forgot(client, test_user.email)

    _reset(client, _token_from(sent[0][2]))

    assert client.post("/auth/activate", json={"token": welcome}).status_code == 410


def test_changing_the_password_normally_burns_a_pending_reset_link(
    client, test_user, sent, auth_headers
):
    _forgot(client, test_user.email)

    client.post("/users/change-password", headers=auth_headers, json={
        "current_password": "testpassword", "new_password": "Recordada123",
        "confirm_password": "Recordada123"})

    assert _reset(client, _token_from(sent[0][2])).json()["detail"]["reason"] == "used"


# ── The email ────────────────────────────────────────────────────────────────

def test_the_email_carries_the_link_and_its_lifetime(monkeypatch):
    monkeypatch.setattr(email_service.config, "SES_SENDER_EMAIL", "no-reply@boscogest.com")
    monkeypatch.setattr(email_service.config, "SES_CONFIGURATION_SET", None)
    client = MagicMock()
    client.send_email.return_value = {"MessageId": "1"}
    url = "https://app.boscogest.com/restablecer?token=abc"

    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_password_reset_email("socio@example.org", "Ana Pérez", url)

    message = client.send_email.call_args.kwargs["Message"]
    assert "contraseña" in message["Subject"]["Data"]
    for part in ("Html", "Text"):
        body = message["Body"][part]["Data"]
        assert url in body
        assert "2 horas" in body
