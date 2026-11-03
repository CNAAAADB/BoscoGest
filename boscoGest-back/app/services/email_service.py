"""Transactional email delivery through AWS SES.

Sending is best-effort by design: a welcome email that cannot be delivered must
never roll back the user that was just created, so every failure is logged and
swallowed. Callers invoke this from a BackgroundTask, after the response has
already been returned.
"""

import logging
import threading
from html import escape
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app import config
# The wording of the email has to state the same lifetime the service enforces,
# so it comes from there rather than being repeated here.
from app.services.activation_service import (
    RESET_TTL_HOURS,
    TOKEN_TTL_HOURS as ACTIVATION_TTL_HOURS,
)

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Lazily build one SES client and reuse it.

    Creating a boto3 client costs tens of milliseconds and opens a new
    connection pool; bulk CSV imports send one email per row, so building a
    client per message would dominate the import time.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = boto3.client("ses", region_name=config.AWS_REGION)
    return _client


def reset_client() -> None:
    """Drop the cached client. Used by the tests."""
    global _client
    with _client_lock:
        _client = None


def _build_welcome_html(
    name: str, app_url: str, activation_url: Optional[str]
) -> str:
    """The welcome message, in one of its two shapes.

    Someone an administrator created never chose a password, so their message
    is an invitation to set one through a link. Someone who registered
    themselves already has one, and telling them to "activate" would be
    confusing — they just get the address of the site.
    """
    safe_name = escape(name)
    safe_url = escape(app_url, quote=True)

    if activation_url:
        safe_activation = escape(activation_url, quote=True)
        lead = (
            "Te hemos dado de alta en BoscoGest. Para entrar por primera vez y "
            "elegir tu contraseña, usa este botón:"
        )
        button_url = safe_activation
        button_label = "Entrar y crear mi contraseña"
        # Said plainly, because both facts change what the reader should do:
        # act soon, and do not pass the message on.
        caveat = f"""
              <p style="color:#777;font-size:13px;line-height:1.6;">
                El enlace caduca en {ACTIVATION_TTL_HOURS} horas y solo se puede
                usar una vez. No lo reenvíes a nadie: quien lo abra entrará en
                tu cuenta.
              </p>
              <p style="color:#777;font-size:13px;line-height:1.6;">
                Si caduca antes de que puedas usarlo, pide uno nuevo desde
                <a href="{safe_url}" style="color:#1a237e;">la página de acceso</a>.
              </p>"""
    else:
        lead = (
            "Tu cuenta se ha creado correctamente. Ya puedes acceder a la "
            "plataforma con la contraseña que elegiste."
        )
        button_url = safe_url
        button_label = "Acceder a BoscoGest"
        caveat = """
              <p style="color:#777;font-size:13px;">
                Si no esperabas este correo, puedes ignorarlo.
              </p>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;padding:40px;">
          <tr>
            <td>
              <h2 style="color:#1a237e;margin-top:0;">¡Bienvenido/a a BoscoGest, {safe_name}!</h2>
              <p style="color:#333;line-height:1.6;">
                {lead}
              </p>
              <p style="text-align:center;margin:32px 0;">
                <a href="{button_url}"
                   style="background:#1a237e;color:#ffffff;padding:12px 28px;
                          border-radius:4px;text-decoration:none;font-weight:bold;">
                  {button_label}
                </a>
              </p>
              <p style="color:#777;font-size:12px;word-break:break-all;">
                Si el botón no funciona, copia esta dirección en tu navegador:<br>
                {button_url}
              </p>
{caveat}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_welcome_text(
    name: str, app_url: str, activation_url: Optional[str]
) -> str:
    """Plain-text alternative. Some clients show this one, and a message with
    only an HTML part also scores worse with spam filters."""
    if activation_url:
        return (
            f"¡Bienvenido/a a BoscoGest, {name}!\n\n"
            "Te hemos dado de alta. Para entrar por primera vez y elegir tu "
            "contraseña, abre esta dirección:\n\n"
            f"{activation_url}\n\n"
            f"El enlace caduca en {ACTIVATION_TTL_HOURS} horas y solo se puede "
            "usar una vez. No lo reenvíes a nadie.\n\n"
            f"Si caduca, pide uno nuevo desde {app_url}"
        )
    return (
        f"¡Bienvenido/a a BoscoGest, {name}!\n\n"
        f"Tu cuenta se ha creado. Accede en: {app_url}"
    )


def send_welcome_email(
    recipient_email: Optional[str],
    recipient_name: str,
    activation_url: Optional[str] = None,
) -> None:
    """Send a welcome email via AWS SES. Logs errors without raising.

    ``activation_url`` turns the message into an invitation to set a password.
    Leave it out for people who chose their own.
    """
    # A user may be registered with a phone number and no email at all
    # (UserBase requires one or the other), in which case there is nothing to
    # send to and boto3 would raise on an empty destination list.
    if not recipient_email:
        logger.info(
            "No email address for %s — skipping welcome email", recipient_name
        )
        return

    if not config.SES_SENDER_EMAIL:
        logger.warning(
            "SES_SENDER_EMAIL not configured — skipping welcome email to %s",
            recipient_email,
        )
        return

    app_url = config.APP_BASE_URL
    request = {
        "Source": config.SES_SENDER_EMAIL,
        "Destination": {"ToAddresses": [recipient_email]},
        "Message": {
            "Subject": {
                "Data": (
                    "Activa tu cuenta de BoscoGest"
                    if activation_url
                    else "Bienvenido/a a BoscoGest"
                ),
                "Charset": "UTF-8",
            },
            "Body": {
                "Html": {
                    "Data": _build_welcome_html(
                        recipient_name, app_url, activation_url
                    ),
                    "Charset": "UTF-8",
                },
                "Text": {
                    "Data": _build_welcome_text(
                        recipient_name, app_url, activation_url
                    ),
                    "Charset": "UTF-8",
                },
            },
        },
    }
    _deliver(request, recipient_email, "welcome")


def _deliver(request: dict, recipient_email: str, kind: str) -> None:
    """Hand a built message to SES, logging instead of raising."""
    # Lets SES report bounces and complaints, which is a prerequisite for
    # keeping production sending access.
    if config.SES_CONFIGURATION_SET:
        request["ConfigurationSetName"] = config.SES_CONFIGURATION_SET

    try:
        response = _get_client().send_email(**request)
        logger.info(
            "%s email sent to %s (MessageId=%s)",
            kind.capitalize(),
            recipient_email,
            response.get("MessageId"),
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "MessageRejected":
            # In the SES sandbox every recipient must be verified; this is the
            # error that shows up when it is not, and it is worth calling out
            # explicitly rather than losing it in a generic failure.
            logger.error(
                "SES rejected the message to %s — the sender or recipient is "
                "probably not a verified identity, or the account is still in "
                "the SES sandbox: %s",
                recipient_email,
                exc,
            )
        else:
            logger.error(
                "Failed to send %s email to %s (%s): %s",
                kind,
                recipient_email,
                code or "unknown",
                exc,
            )
    except BotoCoreError as exc:
        logger.error("Failed to send %s email to %s: %s", kind, recipient_email, exc)


def _build_reset_html(name: str, reset_url: str) -> str:
    safe_name = escape(name)
    safe_reset = escape(reset_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;padding:40px;">
          <tr>
            <td>
              <h2 style="color:#1a237e;margin-top:0;">Hola, {safe_name}</h2>
              <p style="color:#333;line-height:1.6;">
                Hemos recibido una petición para cambiar la contraseña de tu
                cuenta de BoscoGest. Para elegir una nueva, usa este botón:
              </p>
              <p style="text-align:center;margin:32px 0;">
                <a href="{safe_reset}"
                   style="background:#1a237e;color:#ffffff;padding:12px 28px;
                          border-radius:4px;text-decoration:none;font-weight:bold;">
                  Cambiar mi contraseña
                </a>
              </p>
              <p style="color:#777;font-size:12px;word-break:break-all;">
                Si el botón no funciona, copia esta dirección en tu navegador:<br>
                {safe_reset}
              </p>
              <p style="color:#777;font-size:13px;line-height:1.6;">
                El enlace caduca en {RESET_TTL_HOURS} horas y solo se puede usar
                una vez. No lo reenvíes a nadie.
              </p>
              <p style="color:#777;font-size:13px;line-height:1.6;">
                Si no has sido tú, no hagas nada: tu contraseña sigue siendo la
                misma.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_reset_text(name: str, reset_url: str) -> str:
    return (
        f"Hola, {name}:\n\n"
        "Hemos recibido una petición para cambiar la contraseña de tu cuenta "
        "de BoscoGest. Para elegir una nueva, abre esta dirección:\n\n"
        f"{reset_url}\n\n"
        f"El enlace caduca en {RESET_TTL_HOURS} horas y solo se puede usar una "
        "vez. No lo reenvíes a nadie.\n\n"
        "Si no has sido tú, no hagas nada: tu contraseña sigue siendo la misma."
    )


def send_password_reset_email(
    recipient_email: str, recipient_name: str, reset_url: str
) -> None:
    """Send the forgotten-password link via AWS SES. Logs errors without raising."""
    if not config.SES_SENDER_EMAIL:
        logger.warning(
            "SES_SENDER_EMAIL not configured — skipping password reset email to %s",
            recipient_email,
        )
        return

    request = {
        "Source": config.SES_SENDER_EMAIL,
        "Destination": {"ToAddresses": [recipient_email]},
        "Message": {
            "Subject": {"Data": "Cambia tu contraseña de BoscoGest", "Charset": "UTF-8"},
            "Body": {
                "Html": {"Data": _build_reset_html(recipient_name, reset_url), "Charset": "UTF-8"},
                "Text": {"Data": _build_reset_text(recipient_name, reset_url), "Charset": "UTF-8"},
            },
        },
    }
    _deliver(request, recipient_email, "password reset")
