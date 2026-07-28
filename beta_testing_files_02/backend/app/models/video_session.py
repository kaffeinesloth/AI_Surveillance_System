from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class VideoSession(Base):
    """1 'shot' duy nhat theo dung nghia video/scene/shot/frame - vi day la nguon quay
    LIEN TUC tu 1 camera (hoac 1 file video upload), khong co cat canh/doi goc quay giua chung.
    Khong can bang Scene/Shot rieng - VideoSession DA LA don vi "1 shot" do."""
    __tablename__ = "video_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # source_type = Column(String, nullable=False)  # 'upload' | 'stream'
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)  # chi co neu source_type='stream'
    # original_filename = Column(String, nullable=True)  # chi co neu source_type='upload'

    fps = Column(Float, nullable=True)
    frame_width = Column(Integer, nullable=True)
    frame_height = Column(Integer, nullable=True)

    status = Column(String, default="streaming")  # streaming | stopped

    # False cho video upload (tra ket qua thang ve UI, KHONG luu Detection/Track vao DB)
    # True cho stream tu camera (luu day du de xem lai lich su/alert)
    # persist_detections = Column(Boolean, default=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)