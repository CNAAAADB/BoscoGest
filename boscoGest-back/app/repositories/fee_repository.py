from datetime import date
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.fee_model import (
    FeeSubscription,
    Fee,
    FeeAssignment,
    FeeConfig,
    FeeMaintenanceRun,
    FeeStatus,
)
from app.models.membership_model import Membership
from app.models.user_model import User
from app.repositories.base_repository import BaseRepository


class FeeRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Fee)

    def get_by_id(self, fee_id: int) -> Optional[Fee]:
        return self.base.get_by_id(fee_id)

    def list_by_entity(self, entity_id: int) -> List[Fee]:
        stmt = (
            select(Fee)
            .where(Fee.entity_id == entity_id, Fee.is_active == True)
            .order_by(Fee.name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, fee: Fee) -> Fee:
        return self.base.create(fee)

    def soft_delete(self, fee: Fee) -> None:
        fee.is_active = False
        self.db.flush()

    def list_auto_renew(self) -> List[Fee]:
        stmt = select(Fee).where(Fee.is_active == True, Fee.auto_renew == True)
        return list(self.db.execute(stmt).scalars().all())


class FeeConfigRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, FeeConfig)

    def get_by_id(self, config_id: int) -> Optional[FeeConfig]:
        return self.base.get_by_id(config_id)

    def get_current(self, fee_id: int) -> Optional[FeeConfig]:
        today = date.today()
        stmt = (
            select(FeeConfig)
            .where(
                FeeConfig.fee_id == fee_id,
                FeeConfig.valid_from <= today,
                or_(FeeConfig.valid_until.is_(None), FeeConfig.valid_until >= today),
            )
            .order_by(FeeConfig.valid_from.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_history(self, fee_id: int) -> List[FeeConfig]:
        stmt = (
            select(FeeConfig)
            .where(FeeConfig.fee_id == fee_id)
            .order_by(FeeConfig.valid_from.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def has_active_assignments(self, fee_id: int) -> bool:
        stmt = (
            select(FeeAssignment.id)
            .where(
                FeeAssignment.fee_id == fee_id,
                FeeAssignment.status.in_([FeeStatus.PENDING.value, FeeStatus.OVERDUE.value]),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first() is not None

    def create(self, config: FeeConfig) -> FeeConfig:
        return self.base.create(config)


class FeeSubscriptionRepository:
    """Who is enrolled in which fee — the roster that generation reads."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subscription_id: int) -> Optional[FeeSubscription]:
        return self.db.get(FeeSubscription, subscription_id)

    def get_for_fee_user(self, fee_id: int, user_id: int) -> Optional[FeeSubscription]:
        return self.db.execute(
            select(FeeSubscription).where(
                FeeSubscription.fee_id == fee_id,
                FeeSubscription.user_id == user_id,
            )
        ).scalars().first()

    def list_for_fee(self, fee_id: int) -> List[FeeSubscription]:
        return list(
            self.db.execute(
                select(FeeSubscription)
                .where(FeeSubscription.fee_id == fee_id)
                .order_by(FeeSubscription.id)
            ).scalars().unique().all()
        )

    def list_for_user(self, user_id: int) -> List[FeeSubscription]:
        return list(
            self.db.execute(
                select(FeeSubscription).where(FeeSubscription.user_id == user_id)
            ).scalars().unique().all()
        )

    def create(self, subscription: FeeSubscription) -> FeeSubscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription

    def delete(self, subscription: FeeSubscription) -> None:
        self.db.delete(subscription)
        self.db.flush()


class FeeAssignmentRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, FeeAssignment)

    def get_by_id(self, assignment_id: int) -> Optional[FeeAssignment]:
        return self.base.get_by_id(assignment_id)

    def get_by_entity(
        self,
        entity_id: int,
        fee_id: Optional[int] = None,
        period: Optional[str] = None,
        status: Optional[FeeStatus] = None,
    ) -> List[FeeAssignment]:
        stmt = (
            select(FeeAssignment)
            .options(joinedload(FeeAssignment.fee))
            .where(FeeAssignment.entity_id == entity_id)
            .order_by(FeeAssignment.created_at.desc())
        )
        if fee_id is not None:
            stmt = stmt.where(FeeAssignment.fee_id == fee_id)
        if period is not None:
            stmt = stmt.where(FeeAssignment.period == period)
        if status is not None:
            stmt = stmt.where(FeeAssignment.status == status.value)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_user(self, user_id: int) -> List[FeeAssignment]:
        stmt = (
            select(FeeAssignment)
            .options(joinedload(FeeAssignment.fee))
            .where(FeeAssignment.user_id == user_id)
            .order_by(FeeAssignment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def exists_for_user_fee_period(self, user_id: int, fee_id: int, period: str) -> bool:
        stmt = (
            select(FeeAssignment.id)
            .where(
                FeeAssignment.user_id == user_id,
                FeeAssignment.fee_id == fee_id,
                FeeAssignment.period == period,
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first() is not None

    def assigned_user_ids_for_fee_period(self, fee_id: int, period: str) -> set[int]:
        stmt = select(FeeAssignment.user_id).where(
            FeeAssignment.fee_id == fee_id,
            FeeAssignment.period == period,
        )
        return {row[0] for row in self.db.execute(stmt).all()}

    def get_pending_with_due_date(self) -> List[FeeAssignment]:
        # Pending assignments that have a due date, with their fee eager-loaded
        # (needed for overdue + reminder passes of the maintenance job).
        stmt = (
            select(FeeAssignment)
            .options(joinedload(FeeAssignment.fee))
            .where(
                FeeAssignment.status == FeeStatus.PENDING.value,
                FeeAssignment.due_date.is_not(None),
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, assignment: FeeAssignment) -> FeeAssignment:
        return self.base.create(assignment)

    def list_active_members(self, entity_id: int) -> List[Membership]:
        # Active members of an entity with user + role eager-loaded (for preview).
        stmt = (
            select(Membership)
            .options(joinedload(Membership.user), joinedload(Membership.role))
            .join(User, Membership.user_id == User.id)
            .where(
                Membership.entity_id == entity_id,
                Membership.is_active == True,
                User.is_active == True,
            )
            .order_by(User.surname, User.name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def member_ids_with_permission(self, entity_id: int, resource: str, action: str) -> List[int]:
        """Active members of the entity whose role grants (resource, action).

        Used to route a submitted receipt to whoever can settle it, rather than
        leaving it for someone to notice.
        """
        from app.models.permission_model import Permission
        from app.models.role_model import Role
        from app.models.relationships import role_permissions

        rows = self.db.execute(
            select(Membership.user_id)
            .join(Role, Role.id == Membership.role_id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                Membership.entity_id == entity_id,
                Membership.is_active == True,  # noqa: E712
                Permission.resource == resource,
                Permission.action.in_([action, "manage_all"]),
            )
            .distinct()
        ).scalars().all()
        return list(rows)

    def active_member_ids(self, entity_id: int) -> set[int]:
        stmt = (
            select(Membership.user_id)
            .join(User, Membership.user_id == User.id)
            .where(
                Membership.entity_id == entity_id,
                Membership.is_active == True,
                User.is_active == True,
            )
        )
        return {row[0] for row in self.db.execute(stmt).all()}


class FeeMaintenanceRunRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, FeeMaintenanceRun)

    def create(self, run: FeeMaintenanceRun) -> FeeMaintenanceRun:
        return self.base.create(run)

    def list(self, skip: int = 0, limit: int = 50) -> List[FeeMaintenanceRun]:
        stmt = (
            select(FeeMaintenanceRun)
            .order_by(FeeMaintenanceRun.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
