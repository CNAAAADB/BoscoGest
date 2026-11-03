from fastapi import APIRouter, Depends, Request, Response, status
from typing import List
from app.models.user_model import User
from app.schemas.group import GroupCreate, GroupResponse
from app.utils.auth import require_root_permission
from app.services.group_service import GroupService, get_group_service

group_router = APIRouter(prefix="/groups", tags=["Group Management"])


@group_router.post(
    "", response_model=GroupResponse, status_code=status.HTTP_201_CREATED
)
def create_group(
    group: GroupCreate,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "create")),
):
    return service.create_group(
        group, current_user, ip_address=request.client.host if request else None
    )


@group_router.get("", response_model=List[GroupResponse])
def get_groups(
    skip: int = 0,
    limit: int = 100,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "list")),
):
    return service.list_groups(skip=skip, limit=limit)


@group_router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "read")),
):
    return service.get_group(group_id)


@group_router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_update: GroupCreate,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "update")),
):
    return service.update_group(
        group_id,
        group_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@group_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "delete")),
):
    service.delete_group(
        group_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@group_router.post(
    "/{group_id}/add-user/{user_id}", status_code=status.HTTP_200_OK
)
def add_user_to_group(
    group_id: int,
    user_id: int,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "assign")),
):
    return service.add_user_to_group(
        group_id,
        user_id,
        current_user,
        ip_address=request.client.host if request else None,
    )


@group_router.post(
    "/{group_id}/remove-user/{user_id}", status_code=status.HTTP_200_OK
)
def remove_user_from_group(
    group_id: int,
    user_id: int,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "assign")),
):
    return service.remove_user_from_group(
        group_id,
        user_id,
        current_user,
        ip_address=request.client.host if request else None,
    )


@group_router.post(
    "/{group_id}/assign-role/{role_id}", status_code=status.HTTP_200_OK
)
def assign_role_to_group(
    group_id: int,
    role_id: int,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "assign")),
):
    return service.assign_role_to_group(
        group_id,
        role_id,
        current_user,
        ip_address=request.client.host if request else None,
    )


@group_router.post(
    "/{group_id}/remove-role/{role_id}", status_code=status.HTTP_200_OK
)
def remove_role_from_group(
    group_id: int,
    role_id: int,
    request: Request,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(require_root_permission("groups", "assign")),
):
    return service.remove_role_from_group(
        group_id,
        role_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
