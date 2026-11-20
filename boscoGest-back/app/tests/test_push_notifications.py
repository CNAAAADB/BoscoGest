"""Notificaciones push: registro de dispositivos y envío.

El envío real contra FCM no se prueba aquí —haría falta un proyecto de
Firebase y salir a la red—, pero sí todo lo que lo rodea: que sin credenciales
no se intente nada, que el mensaje se construya como espera FCM, que los
dispositivos caducados se limpien y que quien esté conectado no reciba el aviso
por duplicado.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models.notification_model import DeviceToken, NotificationPreference
from app.models.user_model import User
from app.services import push_service
from app.services.notification_service import EventType, NotificationService
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture(autouse=True)
def _sin_credenciales_por_defecto():
    """Cada test arranca con el push sin configurar, que es el estado real.

    Y con las credenciales cacheadas limpias, porque el módulo las guarda entre
    llamadas y un test que las configure contaminaría al siguiente.
    """
    push_service.reset_credentials()
    yield
    push_service.reset_credentials()


@pytest.fixture
def sin_websocket():
    """Silencia el canal WebSocket durante las pruebas de push.

    notification_manager es un singleton que guarda el event loop de la
    aplicación. Cuando un test anterior ha levantado y cerrado un TestClient,
    ese loop queda cerrado y encolar en él revienta con "Event loop is closed".
    Aquí lo que se prueba es el push, no la entrega por WebSocket.
    """
    with patch(
        "app.services.notification_service.notification_manager.enqueue"
    ):
        yield


@pytest.fixture
def otro_usuario(db_session):
    user = User(
        email="otro@example.com",
        password_hash=get_password_hash("Otrapass1"),
        name="Otro",
        surname="Usuario",
        phone="600333222",
        birthdate=datetime(1993, 4, 4).date(),
        dni="33333333P",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Registro de dispositivos ─────────────────────────────────────────


def test_registrar_dispositivo(client, auth_headers, db_session, test_user):
    response = client.post(
        "/notifications/devices",
        json={"token": "token-del-movil", "platform": "android"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["platform"] == "android"
    guardado = db_session.query(DeviceToken).filter_by(token="token-del-movil").first()
    assert guardado is not None
    assert guardado.user_id == test_user.id


def test_registrar_requiere_sesion(client):
    response = client.post(
        "/notifications/devices", json={"token": "t", "platform": "ios"}
    )
    assert response.status_code == 401


def test_plataforma_invalida_se_rechaza(client, auth_headers):
    response = client.post(
        "/notifications/devices",
        json={"token": "t", "platform": "windows"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_registrar_dos_veces_no_duplica(client, auth_headers, db_session):
    """La app lo llama en cada arranque, no solo la primera vez."""
    for _ in range(3):
        client.post(
            "/notifications/devices",
            json={"token": "mismo-token", "platform": "ios"},
            headers=auth_headers,
        )

    assert db_session.query(DeviceToken).filter_by(token="mismo-token").count() == 1


def test_el_token_se_reasigna_al_nuevo_dueno(
    client, auth_headers, db_session, test_user, otro_usuario, test_membership
):
    """Un móvil compartido, o alguien que entra con otra cuenta.

    Si no se reasignara, el dueño anterior seguiría recibiendo en ese teléfono
    los avisos de su asociación.
    """
    client.post(
        "/notifications/devices",
        json={"token": "movil-compartido", "platform": "android"},
        headers=auth_headers,
    )

    token_otro = create_access_token({"sub": str(otro_usuario.id)})
    client.post(
        "/notifications/devices",
        json={"token": "movil-compartido", "platform": "android"},
        headers={"Authorization": f"Bearer {token_otro}"},
    )

    db_session.expire_all()
    dispositivos = db_session.query(DeviceToken).filter_by(token="movil-compartido").all()
    assert len(dispositivos) == 1
    assert dispositivos[0].user_id == otro_usuario.id


def test_dar_de_baja_un_dispositivo(client, auth_headers, db_session):
    client.post(
        "/notifications/devices",
        json={"token": "token-baja", "platform": "ios"},
        headers=auth_headers,
    )

    response = client.request(
        "DELETE",
        "/notifications/devices",
        json={"token": "token-baja", "platform": "ios"},
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert db_session.query(DeviceToken).filter_by(token="token-baja").first() is None


def test_no_se_puede_dar_de_baja_el_dispositivo_de_otro(
    client, auth_headers, db_session, otro_usuario
):
    db_session.add(
        DeviceToken(user_id=otro_usuario.id, token="token-ajeno", platform="ios")
    )
    db_session.commit()

    client.request(
        "DELETE",
        "/notifications/devices",
        json={"token": "token-ajeno", "platform": "ios"},
        headers=auth_headers,
    )

    db_session.expire_all()
    assert db_session.query(DeviceToken).filter_by(token="token-ajeno").first() is not None


# ── Envío ────────────────────────────────────────────────────────────


def test_sin_credenciales_no_se_envia_nada(db_session, test_user):
    """El estado por defecto: la app entera funciona sin push configurado."""
    db_session.add(
        DeviceToken(user_id=test_user.id, token="t", platform="ios")
    )
    db_session.commit()

    with patch("httpx.Client") as cliente:
        enviados = push_service.send_to_user(db_session, test_user.id, "Hola", "Qué tal")

    assert enviados == 0
    cliente.assert_not_called()


def test_sin_dispositivos_no_se_pide_token_de_acceso(db_session, test_user):
    with patch("app.config.push_is_configured", return_value=True), \
         patch.object(push_service, "_access_token") as token:
        enviados = push_service.send_to_user(db_session, test_user.id, "Hola", None)

    assert enviados == 0
    token.assert_not_called()


def test_el_mensaje_tiene_la_forma_que_espera_fcm():
    mensaje = push_service.build_message(
        "abc", "Nueva actividad", "Campamento de verano", {"event_type": "activity_created"}
    )["message"]

    assert mensaje["token"] == "abc"
    assert mensaje["notification"] == {
        "title": "Nueva actividad",
        "body": "Campamento de verano",
    }
    # FCM rechaza un data con valores que no sean cadenas.
    assert all(isinstance(v, str) for v in mensaje["data"].values())
    assert mensaje["android"]["priority"] == "high"
    assert "apns" in mensaje


def test_el_cuerpo_vacio_viaja_como_cadena():
    """FCM no admite null en notification.body."""
    mensaje = push_service.build_message("abc", "Título", None, {})["message"]
    assert mensaje["notification"]["body"] == ""


def test_los_valores_nulos_no_llegan_a_data():
    mensaje = push_service.build_message(
        "abc", "T", "B", {"event_type": "x", "resource_id": None}
    )["message"]
    assert "resource_id" not in mensaje["data"]


@pytest.mark.parametrize(
    "status_code,cuerpo,es_baja",
    [
        (404, {}, True),
        (400, {"error": {"status": "UNREGISTERED"}}, True),
        (400, {"error": {"status": "INVALID_ARGUMENT"}}, True),
        # Transitorios: el token sigue siendo bueno y no debe borrarse.
        (500, {}, False),
        (503, {}, False),
        (400, {"error": {"status": "QUOTA_EXCEEDED"}}, False),
    ],
)
def test_solo_se_borran_los_tokens_que_fcm_da_por_muertos(status_code, cuerpo, es_baja):
    respuesta = httpx.Response(
        status_code, json=cuerpo, request=httpx.Request("POST", "http://x")
    )
    assert push_service._is_dead_token(respuesta) is es_baja


def test_un_token_caducado_se_elimina(db_session, test_user):
    db_session.add(DeviceToken(user_id=test_user.id, token="caducado", platform="ios"))
    db_session.commit()

    respuesta = httpx.Response(
        404, json={}, request=httpx.Request("POST", "http://x")
    )
    cliente = MagicMock()
    cliente.__enter__.return_value.post.return_value = respuesta

    with patch("app.config.push_is_configured", return_value=True), \
         patch.object(push_service, "_access_token", return_value="tok"), \
         patch("httpx.Client", return_value=cliente):
        enviados = push_service.send_to_user(db_session, test_user.id, "Hola", None)

    assert enviados == 0
    db_session.expire_all()
    assert db_session.query(DeviceToken).filter_by(token="caducado").first() is None


def test_un_fallo_de_red_no_propaga(db_session, test_user):
    """Un push que no sale no puede tumbar la operación que lo originó."""
    db_session.add(DeviceToken(user_id=test_user.id, token="t", platform="ios"))
    db_session.commit()

    cliente = MagicMock()
    cliente.__enter__.return_value.post.side_effect = httpx.ConnectError("sin red")

    with patch("app.config.push_is_configured", return_value=True), \
         patch.object(push_service, "_access_token", return_value="tok"), \
         patch("httpx.Client", return_value=cliente):
        enviados = push_service.send_to_user(db_session, test_user.id, "Hola", None)

    assert enviados == 0
    db_session.expire_all()
    # El token era bueno: un corte de red no es motivo para darlo de baja.
    assert db_session.query(DeviceToken).filter_by(token="t").first() is not None


# ── Integración con notify() ─────────────────────────────────────────


def test_a_quien_esta_conectado_no_se_le_manda_push(
    sin_websocket,
    db_session, test_user, otro_usuario, test_entity, test_membership
):
    """Ya lo ha recibido por WebSocket; las dos cosas a la vez es lo que hace
    que la gente acabe apagando las notificaciones."""
    service = NotificationService(db_session)

    with patch(
        "app.services.notification_service.notification_manager.is_online",
        return_value=True,
    ), patch("app.services.push_service.send_to_user") as enviar:
        service.notify(
            event_type=EventType.ACTIVITY_CREATED,
            entity_id=test_entity.id,
            actor=otro_usuario,
            resource_type="activities",
            title="Nueva actividad",
        )

    enviar.assert_not_called()


def test_a_quien_esta_desconectado_si(
    sin_websocket,
    db_session, test_user, otro_usuario, test_entity, test_membership
):
    service = NotificationService(db_session)

    with patch(
        "app.services.notification_service.notification_manager.is_online",
        return_value=False,
    ), patch("app.services.push_service.send_to_user") as enviar:
        service.notify(
            event_type=EventType.ACTIVITY_CREATED,
            entity_id=test_entity.id,
            actor=otro_usuario,
            resource_type="activities",
            title="Nueva actividad",
        )

    assert enviar.called
    assert enviar.call_args.kwargs["title"] == "Nueva actividad"
    # Solo identificadores: el aviso se ve en la pantalla bloqueada. Estos tres
    # son los que el cliente necesita para abrir la pantalla correcta al tocar.
    assert enviar.call_args.kwargs["data"] == {
        "event_type": "activity_created",
        "resource_type": "activities",
        "resource_id": None,
    }


def test_se_respeta_la_preferencia_de_push(
    sin_websocket,
    db_session, test_user, otro_usuario, test_entity, test_membership
):
    """Se puede querer el aviso dentro de la app pero no que suene el móvil."""
    db_session.add(
        NotificationPreference(
            user_id=test_user.id,
            event_type=EventType.ACTIVITY_CREATED.value,
            in_app_enabled=True,
            push_enabled=False,
        )
    )
    db_session.commit()

    service = NotificationService(db_session)
    with patch(
        "app.services.notification_service.notification_manager.is_online",
        return_value=False,
    ), patch("app.services.push_service.send_to_user") as enviar:
        notificaciones = service.notify(
            event_type=EventType.ACTIVITY_CREATED,
            entity_id=test_entity.id,
            actor=otro_usuario,
            resource_type="activities",
            title="Nueva actividad",
        )

    # La notificación se guarda igual: la preferencia solo apaga el push.
    assert len(notificaciones) == 1
    enviar.assert_not_called()


def test_un_fallo_de_push_no_rompe_la_notificacion(
    sin_websocket,
    db_session, test_user, otro_usuario, test_entity, test_membership
):
    service = NotificationService(db_session)

    with patch(
        "app.services.notification_service.notification_manager.is_online",
        return_value=False,
    ), patch(
        "app.services.push_service.send_to_user", side_effect=RuntimeError("boom")
    ):
        notificaciones = service.notify(
            event_type=EventType.ACTIVITY_CREATED,
            entity_id=test_entity.id,
            actor=otro_usuario,
            resource_type="activities",
            title="Nueva actividad",
        )

    assert len(notificaciones) == 1


def test_the_transport_google_auth_needs_is_installed():
    """push_service refreshes its token through google.auth.transport.requests,
    which needs the `requests` package. It was not in requirements.txt, so in
    production every push would have failed as soon as it was configured."""
    from google.auth.transport.requests import Request  # noqa: F401


@pytest.mark.parametrize("in_app, push", [(True, True), (False, True), (True, False)])
def test_chat_push_independiente_de_presencia_y_campana(
    sin_websocket, db_session, test_user, otro_usuario, test_entity, in_app, push
):
    db_session.add(NotificationPreference(user_id=test_user.id, event_type="chat_message_received",
                                          in_app_enabled=in_app, push_enabled=push))
    db_session.commit()
    with patch("app.services.notification_service.notification_manager.is_online", return_value=True), \
         patch("app.services.push_service.send_to_user") as send:
        notifications = NotificationService(db_session).notify(
            EventType.CHAT_MESSAGE_RECEIVED, test_entity.id, otro_usuario, "chat", 17,
            recipient_ids=[otro_usuario.id, test_user.id],
        )
    assert bool(notifications) == in_app
    assert send.call_count == int(push)
    if push:
        assert send.call_args.args[1] == test_user.id
        assert send.call_args.kwargs["data"]["resource_id"] == 17
