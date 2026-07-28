from sqlalchemy import Column, Integer, Float, ForeignKey

from app.database import Base


class Detection(Base):
    """1 dong = 1 lan nhan dien tai 1 frame cu the - thay the file
    annotated_output_detections.csv cua Notebook 02. matched_person_id/match_score o day
    la ket qua THO cua RIENG frame nay, chua qua buffer (xem Track.matched_person_id
    de lay ket qua da qua buffer, dang tin cay hon)."""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    video_session_id = Column(Integer, ForeignKey("video_sessions.id"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)

    frame_number = Column(Integer, nullable=False)
    timestamp_sec = Column(Float, nullable=False)

    bbox_x1 = Column(Integer, nullable=False)
    bbox_y1 = Column(Integer, nullable=False)
    bbox_x2 = Column(Integer, nullable=False)
    bbox_y2 = Column(Integer, nullable=False)

    matched_person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)  # ket qua THO, 1 frame
    match_score = Column(Float, nullable=True)
    person_conf = Column(Float, nullable=True)  # do tin cay YOLOv8 (phat hien "co nguoi")