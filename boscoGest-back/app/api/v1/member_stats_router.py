"""Scoped, read-only membership statistics and permission-checked drill-downs."""
from datetime import date, datetime, timedelta
from typing import Literal
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity_model import Entity
from app.models.entity_view_config_model import EntityViewConfig
from app.models.membership_model import Membership
from app.models.user_model import User
from app.models.audit_log_model import AuditLog
from app.models.refresh_session_model import RefreshSession
from app.repositories.entity_repository import EntityRepository
from app.services.authorization_service import AuthorizationService
from app.services.member_review import requires_review
from app.services.user_visibility import UserVisibility
from app.utils.auth import get_current_active_user, get_sync_db

member_stats_router = APIRouter(prefix="/member-stats", tags=["Member statistics"])
Period = Literal["all", "90d", "30d", "7d"]
Metric = Literal["registered", "under_30", "incomplete", "active_30_days"]
PERIOD_DAYS = {"all": None, "90d": 90, "30d": 30, "7d": 7}


def _young(u: User, today: date) -> bool:
    return bool(u.birthdate) and (
        today.year - u.birthdate.year
        - ((today.month, today.day) < (u.birthdate.month, u.birthdate.day))
    ) < 30


def _matches(u: User, metric: Metric, recent_ids: set[int], today: date,
             cutoff: datetime | None = None) -> bool:
    # Each card is a filter on the same population: active memberships in local
    # associations, deduplicated by user. For finite periods, the first three
    # cards describe users registered within that period. Activity describes
    # users who logged in or opened/renewed a session during the period.
    if metric == "active_30_days":
        return u.id in recent_ids
    if cutoff is not None and (not u.created_at or u.created_at < cutoff):
        return False
    if metric == "registered":
        return True
    if metric == "under_30":
        return _young(u, today)
    return requires_review(u, contact=True, sensitive=True)


def _summarize(users, recent_ids, today, cutoff=None):
    users = list({u.id: u for u in users}.values())
    return {metric: sum(_matches(u, metric, recent_ids, today, cutoff) for u in users)
            for metric in ("registered", "under_30", "incomplete", "active_30_days")}


def _data(entity_id: int, period: Period, user: User, db: Session):
    entity = db.get(Entity, entity_id)
    if not entity or not entity.is_active:
        raise HTTPException(status_code=404, detail="Entity not found")
    auth = AuthorizationService(db)
    auth.check_entity_permission(user, entity_id, "users", "manage")
    enabled = db.execute(select(EntityViewConfig).where(
        EntityViewConfig.entity_id == entity_id,
        EntityViewConfig.view_name == "member_stats",
        EntityViewConfig.is_enabled.is_(True),
    )).scalar_one_or_none()
    if not enabled:
        raise HTTPException(status_code=403, detail="Statistics view is not enabled")

    descendants = EntityRepository(db).get_descendant_ids(entity_id)
    candidates = db.execute(select(Entity).where(
        Entity.id.in_([entity_id, *descendants]),
        Entity.level == 4, Entity.is_active.is_(True),
    )).scalars().all()
    # Always enforce effective entity-level permissions per local association.
    leaves = sorted((e for e in candidates if auth.has_effective_permission(
        user, e.id, "users", "manage")), key=lambda e: (e.name.lower(), e.id))
    local_ids = [e.id for e in leaves]
    memberships = db.execute(select(Membership, User).join(
        User, User.id == Membership.user_id
    ).where(
        Membership.entity_id.in_(local_ids),
        Membership.is_active.is_(True),
        User.is_active.is_(True),
    )).all() if local_ids else []
    by_entity: dict[int, dict[int, User]] = {e.id: {} for e in leaves}
    all_users: dict[int, User] = {}
    for m, member in memberships:
        by_entity[m.entity_id][member.id] = member
        all_users[member.id] = member

    days = PERIOD_DAYS[period]
    cutoff = datetime.utcnow() - timedelta(days=days) if days is not None else None
    ids = list(all_users)
    recent_ids: set[int] = set()
    if ids:
        audit = select(AuditLog.user_id).where(
            AuditLog.user_id.in_(ids),
            AuditLog.action == "login",
            AuditLog.resource_type == "auth",
        )
        sessions = select(RefreshSession.user_id).where(RefreshSession.user_id.in_(ids))
        if cutoff:
            audit = audit.where(AuditLog.timestamp >= cutoff)
            sessions = sessions.where(RefreshSession.created_at >= cutoff)
        recent_ids.update(db.execute(audit).scalars().all())
        recent_ids.update(db.execute(sessions).scalars().all())
    return entity, leaves, by_entity, all_users, recent_ids, cutoff


@member_stats_router.get("/entity/{entity_id}")
def member_statistics(
    entity_id: int,
    period: Period = Query("30d"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    entity, leaves, by_entity, all_users, recent_ids, cutoff = _data(
        entity_id, period, user, db
    )
    today = date.today()
    return {
        "entity_id": entity.id, "entity_name": entity.name,
        "period": period, "period_days": PERIOD_DAYS[period],
        "totals": _summarize(all_users.values(), recent_ids, today, cutoff),
        "associations": [
            {"entity_id": leaf.id, "entity_name": leaf.name,
             **_summarize(by_entity[leaf.id].values(), recent_ids, today, cutoff)}
            for leaf in leaves
        ],
    }


@member_stats_router.get("/entity/{entity_id}/members")
def member_statistics_members(
    entity_id: int,
    metric: Metric = Query(...),
    period: Period = Query("30d"),
    association_id: int | None = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    _, leaves, by_entity, all_users, recent_ids, cutoff = _data(
        entity_id, period, user, db
    )
    if association_id is not None and association_id not in by_entity:
        raise HTTPException(status_code=403, detail="Association is outside your scope")
    population = (by_entity[association_id].values() if association_id is not None
                  else all_users.values())
    today = date.today()
    filtered = sorted(
        (u for u in population if _matches(u, metric, recent_ids, today, cutoff)),
        key=lambda u: (u.surname.lower(), u.name.lower(), u.id),
    )
    visibility = UserVisibility.for_viewer(AuthorizationService(db), user)
    if search and search.strip():
        # Searching hidden DNI/phone values could disclose protected data.
        def normalize(value):
            return "".join(ch for ch in unicodedata.normalize(
                "NFKD", str(value or "").casefold()
            ) if not unicodedata.combining(ch))

        query = normalize(search.strip())
        def matches_search(member):
            allowed = visibility.serialize(member, viewer_id=user.id)
            return any(query in normalize(value) for value in (
                allowed.id, allowed.name, allowed.surname, allowed.email,
                allowed.phone, allowed.dni,
            ))
        filtered = [member for member in filtered if matches_search(member)]
    return {
        "total": len(filtered), "skip": skip, "limit": limit,
        # Same schema and field-level permissions as Admin > Usuarios. Reuse its
        # existing table instead of introducing a different user-list format.
        "items": [visibility.serialize(member, viewer_id=user.id)
                  for member in filtered[skip:skip + limit]],
    }
