from sqlalchemy import Column, Integer, String, ForeignKey, JSON

from app.database import Base


class Zone(Base):
    """Vung cam (ROI tu giac) gan voi 1 camera cu the. Luu duoi dang JSON list cac
    diem [x, y] de khop TRUC TIEP voi dinh dang BehaviorRuleEngine can (xem
    app/services/behavior_rule_engine.py, tham so restricted_zones), khong can
    chuyen doi qua lai."""

    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    polygon = Column(JSON, nullable=False)  # vd: [[100,200],[300,200],[300,400],[100,400]]