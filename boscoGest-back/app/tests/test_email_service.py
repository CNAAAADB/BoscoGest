"""Tests for the welcome-email service.

The SES call is always mocked: these assert the decisions the service makes
around it — when it sends, when it declines to, and that a failure never
escapes to the caller, since it runs inside a BackgroundTask after the HTTP
response has been sent.
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app import config
from app.services import email_service


@pytest.fixture(autouse=True)
def _reset_client():
    email_service.reset_client()
    yield
    email_service.reset_client()


@pytest.fixture
def ses_configured(monkeypatch):
    monkeypatch.setattr(config, "SES_SENDER_EMAIL", "noreply@example.org")
    monkeypatch.setattr(config, "APP_BASE_URL", "https://app.example.org")
    monkeypatch.setattr(config, "SES_CONFIGURATION_SET", "")


def _client_returning(message_id="0100000000000000-abc-000000000000"):
    client = MagicMock()
    client.send_email.return_value = {"MessageId": message_id}
    return client


def test_sends_when_configured(ses_configured):
    client = _client_returning()
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")

    client.send_email.assert_called_once()
    kwargs = client.send_email.call_args.kwargs
    assert kwargs["Source"] == "noreply@example.org"
    assert kwargs["Destination"]["ToAddresses"] == ["socio@example.org"]
    assert "Ana Pérez" in kwargs["Message"]["Body"]["Html"]["Data"]
    assert "https://app.example.org" in kwargs["Message"]["Body"]["Text"]["Data"]


def test_skips_when_recipient_has_no_email(ses_configured):
    """Users may register with a phone number and no email at all.

    Regression test: the routers passed user.email straight through, so a
    phone-only user produced a send to None inside a background task.
    """
    client = _client_returning()
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email(None, "Sin Correo")
        email_service.send_welcome_email("", "Cadena Vacia")

    client.send_email.assert_not_called()


def test_skips_when_sender_not_configured(monkeypatch):
    monkeypatch.setattr(config, "SES_SENDER_EMAIL", "")
    client = _client_returning()
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")

    client.send_email.assert_not_called()


def test_message_rejected_is_swallowed(ses_configured, caplog):
    """The SES sandbox rejects unverified recipients; creation must still stand."""
    client = MagicMock()
    client.send_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Email address is not verified"}},
        "SendEmail",
    )
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")

    assert "sandbox" in caplog.text.lower()


def test_transport_failure_is_swallowed(ses_configured):
    client = MagicMock()
    client.send_email.side_effect = EndpointConnectionError(endpoint_url="https://email.eu-west-1.amazonaws.com")
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")


def test_access_denied_is_swallowed(ses_configured, caplog):
    client = MagicMock()
    client.send_email.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "not authorized to perform ses:SendEmail"}},
        "SendEmail",
    )
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")

    assert "AccessDenied" in caplog.text


def test_configuration_set_is_forwarded_when_set(ses_configured, monkeypatch):
    monkeypatch.setattr(config, "SES_CONFIGURATION_SET", "boscogest-events")
    client = _client_returning()
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", "Ana Pérez")

    assert client.send_email.call_args.kwargs["ConfigurationSetName"] == "boscogest-events"


def test_recipient_name_is_html_escaped(ses_configured):
    """The name comes from user input and lands inside an HTML document."""
    client = _client_returning()
    with patch.object(email_service, "_get_client", return_value=client):
        email_service.send_welcome_email("socio@example.org", '<script>alert(1)</script>')

    html = client.send_email.call_args.kwargs["Message"]["Body"]["Html"]["Data"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_client_is_reused_across_sends(ses_configured):
    with patch.object(email_service.boto3, "client", return_value=_client_returning()) as factory:
        email_service.send_welcome_email("a@example.org", "A")
        email_service.send_welcome_email("b@example.org", "B")

    factory.assert_called_once()


def test_welcome_email_with_a_link_invites_you_to_set_a_password():
    """The two shapes of the message differ in more than a URL."""
    from app.services.email_service import _build_welcome_html, _build_welcome_text

    url = "https://boscogest.es/activar?token=secreto"
    html = _build_welcome_html("Ana Ruiz", "https://boscogest.es", url)
    text = _build_welcome_text("Ana Ruiz", "https://boscogest.es", url)

    assert url in html and url in text
    assert "crear mi contraseña" in html
    # Both facts change what the reader does, so both are said outright.
    assert "72 horas" in html and "72 horas" in text
    assert "una vez" in html and "una vez" in text


def test_welcome_email_without_a_link_does_not_mention_activation():
    """Someone who chose their own password has nothing to activate."""
    from app.services.email_service import _build_welcome_html, _build_welcome_text

    html = _build_welcome_html("Ana Ruiz", "https://boscogest.es", None)
    text = _build_welcome_text("Ana Ruiz", "https://boscogest.es", None)

    assert "activar" not in html.lower()
    assert "caduca" not in html
    assert "contraseña que elegiste" in html
    assert "boscogest.es" in text
