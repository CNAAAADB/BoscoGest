from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from typing import List
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.schemas.notification import (
    DeviceRegistration,
    DeviceResponse,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferencesUpdate,
    UnreadCountResponse,
)
from app.services.notification_service import (
    NotificationService,
    get_notification_service,
    EVENT_TYPE_LABELS,
)
from app.services.notification_manager import notification_manager
from app.utils.auth import (
    get_current_active_user,
    get_sync_db,
    SECRET_KEY,
    ALGORITHM,
)

notification_router = APIRouter(
    prefix="/notifications", tags=["Notifications"]
)


# ── REST endpoints ───────────────────────────────────────────────────


@notification_router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread: bool = False,
    event_type: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_notifications(
        current_user.id,
        unread_only=unread,
        event_type=event_type,
        skip=skip,
        limit=limit,
    )


@notification_router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    return UnreadCountResponse(count=service.get_unread_count(current_user.id))


@notification_router.get("/event-types")
def get_event_types():
    """Return all available event types with labels for the preferences UI."""
    return [
        {"event_type": k, "label": v} for k, v in EVENT_TYPE_LABELS.items()
    ]


# ── Dispositivos para push ───────────────────────────────────────────
#
# Declarados antes que las rutas con "/{notification_id}": FastAPI casa en
# orden de declaración y "/devices" acabaría entrando por ahí, que espera un
# entero y responde 422.


@notification_router.post(
    "/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED
)
def register_device(
    registration: DeviceRegistration,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    """Registra el dispositivo del usuario autenticado para recibir push.

    Se llama en cada arranque de la aplicación, no solo la primera vez: el
    token que emite FCM caduca y se renueva solo, y si no se vuelve a mandar,
    el servidor se queda apuntando a uno que ya no existe.
    """
    return service.register_device(
        current_user.id, registration.token, registration.platform
    )


@notification_router.delete("/devices", status_code=status.HTTP_204_NO_CONTENT)
def unregister_device(
    registration: DeviceRegistration,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    """Da de baja el dispositivo. Se llama al cerrar sesión.

    Sin esto, quien cierre sesión en un móvil compartido seguiría recibiendo
    ahí los avisos de su asociación.
    """
    service.unregister_device(current_user.id, registration.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@notification_router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    if not service.mark_read(notification_id, current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"detail": "Marked as read"}


@notification_router.put("/read-all")
def mark_all_as_read(
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    count = service.mark_all_read(current_user.id)
    return {"detail": f"Marked {count} notifications as read"}


@notification_router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    if not service.delete_notification(notification_id, current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"detail": "Notification deleted"}


# ── Preferences ──────────────────────────────────────────────────────


@notification_router.get(
    "/preferences", response_model=List[NotificationPreferenceResponse]
)
def get_preferences(
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_preferences(current_user.id)


@notification_router.put(
    "/preferences", response_model=List[NotificationPreferenceResponse]
)
def update_preferences(
    body: NotificationPreferencesUpdate,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_preferences(current_user.id, body.preferences)


# ── WebSocket endpoint ───────────────────────────────────────────────


@notification_router.websocket("/ws")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket for real-time notification delivery.
    Connect with: ws://host/notifications/ws?token=<JWT>
    """
    # Validate JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            await websocket.close(code=4001)
            return
        user_sub_id = int(sub)
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001)
        return

    # Resolve user from DB
    db: Session = next(get_sync_db())
    try:
        from sqlalchemy import select

        user = db.execute(
            select(User).where(User.id == user_sub_id, User.is_active == True)
        ).scalars().first()

        if not user:
            await websocket.close(code=4001)
            return

        user_id = user.id
    finally:
        db.close()

    await notification_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)
