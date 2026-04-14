from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.repositories.base_repository import BaseRepository


class EntityRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Entity)

    def get_by_id(self, entity_id: int) -> Optional[Entity]:
        return self.base.get_by_id(entity_id)

    def get_ancestor_chain(self, entity_id: int) -> List[int]:
        """Returns [entity_id, parent_id, ..., root_id] via recursive CTE."""
        result = self.db.execute(
            text("""
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, 0 AS depth
                    FROM entities
                    WHERE id = :entity_id
                    UNION ALL
                    SELECT e.id, e.parent_id, a.depth + 1
                    FROM entities e
                    INNER JOIN ancestors a ON e.id = a.parent_id
                )
                SELECT id FROM ancestors ORDER BY depth ASC
            """),
            {"entity_id": entity_id},
        )
        return [row[0] for row in result]

    def get_parent_entity_ids(self, entity_id: int) -> List[int]:
        """Walk up the parent chain, returning [parent_id, grandparent_id, ...]."""
        parent_ids = []
        current_id = entity_id
        while current_id is not None:
            entity = self.db.execute(
                select(Entity).where(Entity.id == current_id)
            ).scalars().first()
            if not entity or entity.parent_id is None:
                break
            parent_ids.append(entity.parent_id)
            current_id = entity.parent_id
        return parent_ids

    def get_descendant_ids(self, entity_id: int) -> List[int]:
        """Returns all descendant entity IDs (not including entity_id itself)."""
        result = self.db.execute(
            text("""
                WITH RECURSIVE descendants AS (
                    SELECT id FROM entities WHERE parent_id = :entity_id
                    UNION ALL
                    SELECT e.id FROM entities e
                    INNER JOIN descendants d ON e.parent_id = d.id
                )
                SELECT id FROM descendants
            """),
            {"entity_id": entity_id},
        )
        return [row[0] for row in result]

    def get_accessible_entity_ids(self, user) -> List[int]:
        """Returns direct membership entity IDs + all their descendants."""
        direct_ids = set()
        for membership in user.memberships:
            if membership.is_active:
                direct_ids.add(membership.entity_id)

        if not direct_ids:
            return []

        all_ids = set(direct_ids)
        for eid in direct_ids:
            all_ids.update(self.get_descendant_ids(eid))
        return list(all_ids)
