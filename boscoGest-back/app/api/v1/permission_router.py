from fastapi import APIRouter, Depends, Request, Response, status
from typing import List
from app.models.user_model import User
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionResponse
from app.utils.auth import require_permission, require_root_permission
from app.services.permission_service import PermissionService, get_permission_service

permission_router = APIRouter(prefix="/permissions", tags=["Permission Management"])


@permission_router.post(
    "", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED
)
def create_permission(
    permission: PermissionCreate,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_root_permission("permissions", "create")),
):
    return service.create_permission(
        permission, current_user, ip_address=request.client.host if request else None
    )


@permission_router.get("", response_model=List[PermissionResponse])
def get_permissions(
    skip: int = 0,
    limit: int = 100,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_permission("permissions", "list")),
):
    return service.list_permissions(skip=skip, limit=limit)


@permission_router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: int,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_permission("permissions", "read")),
):
    return service.get_permission(permission_id)


@permission_router.put("/{permission_id}", response_model=PermissionResponse)
def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_root_permission("permissions", "update")),
):
    return service.update_permission(
        permission_id,
        permission_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@permission_router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    permission_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_root_permission("permissions", "delete")),
):
    service.delete_permission(
        permission_id, current_user, ip_address=request.client.host if request else None
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@permission_router.post(
    "/{permission_id}/assign-to-role/{role_id}", status_code=status.HTTP_200_OK
)
def assign_permission_to_role(
    permission_id: int,
    role_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(require_root_permission("permissions", "assign")),
):
    return service.assign_to_role(
        permission_id,
        role_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
