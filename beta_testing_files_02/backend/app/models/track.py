from sqlalchemy import Column, Integer, Float, ForeignKey

from app.database import Base


class Track(Base):
    """1 dong = 1 nguoi duoc ByteTrack theo doi LIEN TUC trong 1 VideoSession.
    Cot track_id la ID do ByteTrack gan - chi duy nhat TRONG 1 session, khac voi
    id (khoa chinh) la duy nhat toan he thong."""

    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    video_session_id = Column(Integer, ForeignKey("video_sessions.id"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False)  # ID cua ByteTrack, vd: 1, 2, 3... trong session nay

    # Ket qua nhan dang HIEN TAI - DA QUA BUFFER (trung binh N frame gan nhat, xem
    # BUFFER_SIZE o Notebook 02), cap nhat lien tuc khi co detection moi.
    matched_person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    avg_match_score = Column(Float, nullable=True)

    first_seen_frame = Column(Integer, nullable=True)
    first_seen_timestamp = Column(Float, nullable=True)
    last_seen_frame = Column(Integer, nullable=True)
    last_seen_timestamp = Column(Float, nullable=True)