from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    video_session_id = Column(Integer, ForeignKey("video_sessions.id"), nullable=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)  # null = nguoi la
    alert_type = Column(String, nullable=False)  # unknown_face | zone_intrusion | loitering
    confidence = Column(Float, nullable=True)
    snapshot_path = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
