from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from app.models.activity_model import Activity
from app.models.activity_registration_model import ActivityRegistration
from app.models.membership_model import Membership
from app.repositories.base_repository import BaseRepository


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Activity)

    # ── Activity CRUD ───────────────────────────────────────────────

    def get_by_id(self, activity_id: int) -> Optional[Activity]:
        return self.base.get_by_id(activity_id)

    def lock_activity(self, activity_id: int) -> Optional[Activity]:
        stmt = select(Activity).where(Activity.id == activity_id).with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id_with_entity(self, activity_id: int) -> Optional[Activity]:
        """Load activity with its entity relationship eagerly loaded."""
        stmt = (
            select(Activity)
            .options(joinedload(Activity.entity))
            .where(Activity.id == activity_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_entity_ids(
        self,
        entity_ids: List[int],
        with_entity: bool = True,
    ) -> List[Activity]:
        """Return active activities belonging to the given entity IDs."""
        stmt = select(Activity).where(
            Activity.entity_id.in_(entity_ids),
            Activity.is_active == True,
        )
        if with_entity:
            stmt = stmt.options(joinedload(Activity.entity))
        return list(self.db.execute(stmt).scalars().unique().all())

    def get_accessible_entity_ids(self, user_id: int) -> List[int]:
        """Return entity IDs where the user holds any membership."""
        stmt = select(Membership.entity_id).where(
            Membership.user_id == user_id,
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, activity: Activity) -> Activity:
        return self.base.create(activity)

    def soft_delete(self, activity_id: int) -> bool:
        return self.base.soft_delete(activity_id)

    # ── Registration helpers ────────────────────────────────────────

    def get_registration(
        self, activity_id: int, user_id: int
    ) -> Optional[ActivityRegistration]:
        """Get a registration regardless of is_active status."""
        stmt = select(ActivityRegistration).where(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.user_id == user_id,
        )
        return self.db.execute(stmt).scalars().first()

    def get_active_registration(
        self, activity_id: int, user_id: int
    ) -> Optional[ActivityRegistration]:
        """Get a registration only if it is active."""
        stmt = select(ActivityRegistration).where(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.user_id == user_id,
            ActivityRegistration.is_active == True,
        )
        return self.db.execute(stmt).scalars().first()

    def count_occupied_seats(self, activity_id: int) -> int:
        """Count each accepted member and their guests."""
        stmt = (
            select(func.sum(ActivityRegistration.guest_count + 1))
            .select_from(ActivityRegistration)
            .where(
                ActivityRegistration.activity_id == activity_id,
                ActivityRegistration.status == "accepted",
                ActivityRegistration.is_active.is_(True),
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def create_registration(
        self, registration: ActivityRegistration
    ) -> ActivityRegistration:
        self.db.add(registration)
        self.db.flush()
        self.db.refresh(registration)
        return registration
