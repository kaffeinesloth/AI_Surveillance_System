from dataclasses import dataclass

from backend.ai.contracts import FrameAnalysis
from backend.app.config import (
    ALERT_COOLDOWN_SECONDS,
    UNKNOWN_CONFIRMATION_FRAMES,
    VIDEO_ANALYSIS_MAX_EVENTS,
)
from backend.app.models import DetectionStatus


@dataclass
class _TemporaryTrackState:
    unknown_streak: int = 0
    last_log_key: tuple[str, int | None] | None = None
    last_unknown_event_at: float | None = None


class TemporaryEventCollector:
    def __init__(
        self,
        *,
        member_names: dict[int, str],
        unknown_confirmation_frames: int = UNKNOWN_CONFIRMATION_FRAMES,
        unknown_cooldown_seconds: float = ALERT_COOLDOWN_SECONDS,
        max_events: int = VIDEO_ANALYSIS_MAX_EVENTS,
    ) -> None:
        if unknown_confirmation_frames <= 0:
            raise ValueError("Unknown confirmation frames must be positive")
        if unknown_cooldown_seconds < 0:
            raise ValueError("Unknown cooldown cannot be negative")
        if max_events <= 0:
            raise ValueError("Maximum temporary events must be positive")
        self.member_names = member_names
        self.unknown_confirmation_frames = unknown_confirmation_frames
        self.unknown_cooldown_seconds = unknown_cooldown_seconds
        self.max_events = max_events
        self.events: list[dict] = []
        self.total_known_events = 0
        self.total_unknown_events = 0
        self.events_truncated = False
        self._track_states: dict[int, _TemporaryTrackState] = {}

    def process(self, analysis: FrameAnalysis) -> list[dict]:
        new_events = []
        for track in analysis.tracks:
            state = self._track_states.setdefault(
                track.track_id,
                _TemporaryTrackState(),
            )
            if (
                track.status is DetectionStatus.KNOWN
                and track.member_id is not None
            ):
                state.unknown_streak = 0
                key = (DetectionStatus.KNOWN.value, track.member_id)
                if state.last_log_key == key:
                    continue
                state.last_log_key = key
                event = self._event(
                    analysis,
                    track.track_id,
                    DetectionStatus.KNOWN,
                    track.member_id,
                    track.similarity,
                    "detection",
                )
                self.total_known_events += 1
                new_events.append(event)
                continue

            if track.status is DetectionStatus.UNKNOWN:
                state.unknown_streak += 1
                if state.unknown_streak < self.unknown_confirmation_frames:
                    continue
                event_due = (
                    state.last_unknown_event_at is None
                    or analysis.timestamp_seconds
                    - state.last_unknown_event_at
                    >= self.unknown_cooldown_seconds
                )
                if not event_due:
                    continue
                state.last_log_key = (DetectionStatus.UNKNOWN.value, None)
                state.last_unknown_event_at = analysis.timestamp_seconds
                event = self._event(
                    analysis,
                    track.track_id,
                    DetectionStatus.UNKNOWN,
                    None,
                    track.similarity,
                    "unknown_person",
                )
                self.total_unknown_events += 1
                new_events.append(event)

        self.events.extend(new_events)
        if len(self.events) > self.max_events:
            overflow = len(self.events) - self.max_events
            del self.events[:overflow]
            self.events_truncated = True
        return new_events

    def _event(
        self,
        analysis: FrameAnalysis,
        track_id: int,
        status: DetectionStatus,
        member_id: int | None,
        similarity: float | None,
        event_type: str,
    ) -> dict:
        return {
            "frame_index": analysis.frame_index,
            "timestamp_seconds": analysis.timestamp_seconds,
            "track_id": track_id,
            "status": status,
            "member_id": member_id,
            "member_name": (
                self.member_names.get(member_id)
                if member_id is not None
                else None
            ),
            "similarity": similarity,
            "event_type": event_type,
        }
