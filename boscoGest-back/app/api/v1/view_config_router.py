from fastapi import APIRouter, Depends, Request
from typing import List
from app.models.user_model import User
from app.schemas.entity_view_config import (
    EntityViewConfigUpdate,
    EntityViewConfigBulkUpdate,
    EntityViewConfigResponse,
    EntityViewConfigListResponse,
)
from app.utils.auth import get_current_active_user
from app.services.view_config_service import ViewConfigService, get_view_config_service

view_config_router = APIRouter(
    prefix="/view-configs", tags=["View Configuration"]
)


@view_config_router.get(
    "/entity/{entity_id}", response_model=EntityViewConfigListResponse
)
def get_entity_view_configs(
    entity_id: int,
    service: ViewConfigService = Depends(get_view_config_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entity_view_configs(entity_id, current_user)


@view_config_router.get(
    "/entity/{entity_id}/enabled",
    response_model=List[EntityViewConfigResponse],
)
def get_enabled_views(
    entity_id: int,
    service: ViewConfigService = Depends(get_view_config_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_enabled_views(entity_id, current_user)


@view_config_router.put(
    "/entity/{entity_id}/view/{view_name}",
    response_model=EntityViewConfigResponse,
)
def update_view_config(
    entity_id: int,
    view_name: str,
    config_in: EntityViewConfigUpdate,
    request: Request,
    service: ViewConfigService = Depends(get_view_config_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_view_config(
        entity_id,
        view_name,
        config_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@view_config_router.put(
    "/entity/{entity_id}/bulk", response_model=EntityViewConfigListResponse
)
def bulk_update_view_configs(
    entity_id: int,
    configs_in: EntityViewConfigBulkUpdate,
    request: Request,
    service: ViewConfigService = Depends(get_view_config_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.bulk_update_view_configs(
        entity_id,
        configs_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@view_config_router.post(
    "/entity/{entity_id}/reset", response_model=EntityViewConfigListResponse
)
def reset_view_configs(
    entity_id: int,
    request: Request,
    service: ViewConfigService = Depends(get_view_config_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.reset_view_configs(
        entity_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
