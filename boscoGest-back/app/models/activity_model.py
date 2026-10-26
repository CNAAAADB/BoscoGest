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
    # When it starts. Kept as "date" because that is what the API and the app
    # have always called it.
    date = Column(DateTime, nullable=False)
    # When it ends, for activities that last hours or several days. Optional:
    # activities created before it existed have none, and a one-off meeting
    # does not need one.
    end_date = Column(DateTime, nullable=True)
    capacity = Column(Integer, nullable=False)
    price = Column(Float, default=0.0)
    allow_waitlist = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String, nullable=True)

    entity = relationship("Entity", back_populates="activities")
    created_by = relationship("User")
    registrations = relationship("ActivityRegistration", back_populates="activity", cascade="all, delete-orphan")

