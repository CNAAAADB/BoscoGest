from fastapi import APIRouter, Depends, Request, status
from typing import List
from app.models.user_model import User
from app.models.membership_model import Membership
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleDetails
from app.utils.auth import require_permission, get_current_active_user, get_current_membership
from app.services.role_service import RoleService, get_role_service

role_router = APIRouter(prefix="/roles", tags=["Role Management"])


@role_router.post(
    "", response_model=RoleResponse, status_code=status.HTTP_201_CREATED
)
def create_role(
    role: RoleCreate,
    request: Request = None,
    service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_user),
    current_membership: Membership = Depends(get_current_membership),
):
    return service.create_role(
        role,
        current_user,
        current_membership,
        ip_address=request.client.host if request else None,
    )


@role_router.get("", response_model=List[RoleResponse])
def get_roles(
    skip: int = 0,
    limit: int = 100,
    service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_user),
    current_membership: Membership = Depends(get_current_membership),
):
    return service.list_roles(
        current_user, current_membership, skip=skip, limit=limit
    )


@role_router.get("/{role_id}", response_model=RoleDetails)
def get_role(
    role_id: int,
    service: RoleService = Depends(get_role_service),
    current_user: User = Depends(require_permission("roles", "read")),
):
    return service.get_role(role_id)


@role_router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    request: Request = None,
    service: RoleService = Depends(get_role_service),
    current_user: User = Depends(require_permission("roles", "update")),
):
    return service.update_role(
        role_id,
        role_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@role_router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    request: Request = None,
    service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_user),
    current_membership: Membership = Depends(get_current_membership),
):
    service.delete_role(
        role_id,
        current_user,
        current_membership,
        ip_address=request.client.host if request else None,
    )
    return {"detail": "Role deleted successfully"}
