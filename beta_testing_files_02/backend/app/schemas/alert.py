from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertOut(BaseModel):
    id: int
    camera_id: Optional[int]
    person_id: Optional[int]
    alert_type: str
    confidence: Optional[float]
    snapshot_path: Optional[str]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
