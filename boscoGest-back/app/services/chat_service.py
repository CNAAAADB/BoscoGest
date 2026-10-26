import uuid
from typing import List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.chat_model import (
    ChatConversation,
    ChatJoinRequest,
    ChatMember,
    ChatMessage,
)
from app.models.user_model import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ConversationDetail,
    ConversationListItem,
    GroupUpdate,
    JoinRequestResponse,
    LastMessageBrief,
    MemberResponse,
    MessageResponse,
    ReplyBrief,
    UserBrief,
    UserPresence,
    UserSearchResult,
)
from app.services.chat_manager import chat_manager
from app.services.notification_service import EventType, NotificationService
from app.services.storage import get_storage_service
from app.utils.auth import get_sync_db


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatRepository(db)

    # ── Conversations ─────────────────────────────────────────────────

    def get_conversations(self, current_user: User) -> List[ConversationListItem]:
        convs = self.repo.get_user_conversations(current_user.id)
        result = []
        for conv in convs:
            item = self._to_list_item(conv, current_user.id)
            result.append(item)
        # Pinned first; within each group preserve repo's updated_at desc order
        result.sort(key=lambda c: (0 if c.is_pinned else 1))
        return result

    def get_conversation_detail(
        self, conversation_id: int, current_user: User
    ) -> ConversationDetail:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        my_member = self.repo.get_member(conversation_id, current_user.id)
        member_count = self.repo.count_active_members(conversation_id)
        return ConversationDetail(
            id=conv.id,
            type=conv.type,
            name=conv.name,
            description=conv.description,
            avatar_url=conv.avatar_url,
            created_by_id=conv.created_by_id,
            created_at=conv.created_at,
            my_role=my_member.role if my_member else None,
            member_count=member_count,
        )

    def get_or_create_direct(
        self, current_user: User, target_user_id: int
    ) -> ConversationListItem:
        if target_user_id == current_user.id:
            raise HTTPException(400, "No puedes iniciar un chat contigo mismo")

        existing = self.repo.find_direct_conversation(current_user.id, target_user_id)
        if existing:
            return self._to_list_item(existing, current_user.id)

        conv = self.repo.create_conversation("direct", current_user.id)
        self.repo.add_member(conv.id, current_user.id, "member")
        self.repo.add_member(conv.id, target_user_id, "member")
        self.db.commit()
        return self._to_list_item(self.repo.get_conversation(conv.id), current_user.id)

    def create_group(
        self, current_user: User, name: str, description: Optional[str]
    ) -> ConversationListItem:
        if not name or not name.strip():
            raise HTTPException(400, "El nombre del grupo es obligatorio")

        conv = self.repo.create_conversation(
            "group", current_user.id, name.strip(), description
        )
        self.repo.add_member(conv.id, current_user.id, "admin")
        self.db.commit()
        return self._to_list_item(self.repo.get_conversation(conv.id), current_user.id)

    def update_group(
        self, conversation_id: int, current_user: User, data: GroupUpdate
    ) -> ConversationDetail:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "Solo se pueden editar grupos")
        self._assert_group_admin(conversation_id, current_user.id)

        self.repo.update_conversation(conv, data.name, data.description)
        self.db.commit()
        return self.get_conversation_detail(conversation_id, current_user)

    def deactivate_group(self, conversation_id: int, current_user: User) -> None:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "Solo se pueden desactivar grupos")
        self._assert_group_admin(conversation_id, current_user.id)

        self.repo.deactivate_conversation(conv)
        self.db.commit()

    def upload_group_avatar(
        self, conversation_id: int, current_user: User, data: bytes, content_type: str
    ) -> ConversationDetail:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "Solo los grupos tienen avatar")
        self._assert_group_admin(conversation_id, current_user.id)

        ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
        key = f"chat/avatars/{conversation_id}/{uuid.uuid4().hex}.{ext}"
        storage = get_storage_service()
        storage.upload(key, data, content_type)
        url = storage.get_presigned_url(key, expires_in=86400 * 365)

        self.repo.update_conversation_avatar(conv, url)
        self.db.commit()
        return self.get_conversation_detail(conversation_id, current_user)

    # ── Mute / Pin ────────────────────────────────────────────────────

    def set_muted(
        self, conversation_id: int, current_user: User, is_muted: bool
    ) -> None:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        member = self.repo.get_member(conversation_id, current_user.id)
        self.repo.update_member_muted(member, is_muted)
        self.db.commit()

    def set_pinned(
        self, conversation_id: int, current_user: User, is_pinned: bool
    ) -> None:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        member = self.repo.get_member(conversation_id, current_user.id)
        self.repo.update_member_pinned(member, is_pinned)
        self.db.commit()

    # ── Messages ──────────────────────────────────────────────────────

    def get_messages(
        self,
        conversation_id: int,
        current_user: User,
        before_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[MessageResponse]:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        messages = self.repo.get_messages(conversation_id, before_id=before_id, limit=limit)
        self.repo.update_last_read(conversation_id, current_user.id)
        self.db.commit()
        return [self._to_message_response(m) for m in messages]

    def search_messages(
        self, conversation_id: int, current_user: User, query: str
    ) -> List[MessageResponse]:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        if not query or len(query.strip()) < 2:
            return []
        messages = self.repo.search_messages(conversation_id, query.strip())
        return [self._to_message_response(m) for m in messages]

    def send_message(
        self,
        conversation_id: int,
        current_user: User,
        content: str,
        reply_to_id: Optional[int] = None,
    ) -> MessageResponse:
        self._get_conv_and_assert_member(conversation_id, current_user.id)

        if not content or not content.strip():
            raise HTTPException(400, "El mensaje no puede estar vacío")

        # Build reply preview if replying
        reply_preview = None
        if reply_to_id:
            original = self.repo.get_message(reply_to_id)
            if original and not original.is_deleted:
                reply_preview = original.content[:100]
            else:
                reply_to_id = None

        msg = self.repo.save_message(
            conversation_id,
            current_user.id,
            content.strip(),
            reply_to_id=reply_to_id,
            reply_preview=reply_preview,
        )
        self.repo.update_last_read(conversation_id, current_user.id)
        self.repo.touch_updated_at(conversation_id)
        self.db.commit()

        # Re-fetch to load relationships
        msg = self.repo.get_message(msg.id)
        self._dispatch_new_message(msg, current_user)
        return self._to_message_response(msg)

    def send_file_message(
        self,
        conversation_id: int,
        current_user: User,
        file_data: bytes,
        file_name: str,
        file_mime: str,
        reply_to_id: Optional[int] = None,
    ) -> MessageResponse:
        self._get_conv_and_assert_member(conversation_id, current_user.id)

        # Upload file
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
        key = f"chat/files/{conversation_id}/{uuid.uuid4().hex}.{ext}"
        storage = get_storage_service()
        storage.upload(key, file_data, file_mime)
        file_url = storage.get_presigned_url(key, expires_in=86400 * 30, filename=file_name)

        # Reply preview
        reply_preview = None
        if reply_to_id:
            original = self.repo.get_message(reply_to_id)
            if original and not original.is_deleted:
                reply_preview = original.content[:100]
            else:
                reply_to_id = None

        msg = self.repo.save_message(
            conversation_id,
            current_user.id,
            file_name,
            message_type="file",
            reply_to_id=reply_to_id,
            reply_preview=reply_preview,
            file_url=file_url,
            file_name=file_name,
            file_type=file_mime,
        )
        self.repo.update_last_read(conversation_id, current_user.id)
        self.repo.touch_updated_at(conversation_id)
        self.db.commit()

        msg = self.repo.get_message(msg.id)
        self._dispatch_new_message(msg, current_user)
        return self._to_message_response(msg)

    def delete_message(self, message_id: int, current_user: User) -> None:
        msg = self.repo.get_message(message_id)
        if not msg:
            raise HTTPException(404, "Mensaje no encontrado")
        if msg.sender_id != current_user.id:
            raise HTTPException(403, "Solo puedes borrar tus propios mensajes")

        self.repo.soft_delete_message(msg)
        self.db.commit()

        members = self.repo.get_members(msg.conversation_id)
        payload = {
            "type": "message_deleted",
            "conversation_id": msg.conversation_id,
            "message_id": message_id,
        }
        for member in members:
            if member.user_id != current_user.id:
                chat_manager.enqueue(member.user_id, payload)

    # ── Members ───────────────────────────────────────────────────────

    def get_members(
        self, conversation_id: int, current_user: User
    ) -> List[MemberResponse]:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        members = self.repo.get_members(conversation_id)
        result = []
        for m in members:
            resp = MemberResponse.model_validate(m)
            resp.is_online = chat_manager.is_online(m.user_id)
            result.append(resp)
        return result

    def add_member(
        self, conversation_id: int, current_user: User, target_user_id: int
    ) -> MemberResponse:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "No se pueden añadir miembros a conversaciones directas")
        self._assert_group_admin(conversation_id, current_user.id)

        existing = self.repo.get_member(conversation_id, target_user_id)
        if existing:
            raise HTTPException(409, "El usuario ya es miembro del grupo")

        member = self.repo.add_member(conversation_id, target_user_id)
        self.db.commit()

        # System message
        target_user = self.db.get(User, target_user_id)
        if target_user:
            self._send_system_message(
                conversation_id,
                f"{target_user.name} {target_user.surname} se unió al grupo",
                current_user,
            )

        chat_manager.enqueue(
            target_user_id,
            {"type": "added_to_group", "conversation_id": conversation_id},
        )
        resp = MemberResponse.model_validate(member)
        resp.is_online = chat_manager.is_online(target_user_id)
        return resp

    def leave_group(self, conversation_id: int, current_user: User) -> None:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "No puedes abandonar una conversación directa")

        member = self.repo.get_member(conversation_id, current_user.id)
        if not member:
            raise HTTPException(404, "No eres miembro de este grupo")

        is_admin = member.role == "admin"
        self.repo.remove_member(member)

        if is_admin:
            replacement = self.repo.get_oldest_admin(conversation_id, current_user.id)
            if replacement:
                self.repo.update_member_role(replacement, "admin")

        self.db.commit()

        self._send_system_message(
            conversation_id,
            f"{current_user.name} {current_user.surname} abandonó el grupo",
            current_user,
        )

    def remove_member(
        self, conversation_id: int, current_user: User, target_user_id: int
    ) -> None:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "No se pueden expulsar miembros de conversaciones directas")
        self._assert_group_admin(conversation_id, current_user.id)

        if target_user_id == current_user.id:
            raise HTTPException(400, "Usa 'abandonar grupo' para salir tú mismo")

        member = self.repo.get_member(conversation_id, target_user_id)
        if not member:
            raise HTTPException(404, "El usuario no es miembro de este grupo")

        target_name = f"{member.user.name} {member.user.surname}"
        self.repo.remove_member(member)
        self.db.commit()

        self._send_system_message(
            conversation_id,
            f"{target_name} fue expulsado del grupo",
            current_user,
        )

        chat_manager.enqueue(
            target_user_id,
            {"type": "removed_from_group", "conversation_id": conversation_id},
        )

    def update_member_role(
        self,
        conversation_id: int,
        current_user: User,
        target_user_id: int,
        role: str,
    ) -> MemberResponse:
        conv = self._get_conv_and_assert_member(conversation_id, current_user.id)
        if conv.type != "group":
            raise HTTPException(400, "Los roles de miembro solo aplican a grupos")
        self._assert_group_admin(conversation_id, current_user.id)

        member = self.repo.get_member(conversation_id, target_user_id)
        if not member:
            raise HTTPException(404, "El usuario no es miembro de este grupo")

        member = self.repo.update_member_role(member, role)
        self.db.commit()
        resp = MemberResponse.model_validate(member)
        resp.is_online = chat_manager.is_online(target_user_id)
        return resp

    # ── Join Requests ─────────────────────────────────────────────────

    def get_join_requests(
        self, conversation_id: int, current_user: User
    ) -> List[JoinRequestResponse]:
        conv = self.repo.get_conversation(conversation_id)
        if not conv or conv.type != "group":
            raise HTTPException(404, "Grupo no encontrado")
        self._assert_group_admin(conversation_id, current_user.id)

        requests = self.repo.get_pending_requests(conversation_id)
        return [JoinRequestResponse.model_validate(r) for r in requests]

    def create_join_request(
        self, conversation_id: int, current_user: User
    ) -> JoinRequestResponse:
        conv = self.repo.get_conversation(conversation_id)
        if not conv or conv.type != "group":
            raise HTTPException(404, "Grupo no encontrado")

        if self.repo.get_member(conversation_id, current_user.id):
            raise HTTPException(409, "Ya eres miembro de este grupo")

        if self.repo.get_pending_request_for_user(conversation_id, current_user.id):
            raise HTTPException(409, "Ya tienes una solicitud pendiente para este grupo")

        req = self.repo.create_join_request(conversation_id, current_user.id)
        self.db.commit()

        members = self.repo.get_members(conversation_id)
        for m in members:
            if m.role == "admin":
                chat_manager.enqueue(
                    m.user_id,
                    {
                        "type": "join_request",
                        "conversation_id": conversation_id,
                        "user": {
                            "id": current_user.id,
                            "name": current_user.name,
                            "surname": current_user.surname,
                        },
                    },
                )
        return JoinRequestResponse.model_validate(req)

    def review_join_request(
        self,
        conversation_id: int,
        request_id: int,
        current_user: User,
        status: str,
    ) -> JoinRequestResponse:
        conv = self.repo.get_conversation(conversation_id)
        if not conv or conv.type != "group":
            raise HTTPException(404, "Grupo no encontrado")
        self._assert_group_admin(conversation_id, current_user.id)

        req = self.repo.get_join_request(request_id)
        if not req or req.conversation_id != conversation_id:
            raise HTTPException(404, "Solicitud no encontrada")
        if req.status != "pending":
            raise HTTPException(409, "La solicitud ya fue revisada")

        req = self.repo.review_join_request(req, status, current_user.id)

        if status == "accepted":
            self.repo.add_member(conversation_id, req.user_id)
            self.db.commit()
            # System message
            self._send_system_message(
                conversation_id,
                f"{req.user.name} {req.user.surname} se unió al grupo",
                current_user,
            )
        else:
            self.db.commit()

        chat_manager.enqueue(
            req.user_id,
            {
                "type": f"join_request_{status}",
                "conversation_id": conversation_id,
            },
        )
        return JoinRequestResponse.model_validate(req)

    # ── User search ───────────────────────────────────────────────────

    def search_users(
        self, query: str, current_user: User, entity_id: Optional[int] = None
    ) -> List[UserSearchResult]:
        if not query or len(query.strip()) < 2:
            return []
        # If filtering by association, ensure the user can access that entity.
        if entity_id is not None:
            from app.services.authorization_service import AuthorizationService
            accessible = AuthorizationService(self.db).get_accessible_entity_ids(
                current_user
            )
            if entity_id not in accessible:
                return []
        users = self.repo.search_users(
            query.strip(), current_user.id, entity_id=entity_id
        )
        return [UserSearchResult.model_validate(u) for u in users]

    # ── Presence ──────────────────────────────────────────────────────

    def get_presence(
        self, conversation_id: int, current_user: User
    ) -> List[UserPresence]:
        self._get_conv_and_assert_member(conversation_id, current_user.id)
        members = self.repo.get_members(conversation_id)
        return [
            UserPresence(user_id=m.user_id, is_online=chat_manager.is_online(m.user_id))
            for m in members
        ]

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_conv_and_assert_member(
        self, conversation_id: int, user_id: int
    ) -> ChatConversation:
        conv = self.repo.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(404, "Conversación no encontrada")
        member = self.repo.get_member(conversation_id, user_id)
        if not member:
            raise HTTPException(403, "No eres miembro de esta conversación")
        return conv

    def _assert_group_admin(self, conversation_id: int, user_id: int) -> None:
        member = self.repo.get_member(conversation_id, user_id)
        if not member or member.role != "admin":
            raise HTTPException(403, "Solo los administradores del grupo pueden realizar esta acción")

    def _send_system_message(
        self, conversation_id: int, text: str, actor: User
    ) -> None:
        """Save a system message and broadcast it to all members."""
        msg = self.repo.save_message(
            conversation_id,
            sender_id=None,
            content=text,
            message_type="system",
        )
        self.repo.touch_updated_at(conversation_id)
        self.db.commit()

        payload = {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": {
                "id": msg.id,
                "conversation_id": conversation_id,
                "sender_id": None,
                "sender": None,
                "content": text,
                "message_type": "system",
                "reply_to": None,
                "file_url": None,
                "file_name": None,
                "file_type": None,
                "is_deleted": False,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            },
        }
        members = self.repo.get_members(conversation_id)
        for m in members:
            chat_manager.enqueue(m.user_id, payload)

    def _dispatch_new_message(self, msg: ChatMessage, sender: User) -> None:
        """Broadcast a new message to all other members and send in-app notifications."""
        members = self.repo.get_members(msg.conversation_id)
        reply_to_data = None
        if msg.reply_to_id and msg.reply_to:
            reply_to_data = {
                "id": msg.reply_to.id,
                "sender": (
                    {
                        "id": msg.reply_to.sender.id,
                        "name": msg.reply_to.sender.name,
                        "surname": msg.reply_to.sender.surname,
                    }
                    if msg.reply_to.sender
                    else None
                ),
                "preview": msg.reply_preview or "",
            }

        payload = {
            "type": "new_message",
            "conversation_id": msg.conversation_id,
            "message": {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_id": sender.id,
                "sender": {
                    "id": sender.id,
                    "name": sender.name,
                    "surname": sender.surname,
                },
                "content": msg.content,
                "message_type": msg.message_type,
                "reply_to": reply_to_data,
                "file_url": msg.file_url,
                "file_name": msg.file_name,
                "file_type": msg.file_type,
                "is_deleted": False,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            },
        }

        # Notify recipients that are NOT connected to chat WS
        try:
            notification_service = NotificationService(self.db)
            offline_ids = [
                m.user_id
                for m in members
                if m.user_id != sender.id and not chat_manager.is_online(m.user_id)
                and not m.is_muted
            ]
            if offline_ids:
                conv = self.repo.get_conversation(msg.conversation_id)
                conv_name = conv.name if conv and conv.type == "group" else f"{sender.name} {sender.surname}"
                active_membership = next(
                    (m for m in sender.memberships if m.is_active), None
                )
                if not active_membership:
                    return
                notification_service.notify(
                    event_type=EventType.CHAT_MESSAGE_RECEIVED,
                    entity_id=active_membership.entity_id,
                    actor=sender,
                    resource_type="chat",
                    resource_id=msg.conversation_id,
                    title=f"Nuevo mensaje de {sender.name}",
                    body=f"{conv_name}: {msg.content[:80]}",
                    recipient_ids=offline_ids,
                )
        except Exception:
            pass  # Never block message delivery due to notification failure

        for member in members:
            if member.user_id != sender.id:
                chat_manager.enqueue(member.user_id, payload)

    def _to_list_item(
        self, conv: ChatConversation, current_user_id: int
    ) -> ConversationListItem:
        messages = self.repo.get_messages(conv.id, limit=1)
        last_msg = None
        if messages:
            m = messages[-1]
            last_msg = LastMessageBrief(
                id=m.id,
                content=m.content if not m.is_deleted else "",
                sender=UserBrief.model_validate(m.sender) if m.sender else None,
                created_at=m.created_at,
                is_deleted=m.is_deleted,
                message_type=m.message_type,
            )

        unread = self.repo.count_unread(conv.id, current_user_id)
        my_member = self.repo.get_member(conv.id, current_user_id)

        other_user = None
        if conv.type == "direct":
            for m in self.repo.get_members(conv.id):
                if m.user_id != current_user_id:
                    other_user = UserBrief.model_validate(m.user)
                    break

        return ConversationListItem(
            id=conv.id,
            type=conv.type,
            name=conv.name if conv.type == "group" else (
                f"{other_user.name} {other_user.surname}" if other_user else "Conversación"
            ),
            created_by_id=conv.created_by_id,
            is_active=conv.is_active,
            created_at=conv.created_at,
            other_user=other_user,
            last_message=last_msg,
            unread_count=unread,
            my_role=my_member.role if my_member else None,
            is_muted=my_member.is_muted if my_member else False,
            is_pinned=my_member.is_pinned if my_member else False,
        )

    def _to_message_response(self, msg: ChatMessage) -> MessageResponse:
        reply_to = None
        if msg.reply_to_id and msg.reply_to and not msg.reply_to.is_deleted:
            reply_to = ReplyBrief(
                id=msg.reply_to.id,
                sender=UserBrief.model_validate(msg.reply_to.sender) if msg.reply_to.sender else None,
                preview=msg.reply_preview or msg.reply_to.content[:100],
            )

        return MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            sender=UserBrief.model_validate(msg.sender) if msg.sender else None,
            content=msg.content if not msg.is_deleted else "",
            message_type=msg.message_type,
            reply_to=reply_to,
            file_url=msg.file_url,
            file_name=msg.file_name,
            file_type=msg.file_type,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
        )


def get_chat_service(db: Session = Depends(get_sync_db)) -> ChatService:
    return ChatService(db)
