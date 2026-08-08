import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.ai.contracts import (
    BoundingBox,
    FrameAnalysis,
    TrackAnalysis,
)
from backend.app.database import create_schema
from backend.app.models import DetectionStatus
from backend.services.live_event_service import LiveEventRecorder


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


def make_track(
    *,
    track_id=1,
    status=DetectionStatus.UNKNOWN,
    member_id=None,
    similarity=0.20,
):
    return TrackAnalysis(
        track_id=track_id,
        bounding_box=BoundingBox(1, 1, 10, 12),
        person_confidence=0.9,
        status=status,
        member_id=member_id,
        similarity=similarity,
        face_confidence=0.92,
    )


def make_analysis(frame_index, timestamp, *tracks):
    return FrameAnalysis(
        frame_index=frame_index,
        timestamp_seconds=timestamp,
        width=20,
        height=16,
        tracks=tuple(tracks),
    )


class LiveEventRecorderTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = make_connection()
        self.addCleanup(self.connection.close)
        camera = self.connection.execute(
            "INSERT INTO cameras (name, source) VALUES (?, ?)",
            ("Laptop Webcam", "0"),
        )
        session = self.connection.execute(
            """
            INSERT INTO surveillance_sessions (camera_id)
            VALUES (?)
            """,
            (camera.lastrowid,),
        )
        member = self.connection.execute(
            "INSERT INTO people (name) VALUES (?)",
            ("Known Member",),
        )
        self.connection.commit()
        self.camera_id = int(camera.lastrowid)
        self.session_id = int(session.lastrowid)
        self.member_id = int(member.lastrowid)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.snapshots_dir = Path(self.temporary_directory.name)

    def recorder(self, *, confirmation=3, cooldown=10):
        return LiveEventRecorder(
            self.connection,
            session_id=self.session_id,
            camera_id=self.camera_id,
            snapshots_dir=self.snapshots_dir,
            unknown_confirmation_frames=confirmation,
            alert_cooldown_seconds=cooldown,
        )

    def counts(self):
        logs = self.connection.execute(
            "SELECT COUNT(*) FROM detection_logs"
        ).fetchone()[0]
        alerts = self.connection.execute(
            "SELECT COUNT(*) FROM alerts"
        ).fetchone()[0]
        return logs, alerts

    def test_known_identity_is_logged_once_until_it_changes(self):
        recorder = self.recorder()
        known = make_track(
            status=DetectionStatus.KNOWN,
            member_id=self.member_id,
            similarity=0.78,
        )

        recorder.process(make_analysis(0, 0.0, known), b"jpeg")
        recorder.process(make_analysis(1, 0.1, known), b"jpeg")

        self.assertEqual(self.counts(), (1, 0))
        row = self.connection.execute(
            "SELECT status, member_id, snapshot_path FROM detection_logs"
        ).fetchone()
        self.assertEqual(row["status"], "known")
        self.assertEqual(row["member_id"], self.member_id)
        self.assertIsNone(row["snapshot_path"])
        self.assertEqual(list(self.snapshots_dir.iterdir()), [])

    def test_unknown_requires_confirmation_and_alerts_once_per_visible_track(self):
        recorder = self.recorder(confirmation=3, cooldown=10)
        unknown = make_track()

        self.assertEqual(
            recorder.process(make_analysis(0, 0.0, unknown), b"jpeg-0"),
            [],
        )
        self.assertEqual(
            recorder.process(make_analysis(1, 1.0, unknown), b"jpeg-1"),
            [],
        )
        first = recorder.process(
            make_analysis(2, 2.0, unknown),
            b"jpeg-2",
        )
        within_cooldown = recorder.process(
            make_analysis(3, 5.0, unknown),
            b"jpeg-3",
        )
        repeated_after_cooldown = recorder.process(
            make_analysis(4, 12.0, unknown),
            b"jpeg-4",
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(within_cooldown, [])
        self.assertEqual(repeated_after_cooldown, [])
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(len(list(self.snapshots_dir.glob("*.jpg"))), 1)

    def test_unknown_track_can_alert_again_after_it_disappears(self):
        recorder = self.recorder(confirmation=1, cooldown=3)
        unknown = make_track()

        first = recorder.process(make_analysis(0, 0.0, unknown), b"jpeg-0")
        recorder.process(make_analysis(1, 1.0), b"jpeg-1")
        second = recorder.process(make_analysis(2, 4.0, unknown), b"jpeg-2")

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(self.counts(), (2, 2))

    def test_low_quality_frame_does_not_increment_unknown_streak(self):
        recorder = self.recorder(confirmation=3)
        unknown = make_track()
        low_quality = make_track(
            status=DetectionStatus.LOW_QUALITY,
            similarity=None,
        )

        recorder.process(make_analysis(0, 0.0, unknown), b"jpeg")
        recorder.process(make_analysis(1, 1.0, low_quality), b"jpeg")
        recorder.process(make_analysis(2, 2.0, unknown), b"jpeg")

        self.assertEqual(self.counts(), (0, 0))

        recorder.process(make_analysis(3, 3.0, unknown), b"jpeg")
        self.assertEqual(self.counts(), (1, 1))

    def test_simultaneous_unknown_alerts_share_one_snapshot(self):
        recorder = self.recorder(confirmation=1)
        events = recorder.process(
            make_analysis(
                0,
                0.0,
                make_track(track_id=1),
                make_track(track_id=2),
            ),
            b"same-frame",
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(self.counts(), (2, 2))
        self.assertEqual(
            len({event.snapshot_path for event in events}),
            1,
        )
        self.assertEqual(len(list(self.snapshots_dir.glob("*.jpg"))), 1)

    def test_database_failure_removes_new_snapshot(self):
        recorder = LiveEventRecorder(
            self.connection,
            session_id=999,
            camera_id=self.camera_id,
            snapshots_dir=self.snapshots_dir,
            unknown_confirmation_frames=1,
        )

        with self.assertRaises(sqlite3.IntegrityError):
            recorder.process(
                make_analysis(0, 0.0, make_track()),
                b"temporary-snapshot",
            )

        self.assertEqual(list(self.snapshots_dir.iterdir()), [])
        self.assertEqual(self.counts(), (0, 0))


if __name__ == "__main__":
    unittest.main()
