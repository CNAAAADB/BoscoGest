from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, TIMESTAMP, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EntityBranding(Base):
    """
    Configuración de branding personalizado por entidad.
    Permite a cada entidad tener su propia identidad visual.
    """
    __tablename__ = "entity_brandings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )

    # Subdominio para acceso personalizado (ej: "madrid" -> madrid.boscogest.es)
    subdomain: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)

    # Logo de la entidad (URL o path al archivo)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Colores del tema
    primary_color: Mapped[str] = mapped_column(String(7), default="#1976d2")  # Color principal (hex)
    secondary_color: Mapped[str] = mapped_column(String(7), default="#424242")  # Color secundario (hex)
    accent_color: Mapped[str] = mapped_column(String(7), default="#ff4081")  # Color de acento (hex)

    # Nombre personalizado para mostrar (si difiere del nombre de la entidad)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Descripción corta o slogan
    tagline: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Footer personalizado (texto HTML permitido)
    custom_footer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relación con Entity (1:1)
    entity: Mapped["Entity"] = relationship("Entity", back_populates="branding")
