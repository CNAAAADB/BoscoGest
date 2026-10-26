from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase

from app import config

SYNC_DATABASE_URL = config.DATABASE_URL

# SQLite (used by the test-suite) does not support the QueuePool arguments.
_pool_kwargs = {}
if not SYNC_DATABASE_URL.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size": config.DB_POOL_SIZE,
        "max_overflow": config.DB_MAX_OVERFLOW,
        # RDS drops idle connections; recycle and probe before handing one out.
        "pool_recycle": config.DB_POOL_RECYCLE,
        "pool_timeout": config.DB_POOL_TIMEOUT,
        "pool_pre_ping": True,
    }

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=config.SQLALCHEMY_ECHO,
    future=True,
    **_pool_kwargs,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
