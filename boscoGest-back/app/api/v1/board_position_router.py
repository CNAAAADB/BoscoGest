"""Entity-scoped governing-board labels for users.

Labels describe offices, NOT application permissions. Only national and
federal administrators can assign or revoke them, and solely for memberships
inside their jurisdiction.
"""
import unicodedata
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log_model import AuditLog
from app.models.board_position_model import BoardPosition
from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.user_model import User
from app.repositories.entity_repository import EntityRepository
from app.services.authorization_service import AuthorizationService
from app.utils.auth import get_current_active_user, get_sync_db

board_position_router = APIRouter(prefix="/board-positions", tags=["Board positions"])

RoleCode = Literal[
    "presidente", "secretario", "tesorero", "vicepresidente",
    "coordinador_joven", "otro",
]
ROLE_LABELS = {
    "presidente": "Presidente",
    "secretario": "Secretario",
    "tesorero": "Tesorero",
    "vicepresidente": "Vicepresidente",
    "coordinador_joven": "Coordinador joven",
}


class PositionCreate(BaseModel):
    entity_id: int = Field(gt=0)
    role_code: RoleCode
    custom_title: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def clean_title(self):
        title = " ".join((self.custom_title or "").split())
        if self.role_code == "otro":
            if not (2 <= len(title) <= 80) or any(ord(c) < 32 for c in title):
                raise ValueError("El cargo personalizado debe tener entre 2 y 80 caracteres")
            self.custom_title = title
        elif title:
            raise ValueError("El título personalizado solo se admite en «Otro»")
        else:
            self.custom_title = None
        return self


def _normalize(payload: PositionCreate) -> str:
    value = payload.custom_title if payload.role_code == "otro" else payload.role_code
    folded = unicodedata.normalize("NFKC", value).casefold()
    return f"otro:{folded}" if payload.role_code == "otro" else folded


def _administrator_scope(actor: User, target_entity: Entity, auth: AuthorizationService) -> bool:
    """Explicitly require a national (1) or federal (3) active membership.

    Local users:manage does NOT grant authority to issue board appointments.
    A federal admin can affect only its own federation and descendants.
    """
    if not target_entity.is_active or target_entity.level < 2:
        return False
    for membership in actor.memberships:
        if not membership.is_active or membership.entity is None:
            continue
        if membership.entity.level not in (1, 3):
            continue
        # Permission must come from THIS national/federal appointment, not
        # from an unrelated local admin membership combined with an automatic
        # 'socio' membership at the root.
        if not membership.role or not any(
            p.resource == "users" and p.action in ("manage", "manage_all")
            for p in membership.role.permissions
        ):
            continue
        own_entity = membership.entity_id
        if target_entity.id != own_entity and target_entity.id not in auth.entity_repo.get_descendant_ids(own_entity):
            continue
        if auth.has_effective_permission(actor, target_entity.id, "users", "manage"):
            return True
    return False


def _get_member(db: Session, user_id: int) -> User:
    member = db.get(User, user_id)
    if not member or not member.is_active:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return member


def _active_associations(db: Session, user_id: int) -> list[Entity]:
    return list(db.scalars(
        select(Entity).join(Membership, Membership.entity_id == Entity.id)
        .where(Membership.user_id == user_id, Membership.is_active.is_(True),
               Entity.is_active.is_(True))
        .order_by(Entity.level, Entity.name)
    ).all())


def _serialize(position: BoardPosition, entity: Entity, member: User) -> dict:
    return {
        "id": position.id,
        "user_id": member.id,
        "user_name": member.name,
        "user_surname": member.surname,
        "entity_id": entity.id,
        "entity_name": entity.name,
        "entity_level": entity.level,
        "role_code": position.role_code,
        "custom_title": position.custom_title,
        "title": position.custom_title or ROLE_LABELS[position.role_code],
        "created_at": position.created_at,
    }


def _visible_positions(db: Session, actor: User, member: User):
    auth = AuthorizationService(db)
    if actor.id != member.id and not auth.can_reach_user(actor, member, "read"):
        raise HTTPException(status_code=403, detail="Sin acceso a este usuario")
    query = select(BoardPosition, Entity).join(
        Entity, Entity.id == BoardPosition.entity_id
    ).where(BoardPosition.user_id == member.id).order_by(
        Entity.level, Entity.name, BoardPosition.role_code, BoardPosition.id
    )
    rows = db.execute(query).all()
    if actor.id == member.id:
        return rows
    return [(pos, entity) for pos, entity in rows if _administrator_scope(actor, entity, auth)]


