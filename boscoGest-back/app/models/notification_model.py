from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )

    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_id], lazy="joined"
    )
    actor: Mapped[Optional["User"]] = relationship(
        foreign_keys=[actor_id], lazy="joined"
    )
    entity: Mapped["Entity"] = relationship(lazy="joined")

    __table_args__ = (
        Index(
            "ix_notifications_recipient_unread",
            "recipient_id",
            "is_read",
            "created_at",
        ),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Por defecto activo, igual que el aviso in-app: quien no quiera push lo
    # desactiva por tipo de evento, o retira el permiso desde el sistema. Una
    # preferencia que empieza apagada no la enciende casi nadie, y entonces la
    # función no existe en la práctica.
    push_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="true"
    )

    user: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "event_type", name="uq_user_event_pref"),
    )


class DeviceToken(Base):
    """Un dispositivo al que se le pueden enviar notificaciones push.

    Una persona puede tener varios: el móvil y la tablet, o el mismo móvil tras
    reinstalar la app. Por eso la clave única es el token, no el usuario.

    El token lo emite el servicio del fabricante (FCM), no nosotros, y cambia
    solo: al reinstalar, al restaurar una copia de seguridad o cuando al
    sistema le apetece. Reaparece entonces como un alta nueva, y el anterior
    deja de valer — de ahí que los envíos rechazados tengan que limpiarlo.
    """

    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Los tokens de FCM rondan los 160 caracteres, pero no hay longitud
    # garantizada: Text evita que un cambio de formato los trunque en silencio.
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
    # Se refresca en cada arranque de la app. Sirve para purgar dispositivos
    # que llevan meses sin aparecer, que son casi siempre bajas silenciosas.
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="joined")
