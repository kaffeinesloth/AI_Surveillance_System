from dataclasses import dataclass
from typing import Protocol

import numpy as np

from backend.app.models import DetectionStatus


@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def clamp(self, width: int, height: int) -> "BoundingBox":
        return BoundingBox(
            x1=max(0, min(self.x1, width)),
            y1=max(0, min(self.y1, height)),
            x2=max(0, min(self.x2, width)),
            y2=max(0, min(self.y2, height)),
        )

    @property
    def is_valid(self) -> bool:
        return self.x2 > self.x1 and self.y2 > self.y1


@dataclass(frozen=True)
class TrackedPerson:
    track_id: int
    bounding_box: BoundingBox
    confidence: float


@dataclass(frozen=True)
class FaceObservation:
    face_detected: bool
    candidate_member_id: int | None
    similarity: float | None
    face_confidence: float | None


@dataclass(frozen=True)
class TrackAnalysis:
    track_id: int
    bounding_box: BoundingBox
    person_confidence: float
    status: DetectionStatus
    member_id: int | None
    similarity: float | None
    face_confidence: float | None


@dataclass(frozen=True)
class FrameAnalysis:
    frame_index: int
    timestamp_seconds: float
    width: int
    height: int
    tracks: tuple[TrackAnalysis, ...]


class PersonTracker(Protocol):
    def track_frame(self, frame_bgr: np.ndarray) -> list[TrackedPerson]:
        ...

    def reset(self) -> None:
        ...


class TrackFaceRecognizer(Protocol):
    def observe(self, person_crop_bgr: np.ndarray) -> FaceObservation:
        ...
