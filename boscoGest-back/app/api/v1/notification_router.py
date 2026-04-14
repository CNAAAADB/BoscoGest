from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.schemas.notification import (
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
        email: str | None = payload.get("sub")
        if email is None:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    # Resolve user from DB
    db: Session = next(get_sync_db())
    try:
        from sqlalchemy import select

        user = db.execute(
            select(User).where(User.email == email, User.is_active == True)
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
