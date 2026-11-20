"""Read-only membership overview scoped to the administrator's entity."""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
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
from app.utils.auth import get_current_active_user, get_sync_db

member_stats_router = APIRouter(prefix="/member-stats", tags=["Member statistics"])


def _summarize(users, recent_ids, today):
    users = list({u.id: u for u in users}.values())
    young = sum(
        bool(u.birthdate) and (
            today.year - u.birthdate.year
            - ((today.month, today.day) < (u.birthdate.month, u.birthdate.day))
        ) < 30 for u in users
    )
    return {
        "registered": len(users),
        "under_30": young,
        "incomplete": sum(requires_review(u, contact=True, sensitive=True) for u in users),
        "active_30_days": sum(u.id in recent_ids for u in users),
    }


@member_stats_router.get("/entity/{entity_id}")
def member_statistics(
    entity_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
):
    entity = db.get(Entity, entity_id)
    if not entity or not entity.is_active:
        raise HTTPException(status_code=404, detail="Entity not found")

    authorization = AuthorizationService(db)
    authorization.check_entity_permission(user, entity_id, "users", "manage")

    config = db.execute(select(EntityViewConfig).where(
        EntityViewConfig.entity_id == entity_id,
        EntityViewConfig.view_name == "member_stats",
        EntityViewConfig.is_enabled.is_(True),
    )).scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=403, detail="Statistics view is not enabled")

    descendant_ids = EntityRepository(db).get_descendant_ids(entity_id)
    candidates = db.execute(select(Entity).where(
        Entity.id.in_([entity_id, *descendant_ids]),
        Entity.is_active.is_(True),
    )).scalars().all()
    candidate_ids = {e.id for e in candidates}
    parent_ids = {e.parent_id for e in candidates if e.parent_id in candidate_ids}
    # Local associations are level 4 in BoscoGest; an empty federation is
    # never itself counted as a local association.
    leaves = sorted((e for e in candidates if e.level == 4 and e.id not in parent_ids),
                    key=lambda e: (e.name.lower(), e.id))
    # A parent role does not automatically grant unrestricted cross-entity
    # access; apply the existing effective permission check to every row.
    leaves = [e for e in leaves if authorization.has_effective_permission(
        user, e.id, "users", "manage"
    )]
    leaf_ids = [e.id for e in leaves]

    memberships = db.execute(select(Membership, User).join(
        User, User.id == Membership.user_id
    ).where(
        Membership.entity_id.in_(leaf_ids),
        Membership.is_active.is_(True),
        User.is_active.is_(True),
    )).all() if leaf_ids else []

    by_entity = {entity_id: {} for entity_id in leaf_ids}
    all_users = {}
    for membership, member in memberships:
        by_entity[membership.entity_id][member.id] = member
        all_users[member.id] = member

    cutoff = datetime.utcnow() - timedelta(days=30)
    user_ids = list(all_users)
    recent_ids = set()
    if user_ids:
        recent_ids.update(db.execute(select(AuditLog.user_id).where(
            AuditLog.user_id.in_(user_ids),
            AuditLog.action == "login",
            AuditLog.resource_type == "auth",
            AuditLog.timestamp >= cutoff,
        )).scalars().all())
        recent_ids.update(db.execute(select(RefreshSession.user_id).where(
            RefreshSession.user_id.in_(user_ids),
            RefreshSession.created_at >= cutoff,
        )).scalars().all())

    today = date.today()
    return {
        "entity_id": entity.id,
        "entity_name": entity.name,
        "period_days": 30,
        "totals": _summarize(all_users.values(), recent_ids, today),
        "associations": [
            {
                "entity_id": leaf.id,
                "entity_name": leaf.name,
                **_summarize(by_entity[leaf.id].values(), recent_ids, today),
            }
            for leaf in leaves
        ],
    }
