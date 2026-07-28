from sqlalchemy import Column, Integer, String, Boolean

from app.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    source_url = Column(String, nullable=True)  # RTSP / webcam index / duong dan video
    is_active = Column(Boolean, default=True)
