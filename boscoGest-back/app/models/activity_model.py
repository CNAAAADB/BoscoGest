from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    price = Column(Float, default=0.0)
    allow_waitlist = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String, nullable=True)

    entity = relationship("Entity", back_populates="activities")
    created_by = relationship("User")
    registrations = relationship("ActivityRegistration", back_populates="activity", cascade="all, delete-orphan")

