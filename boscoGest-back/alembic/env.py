import os
import sys
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool

# Añadir el path de la app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base  # tu Base declarativa
from app.models import *        # importa modelos para que Alembic los detecte

# Configuración Alembic
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def get_database_url() -> str:
    """Obtiene la URL de la DB según el entorno (local o Docker)."""
    return (
        os.getenv("DATABASE_URL")      # si estamos en local
        or os.getenv("DATABASE_URL_DOCKER")  # si estamos en Docker
        or config.get_main_option("sqlalchemy.url")  # fallback
    )

def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo online (sync)."""
    url = get_database_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        future=True
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
