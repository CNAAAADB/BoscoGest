from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
import os

SYNC_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:admin123@db:5432/boscoGest")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=True,
    future=True,
)

SyncSessionLocal = sessionmaker(
    sync_engine, 
    class_=Session, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass