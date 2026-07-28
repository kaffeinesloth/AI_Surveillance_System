import cv2
import numpy as np

from backend.ai.contracts import (
    FrameAnalysis,
    PersonTracker,
    TrackAnalysis,
    TrackFaceRecognizer,
)
from backend.ai.recognition_buffer import TrackRecognitionBuffer
from backend.app.config import FACE_MATCH_THRESHOLD, RECOGNITION_BUFFER_SIZE
from backend.app.models import DetectionStatus


class FrameAnalysisEngine:
    """Shared, non-persistent AI pipeline for one analysis session."""

    def __init__(
        self,
        person_tracker: PersonTracker,
        face_recognizer: TrackFaceRecognizer,
        *,
        match_threshold: float = FACE_MATCH_THRESHOLD,
        recognition_buffer_size: int = RECOGNITION_BUFFER_SIZE,
    ) -> None:
        self.person_tracker = person_tracker
        self.face_recognizer = face_recognizer
        self.recognition_buffer = TrackRecognitionBuffer(
            size=recognition_buffer_size,
            match_threshold=match_threshold,
        )

    def analyze_frame(
        self,
        frame_bgr: np.ndarray,
        *,
        frame_index: int,
        timestamp_seconds: float,
    ) -> FrameAnalysis:
        if frame_bgr is None or frame_bgr.size == 0:
            raise ValueError("Frame cannot be empty")
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("Frame must be a BGR image with three channels")

        height, width = frame_bgr.shape[:2]
        track_analyses: list[TrackAnalysis] = []

        for tracked_person in self.person_tracker.track_frame(frame_bgr):
            bounding_box = tracked_person.bounding_box.clamp(width, height)
            if not bounding_box.is_valid:
                continue

            crop = frame_bgr[
                bounding_box.y1 : bounding_box.y2,
                bounding_box.x1 : bounding_box.x2,
            ]
            observation = self.face_recognizer.observe(crop)

            if not observation.face_detected:
                previous = self.recognition_buffer.decision(
                    tracked_person.track_id
                )
                if previous.status is DetectionStatus.KNOWN:
                    status = previous.status
                    member_id = previous.member_id
                    similarity = previous.similarity
                else:
                    status = DetectionStatus.LOW_QUALITY
                    member_id = None
                    similarity = None
            else:
                raw_similarity = (
                    observation.similarity
                    if observation.similarity is not None
                    else -1.0
                )
                decision = self.recognition_buffer.add(
                    tracked_person.track_id,
                    observation.candidate_member_id,
                    raw_similarity,
                )
                status = decision.status
                member_id = decision.member_id
                similarity = decision.similarity

            track_analyses.append(
                TrackAnalysis(
                    track_id=tracked_person.track_id,
                    bounding_box=bounding_box,
                    person_confidence=tracked_person.confidence,
                    status=status,
                    member_id=member_id,
                    similarity=similarity,
                    face_confidence=observation.face_confidence,
                )
            )

        return FrameAnalysis(
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            width=width,
            height=height,
            tracks=tuple(track_analyses),
        )

    def reset(self) -> None:
        self.recognition_buffer.reset()
        self.person_tracker.reset()


def annotate_frame(
    frame_bgr: np.ndarray,
    analysis: FrameAnalysis,
    *,
    member_names: dict[int, str] | None = None,
) -> np.ndarray:
    annotated = frame_bgr.copy()
    names = member_names or {}
    colors = {
        DetectionStatus.KNOWN: (60, 180, 75),
        DetectionStatus.UNKNOWN: (40, 40, 220),
        DetectionStatus.LOW_QUALITY: (0, 165, 255),
    }

    for track in analysis.tracks:
        box = track.bounding_box
        color = colors[track.status]
        cv2.rectangle(annotated, (box.x1, box.y1), (box.x2, box.y2), color, 2)

        if track.status is DetectionStatus.KNOWN and track.member_id is not None:
            identity = names.get(track.member_id, f"Member {track.member_id}")
        elif track.status is DetectionStatus.UNKNOWN:
            identity = "Unknown"
        else:
            identity = "Face unavailable"

        score = (
            f" {track.similarity:.2f}"
            if track.similarity is not None
            else ""
        )
        label = f"#{track.track_id} {identity}{score}"
        cv2.putText(
            annotated,
            label,
            (box.x1, max(20, box.y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return annotated
