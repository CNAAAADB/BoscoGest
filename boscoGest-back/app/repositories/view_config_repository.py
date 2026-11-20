from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.entity_view_config_model import EntityViewConfig, DEFAULT_VIEWS
from app.repositories.base_repository import BaseRepository


class ViewConfigRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, EntityViewConfig)

    def get_by_entity_id(self, entity_id: int) -> List[EntityViewConfig]:
        stmt = (
            select(EntityViewConfig)
            .where(EntityViewConfig.entity_id == entity_id)
            .order_by(EntityViewConfig.display_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_enabled_by_entity_id(self, entity_id: int) -> List[EntityViewConfig]:
        stmt = (
            select(EntityViewConfig)
            .where(
                EntityViewConfig.entity_id == entity_id,
                EntityViewConfig.is_enabled == True,
            )
            .order_by(EntityViewConfig.display_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_entity_and_view_name(
        self, entity_id: int, view_name: str
    ) -> Optional[EntityViewConfig]:
        stmt = select(EntityViewConfig).where(
            EntityViewConfig.entity_id == entity_id,
            EntityViewConfig.view_name == view_name,
        )
        return self.db.execute(stmt).scalars().first()

    def initialize_defaults(self, entity_id: int) -> List[EntityViewConfig]:
        configs = []
        for view_data in DEFAULT_VIEWS:
            config = EntityViewConfig(
                entity_id=entity_id,
                view_name=view_data["view_name"],
                display_name=view_data["display_name"],
                display_order=view_data["display_order"],
                icon=view_data.get("icon"),
                is_enabled=view_data.get("is_enabled", True),
            )
            self.db.add(config)
            configs.append(config)
        self.db.flush()
        return configs

    def add_missing_defaults(self, entity_id: int) -> bool:
        """Register newly introduced views without changing tenant choices."""
        existing = {c.view_name for c in self.get_by_entity_id(entity_id)}
        added = False
        for view in DEFAULT_VIEWS:
            if view["view_name"] in existing:
                continue
            self.db.add(EntityViewConfig(
                entity_id=entity_id,
                view_name=view["view_name"],
                display_name=view["display_name"],
                display_order=view["display_order"],
                icon=view.get("icon"),
                is_enabled=view.get("is_enabled", True),
            ))
            added = True
        if added:
            self.db.flush()
        return added

    def delete_by_entity_id(self, entity_id: int) -> None:
        self.db.query(EntityViewConfig).filter(
            EntityViewConfig.entity_id == entity_id
        ).delete()
