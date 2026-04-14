from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status
from app.models.user_model import User
from app.schemas.membership_request import (
    MembershipRequestCreate,
    MembershipRequestReject,
    MembershipRequestResponse,
)
from app.utils.auth import get_current_active_user
from app.services.membership_request_service import (
    MembershipRequestService,
    get_membership_request_service,
)

membership_request_router = APIRouter(
    prefix="/membership-requests", tags=["Membership Requests"]
)


@membership_request_router.get(
    "/mine", response_model=List[MembershipRequestResponse]
)
def get_my_requests(
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Returns the current user's own membership requests."""
    return service.list_my_requests(current_user.id)


@membership_request_router.get("", response_model=List[MembershipRequestResponse])
def list_requests(
    entity_id: Optional[int] = None,
    status: Optional[str] = None,
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Lists pending requests for entities the current user can manage."""
    return service.list_requests_for_admin(current_user, entity_id=entity_id, status_filter=status)


@membership_request_router.post(
    "",
    response_model=MembershipRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    request_in: MembershipRequestCreate,
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Creates a new membership request for the current user (used when joining a new entity)."""
    return service.create_request(
        user_id=current_user.id,
        entity_id=request_in.entity_id,
        message=request_in.message,
    )


@membership_request_router.post(
    "/{request_id}/accept", response_model=MembershipRequestResponse
)
def accept_request(
    request_id: int,
    request: Request = None,
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Accepts a membership request and creates the membership."""
    ip_address = request.client.host if request else None
    return service.accept_request(request_id, current_user, ip_address=ip_address)


@membership_request_router.post(
    "/{request_id}/reject", response_model=MembershipRequestResponse
)
def reject_request(
    request_id: int,
    body: MembershipRequestReject = MembershipRequestReject(),
    request: Request = None,
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Rejects a membership request with an optional reason."""
    ip_address = request.client.host if request else None
    return service.reject_request(
        request_id,
        current_user,
        rejection_reason=body.rejection_reason,
        ip_address=ip_address,
    )


@membership_request_router.delete(
    "/{request_id}", status_code=status.HTTP_204_NO_CONTENT
)
def cancel_request(
    request_id: int,
    service: MembershipRequestService = Depends(get_membership_request_service),
    current_user: User = Depends(get_current_active_user),
):
    """Cancels a pending request (only the requesting user can cancel their own request)."""
    service.cancel_request(request_id, current_user)
