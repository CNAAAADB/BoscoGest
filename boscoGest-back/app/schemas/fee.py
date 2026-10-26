from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import date, datetime
from typing import List, Optional
from app.models.fee_model import FeeStatus, FeePeriodicity


# ── Fee (cuota con nombre, por entidad) ─────────────────────────────────────

class FeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    periodicity: FeePeriodicity
    entity_ids: List[int] = Field(..., min_length=1, description="One independent fee is created per entity")
    amount: float = Field(..., gt=0, description="Initial amount in euros")
    valid_from: date
    valid_until: Optional[date] = None
    auto_renew: bool = False
    reminder_days: int = Field(7, ge=0, description="Days before due date to send a reminder")
    # Defaults to 1 (the calendar year) so an existing caller that does not
    # send it keeps the behaviour it had. Set it to the month the
    # organisation's financial year starts on.
    period_start_month: int = Field(
        1, ge=1, le=12, description="Month a yearly cycle starts on (1 = calendar year)"
    )


class FeeConfigResponse(BaseModel):
    id: int
    fee_id: int
    amount: float
    valid_from: date
    valid_until: Optional[date] = None
    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeeResponse(BaseModel):
    id: int
    entity_id: int
    name: str
    periodicity: FeePeriodicity
    period_start_month: int
    auto_renew: bool
    reminder_days: int
    is_active: bool
    created_at: datetime
    current_config: Optional[FeeConfigResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FeeVersionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in euros")
    valid_from: date
    valid_until: Optional[date] = None


# ── Fee Assignment ──────────────────────────────────────────────────────────

class MemberPreviewResponse(BaseModel):
    user_id: int
    name: str
    surname: str
    role_name: Optional[str] = None
    already_assigned: bool = False


class FeeAssignmentGenerateRequest(BaseModel):
    fee_id: int
    reference_date: Optional[date] = None
    # Omit to charge everyone enrolled in the fee, which is the normal case.
    # Supplying ids narrows that roster; it cannot add somebody outside it.
    user_ids: Optional[List[int]] = None
    due_date: Optional[date] = None



class FeeAssignmentStatusUpdate(BaseModel):
    status: FeeStatus
    notes: Optional[str] = None


class UserBrief(BaseModel):
    id: int
    name: str
    surname: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class FeeAssignmentResponse(BaseModel):
    """A charge as shown to the member and to whoever settles it."""

    id: int
    fee_id: int
    fee_name: Optional[str] = None
    user_id: int
    entity_id: int
    fee_config_id: Optional[int] = None
    periodicity: FeePeriodicity
    period: str
    amount: float
    status: FeeStatus
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None

    # Proof of payment. Without a gateway this is the whole payment record, so
    # both the member and the treasurer need to see its state.
    proof_reference: Optional[str] = None
    proof_submitted_at: Optional[datetime] = None
    proof_rejected_reason: Optional[str] = None
    has_proof: bool = False
    created_at: datetime
    user: Optional[UserBrief] = None

    model_config = ConfigDict(from_attributes=True)


class FeeGenerateResult(BaseModel):
    created: int
    skipped: int
    # Enrolled members recorded as owing nothing (honorary and the like).
    # Counted separately so "created 12, skipped 3" does not hide them.
    exempt: int = 0
    period: str
    fee_id: int
    entity_id: int


# ── Maintenance / monitoring ────────────────────────────────────────────────

class TriggeredByBrief(BaseModel):
    id: int
    name: str
    surname: str

    model_config = ConfigDict(from_attributes=True)


class FeeMaintenanceRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    trigger: str
    triggered_by_id: Optional[int] = None
    triggered_by: Optional[TriggeredByBrief] = None
    overdue_count: int
    reminded_count: int
    renewed_count: int
    details: Optional[dict] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Enrolments ──────────────────────────────────────────────────────────────

class FeeSubscriptionResponse(BaseModel):
    id: int
    fee_id: int
    user_id: int
    entity_id: int
    starts_on: date
    ends_on: Optional[date] = None
    exempt: bool
    exempt_reason: Optional[str] = None
    # Denormalised for the roster table, so the client needs no second call.
    user_name: Optional[str] = None
    user_surname: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _flatten_user(cls, value):
        user = getattr(value, "user", None)
        if user is not None:
            # Pydantic reads attributes, so set them on the ORM object itself.
            object.__setattr__(value, "user_name", user.name)
            object.__setattr__(value, "user_surname", user.surname)
        return value


class FeeSubscribeRequest(BaseModel):
    user_ids: List[int] = Field(min_length=1)
    starts_on: Optional[date] = None
    exempt: bool = False
    exempt_reason: Optional[str] = Field(default=None, max_length=200)


class FeeExemptionRequest(BaseModel):
    exempt: bool
    reason: Optional[str] = Field(default=None, max_length=200)


class FeeUnsubscribeRequest(BaseModel):
    ends_on: Optional[date] = None


# ── Proof of payment ────────────────────────────────────────────────────────

class FeeProofRejectRequest(BaseModel):
    # Required: sending a receipt back without saying why leaves the member
    # with nothing to act on.
    reason: str = Field(min_length=3, max_length=500)
