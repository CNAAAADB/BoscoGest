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
        """Walk up the parent chain, returning [parent_id, grandparent_id, ...].

        Reuses the ancestor CTE instead of issuing one SELECT per level: with a
        four-level hierarchy that was four round-trips to answer a question the
        database can settle in one.
        """
        chain = self.get_ancestor_chain(entity_id)
        # get_ancestor_chain starts at entity_id itself, which is not a parent.
        return chain[1:]

    def get_descendant_ids(self, entity_id: int) -> List[int]:
        """Returns all descendant entity IDs (not including entity_id itself)."""
        return self.get_descendant_ids_of([entity_id])

    def get_descendant_ids_of(self, entity_ids: List[int]) -> List[int]:
        """Descendants of every given entity, in a single recursive CTE.

        The per-entity variant was called in a loop, so resolving what a user
        can reach cost one recursive CTE per membership. A confederal
        administrator with a membership in each of the 72 seeded entities paid
        72 round-trips on every request that needed their scope.

        Built with the Core rather than raw SQL: the first version used
        `= ANY(:ids)`, which PostgreSQL understands and SQLite does not.
        """
        if not entity_ids:
            return []

        base = (
            select(Entity.id)
            .where(Entity.parent_id.in_(list(entity_ids)))
            .cte("descendants", recursive=True)
        )
        descendants = base.union(
            select(Entity.id).join(base, Entity.parent_id == base.c.id)
        )
        return [row[0] for row in self.db.execute(select(descendants.c.id))]

    def get_accessible_entity_ids(self, user) -> List[int]:
        """Returns direct membership entity IDs + all their descendants."""
        direct_ids = {
            membership.entity_id
            for membership in user.memberships
            if membership.is_active
        }
        if not direct_ids:
            return []

        # UNION rather than UNION ALL in the CTE: overlapping subtrees (a
        # membership in both a federation and one of its associations) would
        # otherwise revisit the same rows.
        return list(direct_ids | set(self.get_descendant_ids_of(list(direct_ids))))
