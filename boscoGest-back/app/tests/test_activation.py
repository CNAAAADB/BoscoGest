"""One-shot sign-in links from the welcome email."""

from datetime import datetime, timedelta

import pytest

from app.models.activation_token_model import ActivationToken
from app.services import activation_service


def _issue(db_session, user):
    return activation_service.issue_token(db_session, user)


def test_a_link_signs_you_in_once(client, db_session, test_user):
    """The whole point: in without a password, and only the once."""
    raw = _issue(db_session, test_user)

    first = client.post("/auth/activate", json={"token": raw})
    assert first.status_code == 200
    assert first.json()["access_token"]
    assert first.json()["token_type"] == "bearer"

    second = client.post("/auth/activate", json={"token": raw})
    assert second.status_code == 410
    assert second.json()["detail"]["reason"] == "used"


def test_the_secret_is_not_stored(db_session, test_user):
    """A database dump must not yield working links."""
    raw = _issue(db_session, test_user)

    stored = db_session.query(ActivationToken).filter_by(user_id=test_user.id).one()
    assert stored.token_hash != raw
    assert raw not in stored.token_hash
    assert stored.token_hash == activation_service.hash_token(raw)


def test_an_expired_link_is_refused(client, db_session, test_user):
    """72 hours, and the reason says so — the screen offers a new one."""
    raw = _issue(db_session, test_user)
    token = db_session.query(ActivationToken).filter_by(user_id=test_user.id).one()
    token.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    response = client.post("/auth/activate", json={"token": raw})

    assert response.status_code == 410
    assert response.json()["detail"]["reason"] == "expired"


def test_the_link_lasts_72_hours(db_session, test_user):
    _issue(db_session, test_user)
    token = db_session.query(ActivationToken).filter_by(user_id=test_user.id).one()

    remaining = token.expires_at - datetime.utcnow()
    assert timedelta(hours=71, minutes=59) < remaining <= timedelta(hours=72)


def test_a_made_up_token_is_refused(client):
    response = client.post("/auth/activate", json={"token": "x" * 40})

    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "invalid"


def test_issuing_a_link_burns_the_previous_one(client, db_session, test_user):
    """A second welcome email must not leave the first link working."""
    first_raw = _issue(db_session, test_user)
    second_raw = _issue(db_session, test_user)

    assert client.post("/auth/activate", json={"token": first_raw}).status_code == 410
    assert client.post("/auth/activate", json={"token": second_raw}).status_code == 200


def test_setting_a_password_burns_outstanding_links(
    client, db_session, test_user, auth_headers
):
    """The welcome email stays in the inbox; it must stop being a way in."""
    test_user.must_change_password = True
    db_session.commit()
    raw = _issue(db_session, test_user)

    changed = client.post(
        "/users/first-time-password-change",
        json={"new_password": "NuevaClave123", "confirm_password": "NuevaClave123"},
        headers=auth_headers,
    )
    assert changed.status_code == 200

    assert client.post("/auth/activate", json={"token": raw}).status_code == 410


def test_a_link_for_a_deactivated_account_is_refused(client, db_session, test_user):
    raw = _issue(db_session, test_user)
    test_user.is_active = False
    db_session.commit()

    response = client.post("/auth/activate", json={"token": raw})

    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "invalid"


def test_resend_answers_the_same_for_an_unknown_address(client):
    """Otherwise the form would tell anyone whether an address is a member."""
    known = client.post(
        "/auth/activate/resend", json={"identifier": "nadie@ejemplo.com"}
    )
    assert known.status_code == 202
    assert "Si esa cuenta existe" in known.json()["message"]


def test_resend_issues_a_link_for_an_account_without_a_password(
    client, db_session, test_user
):
    test_user.must_change_password = True
    db_session.commit()

    response = client.post(
        "/auth/activate/resend", json={"identifier": test_user.email}
    )

    assert response.status_code == 202
    assert db_session.query(ActivationToken).filter_by(user_id=test_user.id).count() == 1


def test_resend_does_nothing_for_someone_who_has_a_password(
    client, db_session, test_user
):
    """They should sign in normally, not be handed a way round the password."""
    test_user.must_change_password = False
    db_session.commit()

    response = client.post(
        "/auth/activate/resend", json={"identifier": test_user.email}
    )

    assert response.status_code == 202
    assert db_session.query(ActivationToken).filter_by(user_id=test_user.id).count() == 0


def test_the_url_points_at_the_activation_screen():
    url = activation_service.build_activation_url("abc-123")

    assert "/activar?token=abc-123" in url


# --- Handing over a link by hand -------------------------------------------
#
# The welcome email cannot reach everyone: some members are registered with a
# phone and no address, and some messages never arrive. An administrator can
# mint a link for those and pass it on however they already talk to them.


