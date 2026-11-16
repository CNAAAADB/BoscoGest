from fastapi import APIRouter, Depends, Request, status
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entity_model import Entity
from app.models.user_model import User
from app.schemas.entity import EntityCreate, EntityUpdate, EntityResponse
from app.utils.auth import get_current_active_user, require_permission, get_sync_db
from app.services.entity_service import EntityService, get_entity_service

entity_router = APIRouter(prefix="/entities", tags=["Entity Management"])


@entity_router.get("/public", response_model=List[EntityResponse])
def get_public_entities(
    db: Session = Depends(get_sync_db),
):
    """
    Public endpoint: returns all active non-root entities for the registration form.
    No authentication required.
    """
    stmt = (
        select(Entity)
        .where(Entity.is_active == True, Entity.level > 1)
        .order_by(Entity.level.asc(), Entity.name.asc())
    )
    return list(db.execute(stmt).scalars().all())


@entity_router.get("/associations", response_model=List[EntityResponse])
def get_all_local_associations(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_active_user),
):
    """All active local associations, never federations or higher entities.

    Names and hierarchy are directory metadata; member search permissions
    are enforced independently by each user-search endpoint.
    """
    return list(db.execute(
        select(Entity)
        .where(Entity.is_active == True, Entity.level == 4)
        .order_by(Entity.name, Entity.id)
    ).scalars().all())


@entity_router.get("/accessible", response_model=List[EntityResponse])
def get_accessible_entities(
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    """Entities the authenticated user can access (memberships + descendants)."""
    return service.get_accessible_entities(current_user)


@entity_router.get("/membership-manageable", response_model=List[EntityResponse])
def get_membership_manageable_entities(
    skip: int = 0,
    limit: int = 100,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(require_permission("memberships", "manage")),
):
    return service.get_membership_manageable_entities(
        current_user, skip=skip, limit=limit
    )


@entity_router.get("/admin", response_model=List[EntityResponse])
def get_admin_entities(
    skip: int = 0,
    limit: int = 100,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(require_permission("entities", "list")),
):
    return service.get_admin_entities(current_user, skip=skip, limit=limit)


@entity_router.get("", response_model=List[EntityResponse])
def get_entities(
    skip: int = 0,
    limit: int = 100,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(require_permission("entities", "list")),
):
    return service.get_entities(current_user, skip=skip, limit=limit)


@entity_router.get("/{entity_id}/roles", response_model=List)
def get_entity_roles(
    entity_id: int,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entity_roles(entity_id, current_user)


@entity_router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: int,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entity(entity_id, current_user)


@entity_router.post(
    "", response_model=EntityResponse, status_code=status.HTTP_201_CREATED
)
def create_entity(
    entity_in: EntityCreate,
    request: Request = None,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_entity(
        entity_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@entity_router.put("/{entity_id}", response_model=EntityResponse)
def update_entity(
    entity_id: int,
    entity_in: EntityUpdate,
    request: Request = None,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_entity(
        entity_id,
        entity_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@entity_router.get("/{entity_id}/deletion-impact", status_code=status.HTTP_200_OK)
def get_deletion_impact(
    entity_id: int,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    """What removing this association would affect, so the interface can warn
    before the fact instead of reporting it afterwards."""
    return service.get_deletion_impact(entity_id, current_user)


@entity_router.delete("/{entity_id}", status_code=status.HTTP_200_OK)
def delete_entity(
    entity_id: int,
    request: Request = None,
    service: EntityService = Depends(get_entity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.delete_entity(
        entity_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
