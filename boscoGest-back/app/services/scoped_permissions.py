"""Entity-scoped authorization for content, financial records and private fields.

Global direct/group grants do not establish an administrative appointment.
Only active membership roles establish scope; inherited permissions go down,
never up or sideways.
"""
from fastapi import HTTPException
from sqlalchemy import select

from app.models.entity_model import Entity
from app.repositories.entity_repository import EntityRepository


class ScopedPermissions:
    def __init__(self, db):
        self.db = db
        self.entities = EntityRepository(db)
        self._cache = {}

    @staticmethod
    def active_memberships(user):
        return [
            m for m in user.memberships
            if m.is_active and m.entity is not None and m.entity.is_active
            and m.role is not None and m.role.is_active
        ]

    def is_root_superadmin(self, user):
        return any(
            m.entity.level == 1 and m.entity.parent_id is None
            and m.role.name == "superadmin"
            for m in self.active_memberships(user)
        )

    def ids(self, user, resource, action, *, inherit=True, wildcard=True):
        key = (user.id, resource, action, inherit, wildcard)
        if key in self._cache:
            return self._cache[key]
        direct, descendants = set(), set()
        for m in self.active_memberships(user):
            if m.entity.level == 1 and m.entity.parent_id is None and m.role.name == "superadmin":
                direct.add(m.entity_id)
                descendants.add(m.entity_id)
                continue
            for p in m.role.permissions:
                if not p.is_active or p.resource != resource:
                    continue
                if p.action != action and not (wildcard and p.action == "manage_all"):
                    continue
                direct.add(m.entity_id)
                if inherit and p.inheritable:
                    descendants.add(m.entity_id)
        candidates = direct | set(self.entities.get_descendant_ids_of(list(descendants)))
        result = set(self.db.scalars(
            select(Entity.id).where(Entity.id.in_(candidates), Entity.is_active.is_(True))
        ).all()) if candidates else set()
        self._cache[key] = result
        return result

    def allows(self, user, entity_id, resource, action, **options):
        return entity_id in self.ids(user, resource, action, **options)

    def require(self, user, entity_id, resource, action, **options):
        if not self.allows(user, entity_id, resource, action, **options):
            raise HTTPException(status_code=403, detail="Permission denied")

    def content_ids(self, user, resource, admin_actions):
        # Automatic parent socio memberships grant access to that parent's
        # published content, not every sibling association's content.
        result = set(self.ids(user, resource, "read", inherit=False))
        for action in admin_actions:
            result.update(self.ids(user, resource, action))
        return result

    def decorate(self, user, rows, resource, actions):
        items = rows if isinstance(rows, list) else [rows]
        permitted = {action: self.ids(user, resource, action) for action in actions}
        for item in items:
            item.permissions = {action: item.entity_id in ids for action, ids in permitted.items()}
        return rows
