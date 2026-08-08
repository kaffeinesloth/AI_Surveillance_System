import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.ai.contracts import FrameAnalysis, TrackAnalysis
from backend.app.config import (
    ALERT_COOLDOWN_SECONDS,
    SNAPSHOTS_DIR,
    UNKNOWN_CONFIRMATION_FRAMES,
    serialize_storage_path,
)
from backend.app.models import AlertType, DetectionStatus


@dataclass
class _TrackEventState:
    unknown_streak: int = 0
    last_log_key: tuple[str, int | None] | None = None
    last_alert_at: float | None = None
    last_seen_at: float | None = None
    unknown_alert_recorded: bool = False


@dataclass(frozen=True)
class PersistedAlertEvent:
    alert_id: int
    detection_log_id: int
    track_id: int
    snapshot_path: str


class LiveEventRecorder:
    """Persist selected events from live mode only."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: int,
        camera_id: int,
        snapshots_dir: Path = SNAPSHOTS_DIR,
        unknown_confirmation_frames: int = UNKNOWN_CONFIRMATION_FRAMES,
        alert_cooldown_seconds: float = ALERT_COOLDOWN_SECONDS,
    ) -> None:
        if unknown_confirmation_frames <= 0:
            raise ValueError("Unknown confirmation frames must be positive")
        if alert_cooldown_seconds < 0:
            raise ValueError("Alert cooldown cannot be negative")
        self.connection = connection
        self.session_id = session_id
        self.camera_id = camera_id
        self.snapshots_dir = snapshots_dir
        self.unknown_confirmation_frames = unknown_confirmation_frames
        self.alert_cooldown_seconds = alert_cooldown_seconds
        self.track_state_ttl_seconds = max(alert_cooldown_seconds, 1.0)
        self._track_states: dict[int, _TrackEventState] = {}

    def process(
        self,
        analysis: FrameAnalysis,
        annotated_frame_jpeg: bytes,
    ) -> list[PersistedAlertEvent]:
        pending_logs: list[TrackAnalysis] = []
        pending_alerts: list[TrackAnalysis] = []
        stale_track_ids = [
            track_id
            for track_id, state in self._track_states.items()
            if state.last_seen_at is not None
            and analysis.timestamp_seconds - state.last_seen_at
            >= self.track_state_ttl_seconds
        ]
        for track_id in stale_track_ids:
            self._track_states.pop(track_id, None)

        for track in analysis.tracks:
            state = self._track_states.setdefault(
                track.track_id,
                _TrackEventState(),
            )
            state.last_seen_at = analysis.timestamp_seconds
            if (
                track.status is DetectionStatus.KNOWN
                and track.member_id is not None
            ):
                state.unknown_streak = 0
                state.unknown_alert_recorded = False
                key = (DetectionStatus.KNOWN.value, track.member_id)
                if state.last_log_key != key:
                    pending_logs.append(track)
                continue

            if track.status is DetectionStatus.UNKNOWN:
                state.unknown_streak += 1
                if state.unknown_streak < self.unknown_confirmation_frames:
                    continue
                if state.unknown_alert_recorded:
                    continue
                alert_due = (
                    state.last_alert_at is None
                    or analysis.timestamp_seconds - state.last_alert_at
                    >= self.alert_cooldown_seconds
                )
                if alert_due:
                    pending_logs.append(track)
                    pending_alerts.append(track)

        if not pending_logs:
            return []

        snapshot_path = None
        if pending_alerts:
            snapshot_path = self._save_snapshot(
                annotated_frame_jpeg,
                analysis,
            )

        persisted_alerts: list[PersistedAlertEvent] = []
        detected_at = datetime.now(timezone.utc).isoformat()
        try:
            for track in pending_logs:
                is_alert = track in pending_alerts
                log_snapshot_path = snapshot_path if is_alert else None
                log_cursor = self.connection.execute(
                    """
                    INSERT INTO detection_logs (
                        session_id,
                        camera_id,
                        member_id,
                        track_id,
                        status,
                        confidence,
                        snapshot_path,
                        detected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.session_id,
                        self.camera_id,
                        track.member_id,
                        track.track_id,
                        track.status.value,
                        track.similarity,
                        log_snapshot_path,
                        detected_at,
                    ),
                )
                detection_log_id = int(log_cursor.lastrowid)

                if is_alert and snapshot_path is not None:
                    alert_cursor = self.connection.execute(
                        """
                        INSERT INTO alerts (
                            session_id,
                            camera_id,
                            detection_log_id,
                            member_id,
                            alert_type,
                            message,
                            confidence,
                            snapshot_path,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self.session_id,
                            self.camera_id,
                            detection_log_id,
                            None,
                            AlertType.UNKNOWN_PERSON.value,
                            f"Unknown person detected on track {track.track_id}",
                            track.similarity,
                            snapshot_path,
                            detected_at,
                        ),
                    )
                    persisted_alerts.append(
                        PersistedAlertEvent(
                            alert_id=int(alert_cursor.lastrowid),
                            detection_log_id=detection_log_id,
                            track_id=track.track_id,
                            snapshot_path=snapshot_path,
                        )
                    )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            if snapshot_path is not None:
                self._delete_snapshot(snapshot_path)
            raise

        for track in pending_logs:
            state = self._track_states[track.track_id]
            state.last_log_key = (track.status.value, track.member_id)
            if track in pending_alerts:
                state.last_alert_at = analysis.timestamp_seconds
                state.unknown_alert_recorded = True
        return persisted_alerts

    def _save_snapshot(
        self,
        content: bytes,
        analysis: FrameAnalysis,
    ) -> str:
        if not content:
            raise ValueError("Annotated snapshot cannot be empty")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        filename = (
            f"session_{self.session_id}_frame_{analysis.frame_index}_"
            f"{timestamp}_{uuid4().hex}.jpg"
        )
        target = self.snapshots_dir / filename
        temporary = target.with_suffix(".tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return serialize_storage_path(target)

    @staticmethod
    def _delete_snapshot(stored_path: str) -> None:
        from backend.app.config import resolve_storage_path

        path = resolve_storage_path(stored_path)
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass
