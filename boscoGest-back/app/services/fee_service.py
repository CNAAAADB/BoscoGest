import logging
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session


def _cycle_year(ref: date, start_month: int) -> int:
    """The year a yearly cycle belongs to, given the month it starts on.

    With start_month = 9, everything from September 2026 to August 2027 belongs
    to cycle 2026, labelled "2026-2027".
    """
    return ref.year if ref.month >= start_month else ref.year - 1


def derive_period(periodicity: str, ref: date, start_month: int = 1) -> str:
    """Label for the period that contains `ref`.

    The label identifies the charge and, with the unique constraint on
    (user, fee, period), is what stops the same period being billed twice.

    `start_month` shifts the yearly cycle, for an organisation whose financial
    year does not begin in January. It exists because with the default of 1 a
    yearly period spanning two calendar years came out labelled "2026" or
    "2027" depending on the day it was generated, and two consecutive cycles
    could collide on the same label.
    """
    if periodicity == FeePeriodicity.WEEKLY.value:
        iso = ref.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if periodicity == FeePeriodicity.MONTHLY.value:
        return f"{ref.year}-{ref.month:02d}"

    # Everything below divides a year, so it follows the cycle.
    year = _cycle_year(ref, start_month)
    # Months elapsed since the cycle began.
    offset = (ref.month - start_month) % 12

    if periodicity == FeePeriodicity.QUARTERLY.value:
        return f"{_span(year, start_month)}-T{offset // 3 + 1}"
    if periodicity == FeePeriodicity.FOUR_MONTHLY.value:
        return f"{_span(year, start_month)}-C{offset // 4 + 1}"
    if periodicity == FeePeriodicity.BIANNUAL.value:
        return f"{_span(year, start_month)}-S{offset // 6 + 1}"
    return _span(year, start_month)  # annual


