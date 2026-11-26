from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.entity_model import Entity
from app.models.entity_view_config_model import EntityViewConfig
from app.models.user_model import User
from app.models.membership_model import Membership
from sqlalchemy import select
from app.schemas.entity_view_config import (
    EntityViewConfigUpdate,
    EntityViewConfigBulkUpdate,
    EntityViewConfigResponse,
    EntityViewConfigListResponse,
    VALID_VIEW_NAMES,
)
from app.repositories.view_config_repository import ViewConfigRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db


class ViewConfigService:
    def __init__(self, db: Session):
        self.db = db
        self.config_repo = ViewConfigRepository(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)

    def _ensure_entity_exists(self, entity_id: int) -> Entity:
        entity = self.db.get(Entity, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    def _can_manage_global_statistics(self, current_user: User) -> bool:
        """Only a superadmin appointed to the root Superentity."""
        return any(
            m.is_active and m.entity is not None and m.entity.level == 1
            and m.role is not None and m.role.name == "superadmin"
            for m in current_user.memberships
        ) and self.auth_service.has_root_permission(current_user, "views", "update")

    def _validate_statistics_setting(self, entity_id: int, current_user: User):
        entity = self._ensure_entity_exists(entity_id)
        if entity.level != 1 or not self._can_manage_global_statistics(current_user):
            raise HTTPException(status_code=403, detail="Solo Superadmin en Superentity puede configurar estadísticas")

    def _filter_stats_config(self, configs, entity: Entity, current_user: User):
        if entity.level == 1 and self._can_manage_global_statistics(current_user):
            return list(configs)
        return [c for c in configs if c.view_name != "member_stats"]

    def statistics_availability(self) -> dict:
        """A global switch controlled only by root Superentity administration."""
        root_id = self.auth_service.root_entity_id()
        config = (self.config_repo.get_by_entity_and_view_name(root_id, "member_stats")
                  if root_id is not None else None)
        return {"is_enabled": bool(config and config.is_enabled)}

    def get_entity_view_configs(
        self, entity_id: int, current_user: User
    ) -> EntityViewConfigListResponse:
        entity = self._ensure_entity_exists(entity_id)
        self.auth_service.check_entity_permission(
            current_user, entity_id, "views", "read"
        )

        configs = self.config_repo.get_by_entity_id(entity_id)
        # Backfill newly shipped optional modules for existing tenants, too.
        if not configs:
            configs = self.config_repo.initialize_defaults(entity_id)
            self.db.commit()
        elif self.config_repo.add_missing_defaults(entity_id):
            self.db.commit()
            configs = self.config_repo.get_by_entity_id(entity_id)

        return EntityViewConfigListResponse(
            entity_id=entity_id,
            configs=[EntityViewConfigResponse.model_validate(c) for c in self._filter_stats_config(configs, entity, current_user)],
        )

    def get_enabled_views(
        self, entity_id: int, current_user: User
    ) -> List[EntityViewConfig]:
        self._ensure_entity_exists(entity_id)
        self.auth_service.check_entity_permission(
            current_user, entity_id, "views", "read"
        )

        configs = self.config_repo.get_enabled_by_entity_id(entity_id)
        if not configs:
            all_configs = self.config_repo.initialize_defaults(entity_id)
            self.db.commit()
            configs = [c for c in all_configs if c.is_enabled]

        return self._filter_stats_config(configs, entity, current_user)

    def update_view_config(
        self,
        entity_id: int,
        view_name: str,
        config_in: EntityViewConfigUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityViewConfig:
        if view_name not in VALID_VIEW_NAMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid view name. Valid options: {', '.join(VALID_VIEW_NAMES)}",
            )

        self.auth_service.check_entity_permission(
            current_user, entity_id, "views", "update"
        )
        if view_name == "member_stats":
            self._validate_statistics_setting(entity_id, current_user)

        config = self.config_repo.get_by_entity_and_view_name(entity_id, view_name)
        if not config:
            self.config_repo.add_missing_defaults(entity_id)
            self.db.flush()
            existing = self.config_repo.get_by_entity_id(entity_id)
            if not existing:
                self.config_repo.initialize_defaults(entity_id)
                self.db.flush()
            config = self.config_repo.get_by_entity_and_view_name(
                entity_id, view_name
            )

        if not config:
            raise HTTPException(
                status_code=404, detail="View configuration not found"
            )

        update_data = config_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

        self.db.commit()
        self.db.refresh(config)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="update",
            resource_type="view_config",
            resource_id=config.id,
            details={"view_name": view_name, "entity_id": entity_id, **update_data},
            ip_address=ip_address,
        )

        return config

    def bulk_update_view_configs(
        self,
        entity_id: int,
        configs_in: EntityViewConfigBulkUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityViewConfigListResponse:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "views", "update"
        )

        if any(item.view_name == "member_stats" for item in configs_in.configs):
            self._validate_statistics_setting(entity_id, current_user)

        for config_item in configs_in.configs:
            if config_item.view_name not in VALID_VIEW_NAMES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid view name: {config_item.view_name}. Valid options: {', '.join(VALID_VIEW_NAMES)}",
                )

        entity = self._ensure_entity_exists(entity_id)
        existing_configs = self.config_repo.get_by_entity_id(entity_id)
        if not existing_configs:
            self.config_repo.initialize_defaults(entity_id)
            self.db.flush()
            existing_configs = self.config_repo.get_by_entity_id(entity_id)

        config_map = {c.view_name: c for c in existing_configs}

        updated_configs = []
        for config_item in configs_in.configs:
            if config_item.view_name in config_map:
                config = config_map[config_item.view_name]
                config.display_name = config_item.display_name
                config.is_enabled = config_item.is_enabled
                config.display_order = config_item.display_order
                if config_item.icon:
                    config.icon = config_item.icon
                updated_configs.append(config)

        self.db.commit()

        all_configs = self.config_repo.get_by_entity_id(entity_id)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="bulk_update",
            resource_type="view_config",
            resource_id=entity_id,
            details={
                "entity_id": entity_id,
                "updated_count": len(updated_configs),
            },
            ip_address=ip_address,
        )

        return EntityViewConfigListResponse(
            entity_id=entity_id,
            configs=[EntityViewConfigResponse.model_validate(c) for c in self._filter_stats_config(all_configs, entity, current_user)],
        )

    def reset_view_configs(
        self,
        entity_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> EntityViewConfigListResponse:
        self.auth_service.check_entity_permission(
            current_user, entity_id, "views", "update"
        )

        entity = self._ensure_entity_exists(entity_id)
        if entity.level == 1 and not self._can_manage_global_statistics(current_user):
            raise HTTPException(status_code=403, detail="Solo Superadmin puede restaurar la configuración raíz")
        self.config_repo.delete_by_entity_id(entity_id)
        configs = self.config_repo.initialize_defaults(entity_id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="reset",
            resource_type="view_config",
            resource_id=entity_id,
            details={"entity_id": entity_id},
            ip_address=ip_address,
        )

        return EntityViewConfigListResponse(
            entity_id=entity_id,
            configs=[EntityViewConfigResponse.model_validate(c) for c in self._filter_stats_config(configs, entity, current_user)],
        )


def get_view_config_service(
    db: Session = Depends(get_sync_db),
) -> ViewConfigService:
    return ViewConfigService(db)
