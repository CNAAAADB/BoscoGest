"""Envío de notificaciones push a través de Firebase Cloud Messaging.

Por qué FCM y no APNs directamente: en iOS el push lo entrega APNs
obligatoriamente, y en Android lo entrega FCM, así que hacen falta los dos de
todos modos. FCM sabe hablar con APNs, de modo que usarlo para ambos deja un
solo camino de código y un solo juego de credenciales en el servidor.

Sin credenciales configuradas no se envía nada y queda un aviso en el log, igual
que hace el correo cuando falta SES_SENDER_EMAIL. La aplicación funciona entera
sin push: es un canal más, no el que sostiene nada.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import config
from app.models.notification_model import DeviceToken

logger = logging.getLogger(__name__)

_FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

# Respuestas de FCM que significan "este token ya no vale". Cualquier otro
# error es transitorio y el token se conserva.
_DEAD_TOKEN_ERRORS = {"UNREGISTERED", "INVALID_ARGUMENT"}

# El token OAuth dura una hora y google-auth lo renueva solo, pero las
# credenciales hay que construirlas una vez: leer el JSON y firmar en cada
# envío sería tirar el trabajo a la basura. El lock protege la construcción,
# porque los servicios corren en el pool de hilos de Uvicorn.
_credentials = None
_credentials_lock = threading.Lock()


def _get_credentials():
    """Credenciales de la cuenta de servicio, construidas una sola vez."""
    global _credentials
    if _credentials is not None:
        return _credentials
    with _credentials_lock:
        if _credentials is None:
            from google.oauth2 import service_account

            _credentials = service_account.Credentials.from_service_account_file(
                config.FCM_CREDENTIALS_FILE, scopes=[_SCOPE]
            )
    return _credentials


def reset_credentials() -> None:
    """Olvida las credenciales cacheadas. Para los tests."""
    global _credentials
    _credentials = None


def _access_token() -> str:
    from google.auth.transport.requests import Request as GoogleRequest

    creds = _get_credentials()
    if not creds.valid:
        creds.refresh(GoogleRequest())
    return creds.token


def build_message(token: str, title: str, body: str | None, data: Dict[str, Any]) -> dict:
    """El cuerpo de una petición a FCM HTTP v1.

    El texto que se muestra va en `notification`, y en `data` solo van
    identificadores: el aviso aparece en la pantalla bloqueada, a la vista de
    cualquiera que coja el móvil, así que no debe llevar datos personales.
    Todo valor de `data` tiene que ser una cadena; FCM rechaza el resto.
    """
    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body or ""},
            "data": {k: str(v) for k, v in data.items() if v is not None},
            "android": {"priority": "high"},
            "apns": {
                "headers": {"apns-priority": "10"},
                # El badge y el sonido los decide el cliente; aquí solo se
                # marca que es una alerta visible.
                "payload": {"aps": {"sound": "default"}},
            },
        }
    }


def send_to_user(
    db: Session,
    user_id: int,
    title: str,
    body: str | None,
    data: Dict[str, Any] | None = None,
) -> int:
    """Envía a todos los dispositivos de una persona. Devuelve cuántos salieron.

    Nunca lanza: un fallo de push no puede tumbar la operación que lo originó
    —publicar una actividad, aceptar una inscripción—, porque la notificación
    ya está guardada y se verá igual al abrir la aplicación.
    """
    if not config.push_is_configured():
        logger.info(
            "Push sin configurar (FCM_PROJECT_ID / FCM_CREDENTIALS_FILE) — "
            "no se envía nada al usuario %s",
            user_id,
        )
        return 0

    tokens = list(
        db.execute(
            select(DeviceToken.token).where(DeviceToken.user_id == user_id)
        ).scalars().all()
    )
    if not tokens:
        return 0

    try:
        access_token = _access_token()
    except Exception:
        logger.warning("No se pudo obtener el token de acceso de FCM", exc_info=True)
        return 0

    url = _FCM_ENDPOINT.format(project=config.FCM_PROJECT_ID)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    enviados = 0
    muertos: List[str] = []
    # FCM HTTP v1 no admite envío por lotes: una petición por dispositivo. Son
    # pocos por persona, y esto corre en una tarea de fondo.
    with httpx.Client(timeout=10.0) as client:
        for token in tokens:
            try:
                resp = client.post(
                    url, headers=headers,
                    content=json.dumps(build_message(token, title, body, data or {})),
                )
                if resp.status_code == 200:
                    enviados += 1
                elif _is_dead_token(resp):
                    muertos.append(token)
                else:
                    logger.warning(
                        "FCM devolvió %s para un dispositivo del usuario %s",
                        resp.status_code, user_id,
                    )
            except Exception:
                logger.warning(
                    "Fallo enviando push a un dispositivo del usuario %s",
                    user_id, exc_info=True,
                )

    if muertos:
        _forget(db, muertos)

    return enviados


def _is_dead_token(resp: httpx.Response) -> bool:
    """Si la respuesta dice que el token ya no existe.

    Se mira el estado del error, no solo el código HTTP: un 404 siempre es un
    token dado de baja, pero un 400 puede serlo o puede ser un mensaje mal
    construido, y esos no se deben borrar.
    """
    if resp.status_code == 404:
        return True
    if resp.status_code != 400:
        return False
    try:
        status = resp.json().get("error", {}).get("status", "")
    except Exception:
        return False
    return status in _DEAD_TOKEN_ERRORS


def _forget(db: Session, tokens: List[str]) -> None:
    """Borra los dispositivos que FCM ya no reconoce.

    Pasa constantemente: desinstalar la app, restaurar una copia de seguridad o
    limpiar los datos invalidan el token. Sin esta limpieza la tabla acumula
    destinatarios inexistentes y cada envío gasta una petición en ellos.
    """
    try:
        db.execute(delete(DeviceToken).where(DeviceToken.token.in_(tokens)))
        db.commit()
        logger.info("Eliminados %s dispositivos que FCM ya no reconoce", len(tokens))
    except Exception:
        db.rollback()
        logger.warning("No se pudieron eliminar dispositivos caducados", exc_info=True)