def test_an_admin_can_get_a_link_for_someone_who_never_set_a_password(
    client, db_session, test_user, auth_headers, test_membership
):
    test_user.must_change_password = True
    db_session.commit()

    response = client.post(
        f"/users/{test_user.id}/activation-link", headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert "/activar?token=" in body["url"]
    assert body["expires_in_hours"] == 72

    # And it works, which is the only thing that makes it worth handing over.
    raw = body["url"].split("token=")[1]
    assert client.post("/auth/activate", json={"token": raw}).status_code == 200


def test_no_link_for_someone_who_already_chose_a_password(
    client, db_session, test_user, auth_headers, test_membership
):
    """The limit that keeps this from being a way into any account.

    For an account that never set a password the administrator already knew the
    initial one, so a link grants nothing new. Once the member has chosen their
    own, it would.
    """
    test_user.must_change_password = False
    db_session.commit()

    response = client.post(
        f"/users/{test_user.id}/activation-link", headers=auth_headers
    )

    assert response.status_code == 409
    assert "ya eligió su contraseña" in response.json()["detail"]


def test_no_link_for_a_deactivated_account(
    client, db_session, test_user, auth_headers, test_membership, test_role
):
    """A separate account, because deactivating the caller's own would just
    invalidate their session."""
    from datetime import datetime as dt

    from app.models.membership_model import Membership
    from app.models.user_model import User as UserModel

    other = UserModel(
        email="baja@ejemplo.com",
        password_hash="x",
        name="Baja",
        surname="Ejemplo",
        dni="99999999Z",
        birthdate=dt(1990, 1, 1).date(),
        is_active=False,
        must_change_password=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.add(
        Membership(
            user_id=other.id,
            entity_id=test_membership.entity_id,
            role_id=test_role.id,
            is_active=True,
            created_at=dt.utcnow(),
        )
    )
    db_session.commit()

    response = client.post(
        f"/users/{other.id}/activation-link", headers=auth_headers
    )

    assert response.status_code == 409
    assert "dado de baja" in response.json()["detail"]


def test_no_link_for_an_unknown_user(client, auth_headers):
    response = client.post("/users/999999/activation-link", headers=auth_headers)

    assert response.status_code == 404


# --- The CSV no longer carries passwords ------------------------------------


def test_the_csv_no_longer_requires_a_password_column():
    """A roster of members should not travel with credentials in it.

    Nobody uses the password anyway: everyone created this way gets in through
    the link in their welcome email.
    """
    import inspect

    from app.services import user_service

    source = inspect.getsource(user_service.UserService.create_bulk_upload_job)
    required = source[source.index("required_columns"):source.index("csv_columns")]

    assert "password" not in required
    for column in ("name", "surname", "birthdate"):
        assert column in required


def test_generated_passwords_are_random_and_long():
    """They are never shown, never typed and never recovered, so the only
    property that matters is being impossible to guess."""
    from app.services.user_service import generate_unusable_password

    passwords = {generate_unusable_password() for _ in range(50)}

    assert len(passwords) == 50
    assert all(len(p) >= 32 for p in passwords)


def test_a_csv_without_passwords_still_creates_working_accounts(
    monkeypatch, db_session, test_entity, test_user, test_role, test_membership
):
    """The whole point of dropping the column, exercised end to end.

    A row with no password produces a usable account with an activation link,
    and the generated hash is not something anyone could have supplied.
    """
    from app.models.bulk_upload_job_model import BulkUploadJob
    from app.models.user_model import User as UserModel
    from app.services import user_service
    from app.tests.conftest import TestingSessionLocal

    # The background task opens its own session; point it at the test database.
    monkeypatch.setattr(
        "app.database.SyncSessionLocal", TestingSessionLocal, raising=False
    )

    csv_content = (
        '"email","name","surname","phone","birthdate","dni"\n'
        '"nueva@ejemplo.com","Nueva","Socia","611000111","1992-04-04","10101010X"\n'
    ).encode("utf-8")

    job = BulkUploadJob(
        created_by_id=test_user.id,
        target_entity_id=test_entity.id,
        target_role_id=test_role.id,
        status="pending",
        csv_filename="sin-passwords.csv",
        csv_content=csv_content,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    user_service.process_bulk_upload_job(job.id, test_user.id, None)

    db_session.refresh(job)
    assert job.failed == 0, job.errors
    assert job.successful == 1

    created = db_session.query(UserModel).filter_by(email="nueva@ejemplo.com").one()
    assert created.must_change_password is True
    # Whatever ended up in the column, it is not something a person typed.
    assert created.password_hash
    assert len(created.password_hash) > 20

    # And they have a way in.
    from app.models.activation_token_model import ActivationToken

    assert (
        db_session.query(ActivationToken).filter_by(user_id=created.id).count() == 1
    )


def test_creating_a_user_needs_no_password(
    client, db_session, auth_headers, test_entity, test_role, test_membership,
    test_permissions,
):
    """The form no longer asks for one, so neither does the endpoint.

    Whoever fills it in was inventing a credential nobody would ever use: the
    person created signs in through the link in their welcome email.
    """
    from app.models.activation_token_model import ActivationToken
    from app.models.user_model import User as UserModel

    response = client.post(
        "/users",
        json={
            "email": "sinclave@ejemplo.com",
            "name": "Sin",
            "surname": "Clave",
            "birthdate": "1991-02-03",
            "dni": "20202020Y",
            "entity_id": test_entity.id,
            "role_id": test_role.id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    created = db_session.query(UserModel).filter_by(email="sinclave@ejemplo.com").one()
    assert created.must_change_password is True
    assert created.password_hash

    # And a way in was minted for them.
    assert (
        db_session.query(ActivationToken).filter_by(user_id=created.id).count() == 1
    )


def test_a_password_sent_anyway_is_not_accepted_as_one(
    client, db_session, auth_headers, test_entity, test_role, test_membership,
    test_permissions,
):
    """An old client sending the field must not end up setting a password.

    Pydantic ignores the extra key, so what matters is that the stored hash is
    not of what was sent.
    """
    from app.models.user_model import User as UserModel
    from app.utils.auth import verify_password

    response = client.post(
        "/users",
        json={
            "email": "ignorada@ejemplo.com",
            "name": "Clave",
            "surname": "Ignorada",
            "birthdate": "1991-02-03",
            "dni": "30303030W",
            "password": "LoQueSea123",
            "entity_id": test_entity.id,
            "role_id": test_role.id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    created = db_session.query(UserModel).filter_by(email="ignorada@ejemplo.com").one()
    assert not verify_password("LoQueSea123", created.password_hash)


def test_a_csv_email_that_is_not_an_address_is_rejected(
    monkeypatch, db_session, test_entity, test_user, test_role, test_membership
):
    """Spreadsheets export an empty cell as "0", and that used to get stored.

    UserResponse reads `email` back as an EmailStr, so one bad value broke
    every listing containing that user — surfacing in the browser as a CORS
    error, since the 500 carries no CORS headers. The row has to be refused on
    the way in.
    """
    from app.models.bulk_upload_job_model import BulkUploadJob
    from app.models.user_model import User as UserModel
    from app.services import user_service
    from app.tests.conftest import TestingSessionLocal

    monkeypatch.setattr(
        "app.database.SyncSessionLocal", TestingSessionLocal, raising=False
    )

    csv_content = (
        '"email","phone","name","surname","birthdate","dni"\n'
        '"0","611000222","Cero","Excel","1990-01-01","40404040T"\n'
        '"buena@ejemplo.com","611000333","Buena","Fila","1991-02-02","50505050R"\n'
    ).encode("utf-8")

    job = BulkUploadJob(
        created_by_id=test_user.id,
        target_entity_id=test_entity.id,
        target_role_id=test_role.id,
        status="pending",
        csv_filename="con-ceros.csv",
        csv_content=csv_content,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    user_service.process_bulk_upload_job(job.id, test_user.id, None)

    db_session.refresh(job)
    assert job.successful == 1
    assert job.failed == 1
    assert "not a valid email address" in job.errors[0]["error"]

    # The good row still went in, and the bad one left nothing behind.
    assert db_session.query(UserModel).filter_by(email="buena@ejemplo.com").count() == 1
    assert db_session.query(UserModel).filter_by(email="0").count() == 0


def test_a_row_failure_never_stores_personal_data():
    """The error report must not reproduce the roster the CSV is discarded to
    avoid keeping.

    A database-level failure arrives as a SQLAlchemy error whose text embeds
    the whole INSERT with every bound parameter, password hash included. That
    used to be stored verbatim and shown in the import history.

    Tested against the function rather than a real import: SQLite does not
    enforce column lengths, so the failure that leaked in production cannot be
    provoked through the test database.
    """
    from sqlalchemy.exc import DataError

    from app.services.user_service import _safe_row_error

    # The shape psycopg2 produces, trimmed but faithful.
    crudo = (
        '(psycopg2.errors.StringDataRightTruncation) value too long for type '
        'character varying(34)\n[SQL: INSERT INTO users (password_hash, email, '
        "name, dni, iban) VALUES (%(password_hash)s, ...)]\n[parameters: "
        "{'password_hash': '$2b$12$abcdefghijklmnop', 'email': "
        "'david@ejemplo.es', 'name': 'David', 'dni': '11830829C', 'iban': "
        "'ES5120381953166000150372038460590600008'}]"
    )
    exc = DataError("INSERT INTO users ...", {}, Exception(crudo))

    mensaje = _safe_row_error(exc)

    for filtracion in (
        "INSERT INTO", "password_hash", "$2b$", "david@ejemplo.es",
        "11830829C", "ES5120381953",
    ):
        assert filtracion not in mensaje, f"el error filtra {filtracion!r}"
    assert "longitud" in mensaje


def test_our_own_row_errors_keep_their_wording():
    """The row-level checks raise ValueError with text written to be read, so
    that one passes through untouched."""
    from app.services.user_service import _safe_row_error

    nuestro = ValueError("'0' is not a valid email address; leave the column empty")
    assert _safe_row_error(nuestro) == str(nuestro)
