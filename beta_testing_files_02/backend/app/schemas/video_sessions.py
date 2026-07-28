from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class VideoSession(Base):
    """Chi dai dien cho 1 PHIEN STREAM tu camera - video upload xu ly hoan toan trong
    bo nho, KHONG cham DB (xem app/routers/videos.py). Day chinh la '1 shot' lien tuc
    tu 1 camera, tu luc bat dau den luc dung stream."""

    __tablename__ = "video_sessions"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)  # LUON co - chi con dung cho stream

    fps = Column(Float, nullable=True)
    frame_width = Column(Integer, nullable=True)
    frame_height = Column(Integer, nullable=True)

    status = Column(String, default="streaming")  # streaming | stopped

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)