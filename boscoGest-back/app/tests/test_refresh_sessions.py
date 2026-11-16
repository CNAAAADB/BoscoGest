"""Rotating 30-day device sessions: replay, logout and inactive users."""
from datetime import datetime

from app.models.refresh_session_model import RefreshSession
from app.models.user_model import User


def _login(client):
    result = client.post(
        "/auth/token",
        data={"identifier": "test@example.com", "password": "testpassword"},
    )
    assert result.status_code == 200, result.json()
    return result.json()


def test_login_issues_refresh_credential_and_cookie(client, test_user):
    response = client.post(
        "/auth/token",
        data={"identifier": "test@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json()["refresh_token"]
    assert "boscogest_refresh=" in response.headers["set-cookie"]
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "secure" in response.headers["set-cookie"].lower()


def test_refresh_rotates_secret_and_issues_new_access_token(client, test_user):
    first = _login(client)
    renewed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert renewed.status_code == 200, renewed.json()
    assert renewed.json()["refresh_token"] != first["refresh_token"]
    assert renewed.json()["access_token"] != first["access_token"]


def test_refresh_works_with_httponly_cookie(client, test_user):
    session = _login(client)
    # Production uses HTTPS, whereas the test client defaults to plain HTTP.
    # Send the Secure cookie explicitly to exercise the cookie contract.
    response = client.post(
        "/auth/refresh", json={},
        headers={"Cookie": f"boscogest_refresh={session['refresh_token']}"},
    )
    assert response.status_code == 200, response.json()


def test_reused_refresh_revokes_descendants(client, test_user):
    first = _login(client)
    second = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).json()
    replay = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    descendant = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert descendant.status_code == 401


def test_expired_refresh_does_not_work(client, db_session, test_user):
    session = _login(client)
    from app.services.refresh_session_service import _hash

    stored = db_session.query(RefreshSession).filter_by(token_hash=_hash(session["refresh_token"])).one()
    from datetime import timedelta
    stored.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    response = client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert response.status_code == 401


def test_refresh_rejects_inactive_user(client, db_session, test_user):
    session = _login(client)
    db_session.query(User).filter_by(id=test_user.id).update({"is_active": False})
    db_session.commit()
    assert client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]}).status_code == 401


def test_session_revoke_blocks_future_refresh(client, test_user):
    session = _login(client)
    response = client.post("/auth/session/revoke", json={"refresh_token": session["refresh_token"]})
    assert response.status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]}).status_code == 401


def test_refresh_requires_a_credential(client):
    assert client.post("/auth/refresh", json={}).status_code == 401


def test_password_reset_revokes_old_device_sessions(client, db_session, test_user):
    session = _login(client)
    # The actual password reset flow calls this same method. Check that an
    # existing device secret no longer works after a password change.
    from app.services.refresh_session_service import revoke_user_sessions

    revoke_user_sessions(db_session, test_user.id)
    assert client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]}).status_code == 401


def test_web_origin_cannot_read_persistent_refresh_secret(client, test_user):
    login = client.post(
        "/auth/token",
        data={"identifier": "test@example.com", "password": "testpassword"},
        headers={"Origin": "https://boscogest.com"},
    )
    assert login.status_code == 200
    assert login.json()["refresh_token"] is None
    assert "boscogest_refresh=" in login.headers["set-cookie"]


def test_capacitor_origin_receives_refresh_for_encrypted_native_vault(client, test_user):
    login = client.post(
        "/auth/token",
        data={"identifier": "test@example.com", "password": "testpassword"},
        headers={"Origin": "https://localhost"},
    )
    assert login.status_code == 200
    assert login.json()["refresh_token"] is not None
