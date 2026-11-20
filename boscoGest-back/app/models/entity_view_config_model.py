from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EntityViewConfig(Base):
    """
    Configuración de vistas por entidad.
    Permite activar/desactivar, renombrar y reordenar las vistas del menú.

    Vistas disponibles (view_name):
    - dashboard: Panel principal
    - users: Gestión de usuarios
    - entities: Gestión de entidades
    - roles: Gestión de roles
    - activities: Calendario y actividades
    - communications: Noticias
    - magazines: Revistas PDF
    - resources: Recursos formativos
    - chat: Chat
    - shop: Tienda
    - fees: Cuotas
    - payments: Pagos
    - settings: Configuración

    Nota: "profile" (Perfil) siempre está activo según el SRS.
    """
    __tablename__ = "entity_view_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True
    )

    # Identificador interno de la vista (no cambia)
    view_name: Mapped[str] = mapped_column(String(50), index=True)

    # Nombre personalizado para mostrar en el menú
    display_name: Mapped[str] = mapped_column(String(100))

    # Si la vista está habilitada para esta entidad
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Orden de aparición en el menú (menor = primero)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # Icono personalizado (nombre del icono de Material Icons)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Constraint único: una sola configuración por vista por entidad
    __table_args__ = (
        UniqueConstraint('entity_id', 'view_name', name='uq_entity_view'),
    )

    # Relación con Entity
    entity: Mapped["Entity"] = relationship("Entity", back_populates="view_configs")


# Vistas predefinidas del sistema con sus valores por defecto
DEFAULT_VIEWS = [
    {"view_name": "dashboard", "display_name": "Dashboard", "display_order": 1, "icon": "dashboard"},
    {"view_name": "member_stats", "display_name": "Estadísticas de socios", "display_order": 2, "icon": "insights", "is_enabled": False},
    {"view_name": "users", "display_name": "Usuarios", "display_order": 2, "icon": "people"},
    {"view_name": "entities", "display_name": "Asociaciones", "display_order": 3, "icon": "business"},
    {"view_name": "roles", "display_name": "Roles", "display_order": 4, "icon": "admin_panel_settings"},
    {"view_name": "activities", "display_name": "Actividades", "display_order": 5, "icon": "event"},
    {"view_name": "communications", "display_name": "Noticias", "display_order": 6, "icon": "newspaper"},
    {"view_name": "magazines", "display_name": "Revistas", "display_order": 7, "icon": "menu_book"},
    {"view_name": "resources", "display_name": "Recursos", "display_order": 8, "icon": "school", "is_enabled": False},
    {"view_name": "chat", "display_name": "Chat", "display_order": 9, "icon": "chat", "is_enabled": False},
    {"view_name": "shop", "display_name": "Tienda", "display_order": 10, "icon": "store", "is_enabled": False},
    {"view_name": "fees", "display_name": "Cuotas", "display_order": 11, "icon": "payments", "is_enabled": False},
    {"view_name": "payments", "display_name": "Pagos", "display_order": 12, "icon": "account_balance", "is_enabled": False},
    {"view_name": "settings", "display_name": "Configuración", "display_order": 99, "icon": "settings"},
]