@board_position_router.get("/roles")
def available_board_roles(current_user: User = Depends(get_current_active_user)):
    return [{"code": code, "label": label} for code, label in
            [*ROLE_LABELS.items(), ("otro", "Otro (personalizado)")]]


@board_position_router.get("/users/{user_id}/available-entities")
def available_position_entities(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    member = _get_member(db, user_id)
    auth = AuthorizationService(db)
    entities = [e for e in _active_associations(db, member.id)
                if _administrator_scope(current_user, e, auth)]
    return [{"id": e.id, "name": e.name, "level": e.level} for e in entities]


@board_position_router.get("/users/{user_id}")
def list_board_positions(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    member = _get_member(db, user_id)
    return [_serialize(pos, entity, member)
            for pos, entity in _visible_positions(db, current_user, member)]


@board_position_router.post("/users/{user_id}", status_code=status.HTTP_201_CREATED)
def add_board_position(
    user_id: int,
    payload: PositionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    member = _get_member(db, user_id)
    entity = db.get(Entity, payload.entity_id)
    if entity is None or not entity.is_active:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    auth = AuthorizationService(db)
    if not _administrator_scope(current_user, entity, auth):
        raise HTTPException(status_code=403, detail="Solo administración nacional o federal competente")
    if not db.scalar(select(Membership.id).where(
        Membership.user_id == member.id,
        Membership.entity_id == entity.id,
        Membership.is_active.is_(True),
    )):
        raise HTTPException(status_code=422, detail="El usuario no tiene una membresía activa en esa entidad")
    position = BoardPosition(
        user_id=member.id, entity_id=entity.id, role_code=payload.role_code,
        custom_title=payload.custom_title, normalized_title=_normalize(payload),
        created_by_id=current_user.id,
    )
    db.add(position)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este cargo ya está asignado en esta entidad")
    db.add(AuditLog(
        user_id=current_user.id, action="create", resource_type="board_positions",
        resource_id=position.id,
        ip_address=request.client.host if request.client else None,
        details={"target_user_id": member.id, "entity_id": entity.id,
                 "title": position.custom_title or ROLE_LABELS[position.role_code]},
    ))
    db.commit()
    db.refresh(position)
    return _serialize(position, entity, member)


@board_position_router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_board_position(
    position_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    position = db.get(BoardPosition, position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")
    entity = db.get(Entity, position.entity_id)
    if entity is None or not _administrator_scope(current_user, entity, AuthorizationService(db)):
        raise HTTPException(status_code=403, detail="Sin permisos para retirar este cargo")
    db.add(AuditLog(
        user_id=current_user.id, action="delete", resource_type="board_positions",
        resource_id=position.id,
        ip_address=request.client.host if request.client else None,
        details={"target_user_id": position.user_id, "entity_id": position.entity_id,
                 "title": position.custom_title or ROLE_LABELS[position.role_code]},
    ))
    db.delete(position)
    db.commit()


@board_position_router.get("/organigram/{entity_id}")
def organigram_positions(
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    """Flat, structured input for a future hierarchical board visualisation."""
    entity = db.get(Entity, entity_id)
    auth = AuthorizationService(db)
    if entity is None or not _administrator_scope(current_user, entity, auth):
        raise HTTPException(status_code=403, detail="Sin acceso al organigrama de la entidad")
    scoped = [entity.id, *EntityRepository(db).get_descendant_ids(entity.id)]
    rows = db.execute(
        select(BoardPosition, Entity, User)
        .join(Entity, Entity.id == BoardPosition.entity_id)
        .join(User, User.id == BoardPosition.user_id)
        .join(Membership, (Membership.user_id == User.id) &
              (Membership.entity_id == BoardPosition.entity_id))
        .where(BoardPosition.entity_id.in_(scoped),
               Entity.is_active.is_(True), User.is_active.is_(True),
               Membership.is_active.is_(True))
        .order_by(Entity.level, Entity.name, BoardPosition.role_code)
    ).all()
    return [_serialize(p, e, u) for p, e, u in rows
            if _administrator_scope(current_user, e, auth)]
