from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi import status as http_status

from app.models.fee_model import FeeStatus
from app.models.user_model import User
from app.schemas.entity import EntityResponse
from app.schemas.fee import (
    FeeExemptionRequest,
    FeeProofRejectRequest,
    FeeSubscribeRequest,
    FeeSubscriptionResponse,
    FeeUnsubscribeRequest,
    FeeAssignmentGenerateRequest,
    FeeAssignmentResponse,
    FeeAssignmentStatusUpdate,
    FeeConfigResponse,
    FeeCreate,
    FeeGenerateResult,
    FeeMaintenanceRunResponse,
    FeeResponse,
    FeeVersionCreate,
    MemberPreviewResponse,
)
from app.services.fee_service import FeeService, get_fee_service
from app.utils.auth import get_current_active_user

fee_router = APIRouter(prefix="/fees", tags=["Fees"])


# ── Entities selector ───────────────────────────────────────────────────────

@fee_router.get("/entities", response_model=List[EntityResponse])
def list_fee_entities(
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_fee_entities(current_user)


# ── Fees ────────────────────────────────────────────────────────────────────

@fee_router.get("", response_model=List[FeeResponse])
def list_fees(
    entity_id: int = Query(...),
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_fees(entity_id, current_user)


@fee_router.post("", response_model=List[FeeResponse], status_code=http_status.HTTP_201_CREATED)
def create_fee(
    fee_in: FeeCreate,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_fee(
        fee_in, current_user, ip_address=request.client.host if request else None
    )


@fee_router.get("/{fee_id}/history", response_model=List[FeeConfigResponse])
def get_fee_history(
    fee_id: int,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_fee_history(fee_id, current_user)


@fee_router.post(
    "/{fee_id}/versions",
    response_model=FeeConfigResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def add_fee_version(
    fee_id: int,
    version_in: FeeVersionCreate,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.add_fee_version(
        fee_id, version_in, current_user, ip_address=request.client.host if request else None
    )


@fee_router.delete("/{fee_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_fee(
    fee_id: int,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_fee(fee_id, current_user, ip_address=request.client.host if request else None)
    return None


# ── Maintenance / monitoring ──────────────────────────────────────────────────

@fee_router.post(
    "/maintenance/run",
    response_model=FeeMaintenanceRunResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def run_maintenance(
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.trigger_maintenance(current_user)


@fee_router.get("/maintenance/runs", response_model=List[FeeMaintenanceRunResponse])
def list_maintenance_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_maintenance_runs(current_user, skip=skip, limit=limit)


# ── Assignments ───────────────────────────────────────────────────────────────

@fee_router.get("/members-preview", response_model=List[MemberPreviewResponse])
def preview_members(
    fee_id: int = Query(...),
    reference_date: Optional[date] = Query(None),
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.preview_members(fee_id, current_user, reference_date=reference_date)


@fee_router.get("/assignments/mine", response_model=List[FeeAssignmentResponse])
def get_my_assignments(
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_my_assignments(current_user)


@fee_router.get("/assignments", response_model=List[FeeAssignmentResponse])
def list_assignments(
    entity_id: int = Query(...),
    fee_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    fee_status: Optional[FeeStatus] = Query(None, alias="status"),
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_assignments(
        entity_id, current_user, fee_id=fee_id, period=period, fee_status=fee_status
    )


@fee_router.post(
    "/assignments/generate",
    response_model=FeeGenerateResult,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_assignments(
    body: FeeAssignmentGenerateRequest,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.generate_assignments(
        body, current_user, ip_address=request.client.host if request else None
    )


@fee_router.patch("/assignments/{assignment_id}/status", response_model=FeeAssignmentResponse)
def update_assignment_status(
    assignment_id: int,
    body: FeeAssignmentStatusUpdate,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_assignment_status(
        assignment_id, body, current_user, ip_address=request.client.host if request else None
    )


# ── Enrolments ──────────────────────────────────────────────────────────────
#
# Who owes a fee is declared here. Generation and the nightly renewal both read
# this roster, rather than repeating whoever happened to be charged last period.

@fee_router.get("/{fee_id}/subscriptions", response_model=List[FeeSubscriptionResponse])
def list_subscriptions(
    fee_id: int,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """Members enrolled in this fee, with their dates and any exemption."""
    return service.list_subscriptions(fee_id, current_user)


@fee_router.post(
    "/{fee_id}/subscriptions",
    response_model=List[FeeSubscriptionResponse],
    status_code=http_status.HTTP_201_CREATED,
)
def subscribe_members(
    fee_id: int,
    body: FeeSubscribeRequest,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """Enrol members. Re-enrolling somebody reopens their existing row."""
    return service.subscribe_members(
        fee_id,
        body.user_ids,
        current_user,
        starts_on=body.starts_on,
        exempt=body.exempt,
        exempt_reason=body.exempt_reason,
        ip_address=request.client.host if request else None,
    )


@fee_router.delete(
    "/{fee_id}/subscriptions/{user_id}", status_code=http_status.HTTP_204_NO_CONTENT
)
def unsubscribe_member(
    fee_id: int,
    user_id: int,
    body: FeeUnsubscribeRequest | None = None,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """End an enrolment. Charges already issued are left as they are."""
    service.unsubscribe_member(
        fee_id,
        user_id,
        current_user,
        ends_on=body.ends_on if body else None,
        ip_address=request.client.host if request else None,
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@fee_router.patch(
    "/{fee_id}/subscriptions/{user_id}/exemption", response_model=FeeSubscriptionResponse
)
def set_exemption(
    fee_id: int,
    user_id: int,
    body: FeeExemptionRequest,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """Mark an enrolled member as owing nothing for this fee, or undo it."""
    return service.set_exemption(
        fee_id,
        user_id,
        body.exempt,
        current_user,
        reason=body.reason,
        ip_address=request.client.host if request else None,
    )


# ── Proof of payment ────────────────────────────────────────────────────────
#
# There is no gateway and no bank feed, so a transfer is invisible to the
# platform until the member says so and attaches the receipt.

@fee_router.post("/assignments/{assignment_id}/proof", response_model=FeeAssignmentResponse)
async def submit_proof(
    assignment_id: int,
    file: UploadFile = File(...),
    reference: Optional[str] = Form(None),
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """Send the receipt for one of your own fees. PDF or image, up to 10 MB."""
    content = await file.read()
    return service.submit_proof(
        assignment_id,
        current_user,
        content=content,
        content_type=file.content_type or "",
        reference=reference,
        ip_address=request.client.host if request else None,
    )


@fee_router.get("/assignments/{assignment_id}/proof")
def get_proof(
    assignment_id: int,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """A short-lived link to the receipt, for its author or a reviewer."""
    return {"url": service.get_proof_url(assignment_id, current_user)}


@fee_router.post(
    "/assignments/{assignment_id}/proof/reject", response_model=FeeAssignmentResponse
)
def reject_proof(
    assignment_id: int,
    body: FeeProofRejectRequest,
    request: Request = None,
    service: FeeService = Depends(get_fee_service),
    current_user: User = Depends(get_current_active_user),
):
    """Return a receipt to the member with a reason; the fee goes back to pending."""
    return service.reject_proof(
        assignment_id,
        body.reason,
        current_user,
        ip_address=request.client.host if request else None,
    )
