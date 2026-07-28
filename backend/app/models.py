from dataclasses import dataclass
from enum import StrEnum


class SurveillanceSessionStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class LiveSurveillanceState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class VideoAnalysisState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DetectionStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    LOW_QUALITY = "low_quality"


class AlertType(StrEnum):
    UNKNOWN_PERSON = "unknown_person"
    RESTRICTED_AREA = "restricted_area"
    LOITERING = "loitering"


@dataclass(frozen=True)
class SavedFaceImage:
    id: int
    image_path: str
    embedding_path: str | None
    created_at: str


@dataclass(frozen=True)
class CameraRecord:
    id: int
    name: str
    source: str
    location: str | None
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SurveillanceSessionRecord:
    id: int
    camera_id: int
    status: SurveillanceSessionStatus
    started_at: str
    ended_at: str | None
    average_fps: float | None
    frames_processed: int
    error_message: str | None


@dataclass(frozen=True)
class DetectionLogRecord:
    id: int
    session_id: int
    camera_id: int
    member_id: int | None
    track_id: int | None
    status: DetectionStatus
    confidence: float | None
    snapshot_path: str | None
    detected_at: str


@dataclass(frozen=True)
class AlertRecord:
    id: int
    session_id: int
    camera_id: int
    detection_log_id: int | None
    member_id: int | None
    alert_type: AlertType
    message: str
    confidence: float | None
    snapshot_path: str | None
    is_read: bool
    created_at: str


@dataclass(frozen=True)
class ZoneRecord:
    id: int
    camera_id: int
    name: str
    polygon_json: str
    is_active: bool
    created_at: str
    updated_at: str
