import enum
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from typing import Any, Dict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FeeStatus(str, enum.Enum):
    PENDING = "pending"
    # The member says they have paid and attached proof. Without a payment
    # gateway this is the only signal the platform gets, so it needs a state of
    # its own: it is not yet money in the account, but it is no longer waiting
    # on the member either.
    SUBMITTED = "submitted"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    # Owed by nobody on purpose — honorary members (REQ-USR-02) do not pay.
    # Distinct from cancelled, which reads as "charged by mistake".
    EXEMPT = "exempt"


class FeePeriodicity(str, enum.Enum):
    WEEKLY = "weekly"            # semanal
    MONTHLY = "monthly"         # mensual
    QUARTERLY = "quarterly"     # trimestral
    FOUR_MONTHLY = "four_monthly"  # cuatrimestral
    BIANNUAL = "biannual"       # semestral
    ANNUAL = "annual"           # anual


class Fee(Base):
    # A named fee belonging to a single entity. An entity can have several fees.
    # Its amount history lives in FeeConfig rows (versions). Soft-deleted via is_active.
    __tablename__ = "fees"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    periodicity: Mapped[str] = mapped_column(
        SQLEnum(
            "weekly", "monthly", "quarterly", "four_monthly", "biannual", "annual",
            name="fee_periodicity",
        ),
        nullable=False,
    )
    # Automatic renewal / reminder policy (REQ-FEE-03). Due date is derived from
    # the periodicity (end of the period), not stored.
    # Month the yearly cycle starts on (1-12). Anchoring a yearly period to the
    # calendar year made its label depend on when it was generated: a fee for a
    # cycle spanning two years came out as "2026" or "2027" according to the day
    # somebody pressed the button, and always fell due on 31 December. Making
    # the start month configurable fixes that, and lets an organisation whose
    # financial year does not begin in January say so — a September-to-August
    # cycle, for instance. Which one applies here is not settled.
    period_start_month: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    entity: Mapped["Entity"] = relationship("Entity", back_populates="fees")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    versions: Mapped[List["FeeConfig"]] = relationship(
        "FeeConfig", back_populates="fee", cascade="all, delete-orphan"
    )
    assignments: Mapped[List["FeeAssignment"]] = relationship(
        "FeeAssignment", back_populates="fee"
    )
    subscriptions: Mapped[List["FeeSubscription"]] = relationship(
        "FeeSubscription", back_populates="fee", cascade="all, delete-orphan"
    )


class FeeConfig(Base):
    # A version of a Fee's amount (history). Never updated in place — each amount
    # change creates a new row. Current version (for a given fee):
    # valid_from <= today AND (valid_until IS NULL OR valid_until >= today).
    __tablename__ = "fee_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(
        ForeignKey("fees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    fee: Mapped["Fee"] = relationship("Fee", back_populates="versions")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    assignments: Mapped[List["FeeAssignment"]] = relationship(
        "FeeAssignment", back_populates="fee_config"
    )


class FeeAssignment(Base):
    # A fee owed by a user for a given period. amount is copied at generation time
    # (snapshot of the fee's current version) so future changes don't affect history.
    # periodicity records how often the fee is applied to the member.
    # Unique (user_id, fee_id, period) makes generation idempotent.
    __tablename__ = "fee_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(
        ForeignKey("fees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    fee_config_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fee_configs.id", ondelete="SET NULL"), nullable=True
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            "pending", "submitted", "paid", "overdue", "cancelled", "exempt",
            name="fee_assignment_status",
        ),
        default="pending",
        nullable=False,
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Proof of payment sent by the member. With no gateway and no bank feed,
    # this is how a transfer becomes visible to the treasurer. `proof_reference`
    # holds what the member typed (the transfer reference), which used to be
    # crammed into `notes` alongside everything else.
    proof_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    proof_reference: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)
    proof_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # Why the treasurer sent it back, so the member knows what to correct.
    proof_rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    fee: Mapped["Fee"] = relationship("Fee", back_populates="assignments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")
    entity: Mapped["Entity"] = relationship(
        "Entity", foreign_keys=[entity_id], back_populates="fee_assignments", lazy="joined"
    )
    fee_config: Mapped[Optional["FeeConfig"]] = relationship(
        "FeeConfig", back_populates="assignments"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "fee_id", "period", name="uq_fee_assignment_user_fee_period"),
        Index("ix_fee_assignments_entity_period", "entity_id", "period"),
        Index("ix_fee_assignments_user", "user_id"),
    )

    @property
    def has_proof(self) -> bool:
        # Exposed instead of proof_path: the storage key is internal, and the
        # file is served through a short-lived signed URL.
        return self.proof_path is not None

    @property
    def fee_name(self) -> Optional[str]:
        return self.fee.name if self.fee else None

    @property
    def periodicity(self) -> Optional[str]:
        # Periodicity is a property of the fee; assignments expose it for display.
        return self.fee.periodicity if self.fee else None


class FeeSubscription(Base):
    """A member's enrolment in a fee: who owes this, from when, and until when.

    Without it, who pays a fee was inferred from who was charged last period —
    `_renew_fee` read the previous period's assignments and repeated them. That
    made the roster a consequence of history rather than a declared fact, with
    three costs: a skipped period broke the chain silently and it never resumed,
    a new member was only charged if somebody remembered to include them in the
    next manual generation, and the question "who is enrolled in this fee?"
    could not be answered without reading last period's charges.

    Generation and renewal now both read from here.
    """

    __tablename__ = "fee_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(
        ForeignKey("fees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalised from the fee, matching FeeAssignment, so tenant filtering
    # does not need a join.
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    # Open-ended while the member keeps paying it.
    ends_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Enrolled but not charged: honorary members (REQ-USR-02), hardship,
    # a member whose family already pays. Deliberately not the same as being
    # unenrolled — the association wants to know it chose not to charge.
    exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exempt_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    fee: Mapped["Fee"] = relationship("Fee", back_populates="subscriptions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")

    __table_args__ = (
        # One enrolment row per member per fee. Leaving and coming back moves
        # the dates rather than adding a row; the charges themselves are the
        # record of what was actually billed.
        UniqueConstraint("fee_id", "user_id", name="uq_fee_subscription_fee_user"),
    )

    def covers(self, day: date) -> bool:
        """Whether this enrolment is in force on `day`."""
        if self.starts_on > day:
            return False
        return self.ends_on is None or self.ends_on >= day


class FeeMaintenanceRun(Base):
    # One row per execution of the daily fee maintenance job (overdue / reminders /
    # renewal). Powers the monitoring view.
    __tablename__ = "fee_maintenance_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum("success", "error", name="fee_maintenance_status"),
        default="success",
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(
        SQLEnum("scheduled", "manual", name="fee_maintenance_trigger"),
        default="scheduled",
        nullable=False,
    )
    triggered_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overdue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reminded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    renewed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    triggered_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[triggered_by_id], lazy="joined"
    )
