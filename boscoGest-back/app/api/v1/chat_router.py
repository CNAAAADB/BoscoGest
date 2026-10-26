import json
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
)
from typing import List, Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user_model import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    DirectConversationRequest,
    GroupUpdate,
    JoinRequestResponse,
    JoinRequestReview,
    MemberResponse,
    MemberRoleUpdate,
    MessageCreate,
    MessageResponse,
    UserPresence,
    UserSearchResult,
)
from app.services.chat_service import ChatService, get_chat_service
from app.services.chat_manager import chat_manager
from app.utils.auth import get_current_active_user, get_sync_db, SECRET_KEY, ALGORITHM

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Conversations ─────────────────────────────────────────────────────


@chat_router.get("/conversations", response_model=List[ConversationListItem])
def list_conversations(
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_conversations(current_user)


@chat_router.post("/conversations/direct", response_model=ConversationListItem)
def get_or_create_direct(
    body: DirectConversationRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_or_create_direct(current_user, body.target_user_id)


@chat_router.post("/conversations/group", response_model=ConversationListItem)
def create_group(
    body: ConversationCreate,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_group(current_user, body.name, body.description)


@chat_router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_conversation_detail(conversation_id, current_user)


@chat_router.put("/conversations/{conversation_id}", response_model=ConversationDetail)
def update_group(
    conversation_id: int,
    body: GroupUpdate,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_group(conversation_id, current_user, body)


@chat_router.delete("/conversations/{conversation_id}", status_code=204)
def deactivate_group(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.deactivate_group(conversation_id, current_user)


@chat_router.post(
    "/conversations/{conversation_id}/avatar",
    response_model=ConversationDetail,
)
async def upload_group_avatar(
    conversation_id: int,
    file: UploadFile = File(...),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "El archivo supera el límite de 5 MB")
    return service.upload_group_avatar(
        conversation_id, current_user, data, file.content_type or "image/jpeg"
    )


# ── Mute / Pin ────────────────────────────────────────────────────────


@chat_router.put("/conversations/{conversation_id}/mute", status_code=204)
def mute_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.set_muted(conversation_id, current_user, True)


@chat_router.delete("/conversations/{conversation_id}/mute", status_code=204)
def unmute_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.set_muted(conversation_id, current_user, False)


@chat_router.put("/conversations/{conversation_id}/pin", status_code=204)
def pin_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.set_pinned(conversation_id, current_user, True)


@chat_router.delete("/conversations/{conversation_id}/pin", status_code=204)
def unpin_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.set_pinned(conversation_id, current_user, False)


# ── Messages ──────────────────────────────────────────────────────────


@chat_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
)
def get_messages(
    conversation_id: int,
    before_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=100),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_messages(conversation_id, current_user, before_id, limit)


@chat_router.get(
    "/conversations/{conversation_id}/messages/search",
    response_model=List[MessageResponse],
)
def search_messages(
    conversation_id: int,
    q: str = Query(default="", min_length=2),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.search_messages(conversation_id, current_user, q)


@chat_router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
def send_message(
    conversation_id: int,
    body: MessageCreate,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.send_message(
        conversation_id, current_user, body.content, body.reply_to_id
    )


@chat_router.post(
    "/conversations/{conversation_id}/messages/files",
    response_model=MessageResponse,
)
async def send_file_message(
    conversation_id: int,
    file: UploadFile = File(...),
    reply_to_id: Optional[int] = Query(default=None),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "El archivo supera el límite de 20 MB")
    return service.send_file_message(
        conversation_id,
        current_user,
        data,
        file.filename or "archivo",
        file.content_type or "application/octet-stream",
        reply_to_id,
    )


@chat_router.delete("/messages/{message_id}", status_code=204)
def delete_message(
    message_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_message(message_id, current_user)


# ── Members ───────────────────────────────────────────────────────────


@chat_router.get(
    "/conversations/{conversation_id}/members",
    response_model=List[MemberResponse],
)
def get_members(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_members(conversation_id, current_user)


@chat_router.get(
    "/conversations/{conversation_id}/presence",
    response_model=List[UserPresence],
)
def get_presence(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_presence(conversation_id, current_user)


@chat_router.post(
    "/conversations/{conversation_id}/members",
    response_model=MemberResponse,
)
def add_member(
    conversation_id: int,
    body: DirectConversationRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.add_member(conversation_id, current_user, body.target_user_id)


@chat_router.delete("/conversations/{conversation_id}/leave", status_code=204)
def leave_group(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.leave_group(conversation_id, current_user)


@chat_router.delete(
    "/conversations/{conversation_id}/members/{user_id}",
    status_code=204,
)
def remove_member(
    conversation_id: int,
    user_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    service.remove_member(conversation_id, current_user, user_id)


@chat_router.put(
    "/conversations/{conversation_id}/members/{user_id}/role",
    response_model=MemberResponse,
)
def update_member_role(
    conversation_id: int,
    user_id: int,
    body: MemberRoleUpdate,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_member_role(conversation_id, current_user, user_id, body.role)


# ── Join Requests ─────────────────────────────────────────────────────


@chat_router.get(
    "/conversations/{conversation_id}/join-requests",
    response_model=List[JoinRequestResponse],
)
def get_join_requests(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_join_requests(conversation_id, current_user)


@chat_router.post(
    "/conversations/{conversation_id}/join-requests",
    response_model=JoinRequestResponse,
)
def create_join_request(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_join_request(conversation_id, current_user)


@chat_router.put(
    "/conversations/{conversation_id}/join-requests/{request_id}",
    response_model=JoinRequestResponse,
)
def review_join_request(
    conversation_id: int,
    request_id: int,
    body: JoinRequestReview,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.review_join_request(
        conversation_id, request_id, current_user, body.status
    )


# ── User search ───────────────────────────────────────────────────────


@chat_router.get("/users/search", response_model=List[UserSearchResult])
def search_users(
    q: str = Query(default="", min_length=2),
    entity_id: Optional[int] = Query(default=None),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.search_users(q, current_user, entity_id=entity_id)


# ── WebSocket ─────────────────────────────────────────────────────────


@chat_router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket for real-time chat.

    Client → Server messages:
      "ping"                                          → server replies "pong"
      {"type": "typing", "conversation_id": N}        → forwarded to other members as
            {"type": "typing", "conversation_id": N, "user": {...}}

    Server → Client pushes:
      {"type": "new_message", "conversation_id": N, "message": {...}}
      {"type": "message_deleted", "conversation_id": N, "message_id": N}
      {"type": "typing", "conversation_id": N, "user": {...}}
      {"type": "added_to_group" | "removed_from_group", "conversation_id": N}
      {"type": "join_request", "conversation_id": N, "user": {...}}
      {"type": "join_request_accepted" | "join_request_rejected", "conversation_id": N}
    """
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

    db: Session = next(get_sync_db())
    try:
        user = db.execute(
            select(User).where(User.id == user_sub_id, User.is_active == True)
        ).scalars().first()

        if not user:
            await websocket.close(code=4001)
            return
        user_id = user.id
        user_name = user.name
        user_surname = user.surname
    finally:
        db.close()

    await chat_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue

            try:
                msg = json.loads(data)
            except Exception:
                continue

            if msg.get("type") == "typing":
                conv_id = msg.get("conversation_id")
                if not conv_id:
                    continue
                # Forward typing indicator to all other members of that conversation
                db2: Session = next(get_sync_db())
                try:
                    from app.repositories.chat_repository import ChatRepository
                    repo = ChatRepository(db2)
                    member = repo.get_member(conv_id, user_id)
                    if member:
                        members = repo.get_members(conv_id)
                        typing_payload = {
                            "type": "typing",
                            "conversation_id": conv_id,
                            "user": {
                                "id": user_id,
                                "name": user_name,
                                "surname": user_surname,
                            },
                        }
                        for m in members:
                            if m.user_id != user_id:
                                chat_manager.enqueue(m.user_id, typing_payload)
                finally:
                    db2.close()

    except WebSocketDisconnect:
        chat_manager.disconnect(user_id, websocket)
