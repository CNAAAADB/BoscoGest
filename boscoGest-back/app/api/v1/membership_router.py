from fastapi import APIRouter, Depends, Request, status
from typing import List
from app.models.user_model import User
from app.schemas.membership import (
    MembershipCreate,
    MembershipUpdate,
    MembershipResponse,
    MembershipDetails,
)
from app.utils.auth import get_current_active_user
from app.services.membership_service import MembershipService, get_membership_service

membership_router = APIRouter(
    prefix="/memberships", tags=["Membership Management"]
)


@membership_router.post(
    "", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED
)
def create_membership(
    membership: MembershipCreate,
    request: Request = None,
    service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_membership(
        membership,
        current_user,
        ip_address=request.client.host if request else None,
    )


@membership_router.get("", response_model=List[MembershipDetails])
def get_memberships(
    service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_memberships(current_user)


@membership_router.get("/{membership_id}", response_model=MembershipDetails)
def get_membership(
    membership_id: int,
    service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_membership(membership_id, current_user)


@membership_router.put("/{membership_id}", response_model=MembershipResponse)
def update_membership(
    membership_id: int,
    membership_update: MembershipUpdate,
    request: Request = None,
    service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_membership(
        membership_id,
        membership_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@membership_router.delete(
    "/{membership_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_membership(
    membership_id: int,
    request: Request = None,
    service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_membership(
        membership_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return None