def _span(year: int, start_month: int) -> str:
    """"2026" for a calendar cycle, "2026-2027" for one that straddles years."""
    return str(year) if start_month == 1 else f"{year}-{year + 1}"


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    return date(d.year + total // 12, total % 12 + 1, 1)


def period_start_date(periodicity: str, ref: date, start_month: int = 1) -> date:
    """First day of the period that contains `ref`."""
    if periodicity == FeePeriodicity.WEEKLY.value:
        return ref - timedelta(days=ref.weekday())
    if periodicity == FeePeriodicity.MONTHLY.value:
        return date(ref.year, ref.month, 1)

    cycle_start = date(_cycle_year(ref, start_month), start_month, 1)
    months = {
        FeePeriodicity.QUARTERLY.value: 3,
        FeePeriodicity.FOUR_MONTHLY.value: 4,
        FeePeriodicity.BIANNUAL.value: 6,
    }.get(periodicity)
    if months is None:  # annual
        return cycle_start
    offset = (ref.month - start_month) % 12
    return _add_months(cycle_start, (offset // months) * months)


def period_end_date(periodicity: str, ref: date, start_month: int = 1) -> date:
    """Last day of the period that contains `ref` — the due date, since the
    member has the whole period to pay."""
    start = period_start_date(periodicity, ref, start_month)
    if periodicity == FeePeriodicity.WEEKLY.value:
        return start + timedelta(days=6)
    months = {
        FeePeriodicity.MONTHLY.value: 1,
        FeePeriodicity.QUARTERLY.value: 3,
        FeePeriodicity.FOUR_MONTHLY.value: 4,
        FeePeriodicity.BIANNUAL.value: 6,
    }.get(periodicity, 12)  # annual
    return _add_months(start, months) - timedelta(days=1)


from app.models.entity_model import Entity
from app.models.fee_model import (
    Fee,
    FeeAssignment,
    FeeConfig,
    FeeMaintenanceRun,
    FeePeriodicity,
    FeeStatus,
    FeeSubscription,
)
from app.models.user_model import User
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)
from app.repositories.fee_repository import (
    FeeAssignmentRepository,
    FeeConfigRepository,
    FeeMaintenanceRunRepository,
    FeeSubscriptionRepository,
    FeeRepository,
)
from app.schemas.fee import (
    FeeAssignmentGenerateRequest,
    FeeAssignmentStatusUpdate,
    FeeCreate,
    FeeGenerateResult,
    FeeVersionCreate,
    MemberPreviewResponse,
)
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.notification_service import EventType, NotificationService
from app.utils.auth import get_sync_db


class FeeService:
    def __init__(self, db: Session):
        self.db = db
        self.fee_repo = FeeRepository(db)
        self.config_repo = FeeConfigRepository(db)
        self.assignment_repo = FeeAssignmentRepository(db)
        self.run_repo = FeeMaintenanceRunRepository(db)
        self.subscription_repo = FeeSubscriptionRepository(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _get_fee_or_404(self, fee_id: int) -> Fee:
        fee = self.fee_repo.get_by_id(fee_id)
        if not fee or not fee.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee not found")
        return fee

    def _attach_current_config(self, fee: Fee) -> Fee:
        # Pydantic reads `current_config` off the instance; compute and cache it.
        fee.current_config = self.config_repo.get_current(fee.id)
        return fee

    # ── Entities selector ─────────────────────────────────────────────────────

    def list_fee_entities(self, current_user: User) -> List[Entity]:
        # Entities where the user can create fees (used by the admin UI selector).
        # Consistent with EntityService.get_admin_entities: based on the user's
        # active memberships, filtered by effective (inheritable) permission.
        seen: set[int] = set()
        entities: List[Entity] = []
        for membership in current_user.memberships:
            if not membership.is_active or membership.entity_id in seen:
                continue
            if self.auth_service.has_effective_permission(
                current_user, membership.entity_id, "fees", "create"
            ):
                entity = self.db.get(Entity, membership.entity_id)
                if entity and entity.is_active:
                    entities.append(entity)
                    seen.add(membership.entity_id)
        entities.sort(key=lambda e: e.name)
        return entities

    # ── Fees ──────────────────────────────────────────────────────────────────

    def list_fees(self, entity_id: int, current_user: User) -> List[Fee]:
        self.auth_service.check_entity_permission(current_user, entity_id, "fees", "read")
        return [self._attach_current_config(f) for f in self.fee_repo.list_by_entity(entity_id)]

    def create_fee(
        self,
        fee_in: FeeCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> List[Fee]:
        # One independent fee (with its initial version) per selected entity.
        for entity_id in fee_in.entity_ids:
            self.auth_service.check_entity_permission(current_user, entity_id, "fees", "create")

        created: List[Fee] = []
        for entity_id in fee_in.entity_ids:
            fee = Fee(
                entity_id=entity_id,
                name=fee_in.name,
                periodicity=fee_in.periodicity.value,
                period_start_month=fee_in.period_start_month,
                auto_renew=fee_in.auto_renew,
                reminder_days=fee_in.reminder_days,
                created_by=current_user.id,
            )
            self.fee_repo.create(fee)
            self.db.flush()  # obtain fee.id
            version = FeeConfig(
                fee_id=fee.id,
                amount=fee_in.amount,
                valid_from=fee_in.valid_from,
                valid_until=fee_in.valid_until,
                created_by=current_user.id,
            )
            self.config_repo.create(version)
            created.append(fee)

        self.db.commit()

        for fee in created:
            self.db.refresh(fee)
            self._attach_current_config(fee)
            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="fees",
                resource_id=fee.id,
                details={
                    "entity_id": fee.entity_id,
                    "name": fee.name,
                    "amount": float(fee_in.amount),
                },
                ip_address=ip_address,
            )

        return created

    def get_fee_history(self, fee_id: int, current_user: User) -> List[FeeConfig]:
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "read")
        return self.config_repo.get_history(fee_id)

    def add_fee_version(
        self,
        fee_id: int,
        version_in: FeeVersionCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> FeeConfig:
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "create")

        # Auto-close the previous open version(s): the latest is always the current one.
        for prev in self.config_repo.get_history(fee_id):
            if prev.valid_until is None and prev.valid_from < version_in.valid_from:
                prev.valid_until = version_in.valid_from - timedelta(days=1)

        version = FeeConfig(
            fee_id=fee_id,
            amount=version_in.amount,
            valid_from=version_in.valid_from,
            valid_until=version_in.valid_until,
            created_by=current_user.id,
        )
        self.config_repo.create(version)
        self.db.commit()
        self.db.refresh(version)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="create",
            resource_type="fee_configs",
            resource_id=version.id,
            details={"fee_id": fee_id, "amount": float(version_in.amount)},
            ip_address=ip_address,
        )
        return version

    def delete_fee(
        self,
        fee_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "manage")

        if self.config_repo.has_active_assignments(fee_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a fee with active (pending/overdue) assignments",
            )

        self.fee_repo.soft_delete(fee)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="fees",
            resource_id=fee_id,
            details={"entity_id": fee.entity_id, "name": fee.name},
            ip_address=ip_address,
        )

    # ── Assignments ─────────────────────────────────────────────────────────

    # ── Enrolments ───────────────────────────────────────────────────────────

    def list_subscriptions(self, fee_id: int, current_user: User) -> List[FeeSubscription]:
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "read")
        return self.subscription_repo.list_for_fee(fee_id)

    def subscribe_members(
        self,
        fee_id: int,
        user_ids: List[int],
        current_user: User,
        starts_on: Optional[date] = None,
        exempt: bool = False,
        exempt_reason: Optional[str] = None,
        ip_address: str | None = None,
    ) -> List[FeeSubscription]:
        """Enrol members in a fee. Re-enrolling someone reopens their row."""
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "manage")

        # Only members of the entity the fee belongs to.
        allowed = self.assignment_repo.active_member_ids(fee.entity_id)
        # Defaults to the start of the period in progress, not to today.
        # Enrolling somebody halfway through a period means they owe that
        # period; dating it from today would silently exclude them from the
        # period being billed, which is the one the treasurer is looking at.
        starts_on = starts_on or period_start_date(
            fee.periodicity, date.today(), fee.period_start_month
        )
        result: List[FeeSubscription] = []

        for user_id in user_ids:
            if user_id not in allowed:
                continue
            existing = self.subscription_repo.get_for_fee_user(fee_id, user_id)
            if existing:
                # Reopen rather than duplicate: the charges are the record of
                # what was actually billed, so the gap is not lost.
                existing.ends_on = None
                existing.exempt = exempt
                existing.exempt_reason = exempt_reason if exempt else None
                result.append(existing)
                continue
            result.append(
                self.subscription_repo.create(
                    FeeSubscription(
                        fee_id=fee_id,
                        user_id=user_id,
                        entity_id=fee.entity_id,
                        starts_on=starts_on,
                        exempt=exempt,
                        exempt_reason=exempt_reason if exempt else None,
                        created_by=current_user.id,
                    )
                )
            )

        self.db.commit()
        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="subscribe",
            resource_type="fee_subscriptions",
            resource_id=fee_id,
            details={"fee_id": fee_id, "count": len(result), "exempt": exempt},
            ip_address=ip_address,
        )
        return result

    def unsubscribe_member(
        self,
        fee_id: int,
        user_id: int,
        current_user: User,
        ends_on: Optional[date] = None,
        ip_address: str | None = None,
    ) -> None:
        """End an enrolment. Charges already issued are left alone — they are
        what was owed at the time, and deleting them would rewrite history."""
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "manage")

        subscription = self.subscription_repo.get_for_fee_user(fee_id, user_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member is not enrolled in this fee"
            )
        subscription.ends_on = ends_on or date.today()
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="unsubscribe",
            resource_type="fee_subscriptions",
            resource_id=subscription.id,
            details={"fee_id": fee_id, "user_id": user_id, "ends_on": str(subscription.ends_on)},
            ip_address=ip_address,
        )

    def set_exemption(
        self,
        fee_id: int,
        user_id: int,
        exempt: bool,
        current_user: User,
        reason: Optional[str] = None,
        ip_address: str | None = None,
    ) -> FeeSubscription:
        """Mark an enrolled member as not owing this fee — honorary members
        (REQ-USR-02), hardship, a family already covered by another payer.

        Kept apart from unenrolling: the association wants to know it chose not
        to charge, rather than losing the member from the roster entirely.
        """
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "manage")

        subscription = self.subscription_repo.get_for_fee_user(fee_id, user_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member is not enrolled in this fee"
            )
        subscription.exempt = exempt
        subscription.exempt_reason = reason if exempt else None
        self.db.commit()
        self.db.refresh(subscription)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="exempt" if exempt else "unexempt",
            resource_type="fee_subscriptions",
            resource_id=subscription.id,
            details={"fee_id": fee_id, "user_id": user_id, "reason": reason},
            ip_address=ip_address,
        )
        return subscription

    def preview_members(
        self,
        fee_id: int,
        current_user: User,
        reference_date: Optional[date] = None,
    ) -> List[MemberPreviewResponse]:
        fee = self._get_fee_or_404(fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "read")

        period = derive_period(fee.periodicity, reference_date or date.today(), fee.period_start_month)
        already = self.assignment_repo.assigned_user_ids_for_fee_period(fee_id, period)
        memberships = self.assignment_repo.list_active_members(fee.entity_id)
        return [
            MemberPreviewResponse(
                user_id=m.user_id,
                name=m.user.name,
                surname=m.user.surname,
                role_name=m.role.name if m.role else None,
                already_assigned=m.user_id in already,
            )
            for m in memberships
        ]

    def list_assignments(
        self,
        entity_id: int,
        current_user: User,
        fee_id: Optional[int] = None,
        period: Optional[str] = None,
        fee_status: Optional[FeeStatus] = None,
    ) -> List[FeeAssignment]:
        self.auth_service.check_entity_permission(current_user, entity_id, "fees", "list")
        return self.assignment_repo.get_by_entity(
            entity_id, fee_id=fee_id, period=period, status=fee_status
        )

    def get_my_assignments(self, current_user: User) -> List[FeeAssignment]:
        return self.assignment_repo.get_by_user(current_user.id)

    def generate_assignments(
        self,
        body: FeeAssignmentGenerateRequest,
        current_user: User,
        ip_address: str | None = None,
    ) -> FeeGenerateResult:
        fee = self._get_fee_or_404(body.fee_id)
        self.auth_service.check_entity_permission(current_user, fee.entity_id, "fees", "create")

        config = self.config_repo.get_current(fee.id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This fee has no active version (no current amount) for today",
            )

        ref = body.reference_date or date.today()
        period = derive_period(fee.periodicity, ref, fee.period_start_month)
        # Due date defaults to the end of the period (overridable explicitly)
        due_date = body.due_date or period_end_date(fee.periodicity, ref, fee.period_start_month)
        already = self.assignment_repo.assigned_user_ids_for_fee_period(fee.id, period)
        active = self.assignment_repo.active_member_ids(fee.entity_id)

        # Who to charge comes from the enrolments. `user_ids` narrows that set
        # when the treasurer wants to bill only part of it; it can no longer
        # introduce somebody who is not enrolled, which is what made the roster
        # drift from one period to the next.
        subscriptions = self.subscription_repo.list_for_fee(fee.id)
        if body.user_ids:
            requested = set(body.user_ids)
            subscriptions = [s for s in subscriptions if s.user_id in requested]

        created = 0
        skipped = 0
        exempted = 0
        notified_ids: List[int] = []

        for sub in subscriptions:
            if sub.user_id in already:
                skipped += 1
                continue
            if not sub.covers(due_date) or sub.user_id not in active:
                skipped += 1
                continue

            if sub.exempt:
                self.assignment_repo.create(
                    FeeAssignment(
                        fee_id=fee.id,
                        user_id=sub.user_id,
                        entity_id=fee.entity_id,
                        fee_config_id=config.id,
                        period=period,
                        amount=0,
                        status=FeeStatus.EXEMPT.value,
                        due_date=due_date,
                        notes=sub.exempt_reason,
                    )
                )
                exempted += 1
                continue

            self.assignment_repo.create(
                FeeAssignment(
                    fee_id=fee.id,
                    user_id=sub.user_id,
                    entity_id=fee.entity_id,
                    fee_config_id=config.id,
                    period=period,
                    amount=config.amount,
                    status=FeeStatus.PENDING.value,
                    due_date=due_date,
                )
            )
            created += 1
            notified_ids.append(sub.user_id)

        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="generate",
            resource_type="fee_assignments",
            details={
                "fee_id": fee.id,
                "entity_id": fee.entity_id,
                "period": period,
                "periodicity": fee.periodicity,
                "created": created,
                "skipped": skipped,
            },
            ip_address=ip_address,
        )

        if notified_ids:
            self.notification_service.notify(
                event_type=EventType.FEE_GENERATED,
                entity_id=fee.entity_id,
                actor=current_user,
                resource_type="fee_assignments",
                title=f"Nueva cuota asignada — {fee.name} ({period})",
                recipient_ids=notified_ids,
            )

        return FeeGenerateResult(
            created=created,
            skipped=skipped,
            exempt=exempted,
            period=period,
            fee_id=fee.id,
            entity_id=fee.entity_id,
        )

    def update_assignment_status(
        self,
        assignment_id: int,
        body: FeeAssignmentStatusUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> FeeAssignment:
        assignment = self.assignment_repo.get_by_id(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fee assignment not found"
            )

        self.auth_service.check_entity_permission(
            current_user, assignment.entity_id, "fees", "manage"
        )

        old_status = assignment.status
        assignment.status = body.status.value
        if body.notes is not None:
            assignment.notes = body.notes
        if body.status == FeeStatus.PAID:
            assignment.paid_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(assignment)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="update",
            resource_type="fee_assignments",
            resource_id=assignment_id,
            details={"old_status": old_status, "new_status": body.status.value},
            ip_address=ip_address,
        )

        # Notify the member when their fee is registered as paid
        if body.status == FeeStatus.PAID and old_status != FeeStatus.PAID.value:
            self.notification_service.notify(
                event_type=EventType.FEE_PAID,
                entity_id=assignment.entity_id,
                actor=current_user,
                resource_type="fee_assignments",
                resource_id=assignment.id,
                title=f"Cuota pagada — {assignment.fee_name} ({assignment.period})",
                recipient_ids=[assignment.user_id],
            )

        return assignment


    # ── Proof of payment ─────────────────────────────────────────────────────
    #
    # With no gateway and no bank feed, a transfer is invisible to the platform.
    # The member telling us, with a receipt attached, is the only signal there
    # is — so it gets a state of its own rather than an admin editing a status
    # on hearsay, and the treasurer gets a queue to work through.

    ALLOWED_PROOF_TYPES = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/heic": ".heic",
    }
    MAX_PROOF_BYTES = 10 * 1024 * 1024

    def submit_proof(
        self,
        assignment_id: int,
        current_user: User,
        content: bytes,
        content_type: str,
        reference: Optional[str] = None,
        ip_address: str | None = None,
    ) -> FeeAssignment:
        assignment = self.assignment_repo.get_by_id(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fee assignment not found"
            )
        # Members act on their own charges only; no permission grants this.
        if assignment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only send proof of payment for your own fees",
            )
        if assignment.status in (FeeStatus.PAID.value, FeeStatus.CANCELLED.value, FeeStatus.EXEMPT.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This fee is already settled",
            )
        if content_type not in self.ALLOWED_PROOF_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Send the receipt as PDF, JPG, PNG or HEIC",
            )
        if len(content) > self.MAX_PROOF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The receipt must be under 10 MB",
            )

        extension = self.ALLOWED_PROOF_TYPES[content_type]
        key = f"fee-proofs/{assignment.entity_id}/{assignment.id}-{uuid4().hex}{extension}"
        storage = get_storage_service()
        storage.upload(key, content, content_type)

        # Replacing an earlier attempt: drop the old file rather than orphan it.
        if assignment.proof_path:
            try:
                storage.delete(assignment.proof_path)
            except Exception:
                logger.warning("Could not delete the previous proof %s", assignment.proof_path)

        assignment.proof_path = key
        assignment.proof_reference = reference
        assignment.proof_submitted_at = datetime.now(timezone.utc)
        assignment.proof_rejected_reason = None
        assignment.status = FeeStatus.SUBMITTED.value
        self.db.commit()
        self.db.refresh(assignment)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="submit_proof",
            resource_type="fee_assignments",
            resource_id=assignment.id,
            details={"reference": reference},
            ip_address=ip_address,
        )

        # Whoever can settle fees in this entity needs to know there is
        # something waiting; the member cannot chase it themselves.
        reviewers = self.assignment_repo.member_ids_with_permission(
            assignment.entity_id, "fees", "manage"
        )
        if reviewers:
            self.notification_service.notify(
                event_type=EventType.FEE_PROOF_SUBMITTED,
                entity_id=assignment.entity_id,
                actor=current_user,
                resource_type="fee_assignments",
                resource_id=assignment.id,
                title=(
                    f"Justificante recibido — {assignment.fee_name} ({assignment.period}), "
                    f"{current_user.name} {current_user.surname}"
                ),
                recipient_ids=reviewers,
            )
        return assignment

    def get_proof_url(self, assignment_id: int, current_user: User) -> str:
        """A short-lived link to the receipt, for the member who sent it and for
        whoever reviews it."""
        assignment = self.assignment_repo.get_by_id(assignment_id)
        if not assignment or not assignment.proof_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No proof of payment on this fee"
            )
        if assignment.user_id != current_user.id:
            self.auth_service.check_entity_permission(
                current_user, assignment.entity_id, "fees", "manage"
            )
        return get_storage_service().get_presigned_url(assignment.proof_path)

    def reject_proof(
        self,
        assignment_id: int,
        reason: str,
        current_user: User,
        ip_address: str | None = None,
    ) -> FeeAssignment:
        """Send a receipt back with a reason, returning the fee to pending.

        The reason is required: "rejected" with no explanation leaves the member
        with nothing to act on.
        """
        assignment = self.assignment_repo.get_by_id(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fee assignment not found"
            )
        self.auth_service.check_entity_permission(
            current_user, assignment.entity_id, "fees", "manage"
        )
        if assignment.status != FeeStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This fee has no proof awaiting review",
            )
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Give the member a reason so they know what to correct",
            )

        assignment.status = FeeStatus.PENDING.value
        assignment.proof_rejected_reason = reason.strip()
        self.db.commit()
        self.db.refresh(assignment)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="reject_proof",
            resource_type="fee_assignments",
            resource_id=assignment.id,
            details={"reason": reason},
            ip_address=ip_address,
        )
        self._notify_member(
            assignment,
            EventType.FEE_PROOF_REJECTED,
            f"Justificante devuelto — {assignment.fee_name} ({assignment.period})",
        )
        return assignment

    # ── Maintenance (REQ-FEE-03: overdue, reminders, auto-renewal) ────────────

    def _notify_member(self, assignment: FeeAssignment, event_type: str, title: str) -> None:
        # System notification (no actor) to the fee's member.
        self.notification_service.notify(
            event_type=event_type,
            entity_id=assignment.entity_id,
            actor=None,
            resource_type="fee_assignments",
            resource_id=assignment.id,
            title=title,
            recipient_ids=[assignment.user_id],
        )

    def _renew_fee(self, fee: Fee, today: date, details: dict) -> int:
        """Charge every member enrolled in this fee for the current period.

        This used to copy whoever was charged in the previous period. That made
        the roster a consequence of history: a period nobody generated left the
        previous one empty, renewal returned zero, and the fee stopped renewing
        silently and never resumed. It now reads the enrolments, so a gap in the
        charges changes nothing.
        """
        period = derive_period(fee.periodicity, today, fee.period_start_month)
        already = self.assignment_repo.assigned_user_ids_for_fee_period(fee.id, period)
        config = self.config_repo.get_current(fee.id)
        if not config:
            return 0  # no current amount → nothing to charge

        due = period_end_date(fee.periodicity, today, fee.period_start_month)
        active = self.assignment_repo.active_member_ids(fee.entity_id)
        created = 0
        exempted = 0

        for sub in self.subscription_repo.list_for_fee(fee.id):
            if sub.user_id in already:
                continue
            # Enrolment has to be in force for the period being charged, not
            # merely to exist: somebody who left in March is not charged in May.
            if not sub.covers(due):
                continue
            # Still has to be a member of the entity.
            if sub.user_id not in active:
                continue

            if sub.exempt:
                # Recorded rather than skipped, so the roster of who was covered
                # this period is complete and the exemption is visible.
                self.assignment_repo.create(
                    FeeAssignment(
                        fee_id=fee.id,
                        user_id=sub.user_id,
                        entity_id=fee.entity_id,
                        fee_config_id=config.id,
                        period=period,
                        amount=0,
                        status=FeeStatus.EXEMPT.value,
                        due_date=due,
                        notes=sub.exempt_reason,
                    )
                )
                exempted += 1
                continue

            self.assignment_repo.create(
                FeeAssignment(
                    fee_id=fee.id,
                    user_id=sub.user_id,
                    entity_id=fee.entity_id,
                    fee_config_id=config.id,
                    period=period,
                    amount=config.amount,
                    status=FeeStatus.PENDING.value,
                    due_date=due,
                )
            )
            created += 1

        if not created and not exempted:
            return 0

        charged_ids = [
            a.user_id
            for a in self.assignment_repo.get_by_entity(fee.entity_id, fee_id=fee.id, period=period)
            if a.status == FeeStatus.PENDING.value
        ]
        if charged_ids:
            self.notification_service.notify(
                event_type=EventType.FEE_RENEWED,
                entity_id=fee.entity_id,
                actor=None,
                resource_type="fee_assignments",
                title=f"Cuota renovada — {fee.name} ({period})",
                recipient_ids=charged_ids,
            )
        details["renewed"].append(
            {"fee_id": fee.id, "period": period, "count": created, "exempt": exempted}
        )
        return created

    def run_maintenance(
        self,
        today: Optional[date] = None,
        trigger: str = "scheduled",
        triggered_by: Optional[User] = None,
    ) -> FeeMaintenanceRun:
        """Daily job: mark overdue, send reminders, auto-renew. Idempotent.
        Records a FeeMaintenanceRun for monitoring. `today` injectable for tests."""
        today = today or date.today()
        run = FeeMaintenanceRun(
            trigger=trigger,
            triggered_by_id=triggered_by.id if triggered_by else None,
            status="success",
        )
        self.run_repo.create(run)
        self.db.commit()
        self.db.refresh(run)
        run_id = run.id

        details: dict = {"overdue": [], "reminded": [], "renewed": []}
        overdue = reminded = renewed = 0
        try:
            # 1 + 2: overdue and reminders over pending assignments with a due date
            for a in self.assignment_repo.get_pending_with_due_date():
                if a.due_date < today:
                    a.status = FeeStatus.OVERDUE.value
                    overdue += 1
                    details["overdue"].append(a.id)
                    self._notify_member(
                        a, EventType.FEE_OVERDUE,
                        f"Cuota vencida — {a.fee.name} ({a.period})",
                    )
                elif not a.reminder_sent and (a.due_date - today).days <= a.fee.reminder_days:
                    a.reminder_sent = True
                    reminded += 1
                    details["reminded"].append(a.id)
                    self._notify_member(
                        a, EventType.FEE_REMINDER,
                        f"Recordatorio: la cuota «{a.fee.name}» vence el {a.due_date.isoformat()}",
                    )

            # 3: auto-renewal (carry-over from previous period)
            for fee in self.fee_repo.list_auto_renew():
                renewed += self._renew_fee(fee, today, details)

            run = self.db.get(FeeMaintenanceRun, run_id)
            run.status = "success"
        except Exception as exc:  # noqa: BLE001 — best-effort; notify() already committed partial work
            self.db.rollback()
            run = self.db.get(FeeMaintenanceRun, run_id)
            run.status = "error"
            run.error = str(exc)

        run.finished_at = datetime.utcnow()
        run.overdue_count = overdue
        run.reminded_count = reminded
        run.renewed_count = renewed
        run.details = details
        self.db.commit()
        self.db.refresh(run)

        self.audit_service.create_audit_log(
            user_id=triggered_by.id if triggered_by else None,
            action="maintenance",
            resource_type="fee_maintenance_runs",
            resource_id=run.id,
            details={"overdue": overdue, "reminded": reminded, "renewed": renewed, "trigger": trigger},
        )
        return run

    def trigger_maintenance(self, current_user: User) -> FeeMaintenanceRun:
        if not self.auth_service.has_global_permission(current_user, "fees", "maintenance"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return self.run_maintenance(trigger="manual", triggered_by=current_user)

    def list_maintenance_runs(
        self, current_user: User, skip: int = 0, limit: int = 50
    ) -> List[FeeMaintenanceRun]:
        if not self.auth_service.has_global_permission(current_user, "fees", "maintenance"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return self.run_repo.list(skip=skip, limit=limit)


def get_fee_service(db: Session = Depends(get_sync_db)) -> FeeService:
    return FeeService(db)
