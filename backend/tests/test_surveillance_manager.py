import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from backend.ai.contracts import (
    BoundingBox,
    FrameAnalysis,
    TrackAnalysis,
)
from backend.app.database import create_schema
from backend.app.models import DetectionStatus, LiveSurveillanceState
from backend.services.gallery_service import AnalysisRuntime
from backend.services.surveillance_manager import (
    LiveSurveillanceManager,
    SurveillanceAlreadyRunningError,
    SurveillanceCameraInactiveError,
    SurveillanceCameraNotFoundError,
    SurveillanceNotRunningError,
)


class FakeAnalysisEngine:
    def __init__(self):
        self.reset_called = False

    def analyze_frame(self, frame, *, frame_index, timestamp_seconds):
        return FrameAnalysis(
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            width=frame.shape[1],
            height=frame.shape[0],
            tracks=(
                TrackAnalysis(
                    track_id=3,
                    bounding_box=BoundingBox(2, 2, 12, 14),
                    person_confidence=0.91,
                    status=DetectionStatus.KNOWN,
                    member_id=1,
                    similarity=0.78,
                    face_confidence=0.94,
                ),
            ),
        )

    def reset(self):
        self.reset_called = True


class LoopingCapture:
    def __init__(self, source, *, opened=True):
        self.source = source
        self.opened = opened
        self.released = False
        self.frame = np.zeros((20, 30, 3), dtype=np.uint8)

    def isOpened(self):
        return self.opened

    def read(self):
        time.sleep(0.002)
        return self.opened, self.frame.copy()

    def release(self):
        self.released = True


class LiveSurveillanceManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = (
            Path(self.temporary_directory.name) / "surveillance.db"
        )

        connection = self.connection_factory()
        create_schema(connection)
        connection.execute(
            "INSERT INTO people (id, name) VALUES (?, ?)",
            (1, "Known Member"),
        )
        camera = connection.execute(
            """
            INSERT INTO cameras (name, source)
            VALUES (?, ?)
            """,
            ("Laptop Webcam", "0"),
        )
        self.camera_id = int(camera.lastrowid)
        inactive = connection.execute(
            """
            INSERT INTO cameras (name, source, is_active)
            VALUES (?, ?, 0)
            """,
            ("Inactive Webcam", "1"),
        )
        self.inactive_camera_id = int(inactive.lastrowid)
        connection.commit()
        connection.close()

        self.engine = FakeAnalysisEngine()
        self.captures = []

        def capture_factory(source):
            capture = LoopingCapture(source)
            self.captures.append(capture)
            return capture

        self.manager = LiveSurveillanceManager(
            connection_factory=self.connection_factory,
            capture_factory=capture_factory,
            runtime_factory=lambda connection: AnalysisRuntime(
                engine=self.engine,
                member_names={1: "Known Member"},
            ),
            read_failure_limit=2,
            stop_timeout_seconds=1,
        )
        self.addCleanup(self.manager.shutdown)

    def connection_factory(self):
        connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def wait_for(self, predicate, timeout=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.005)
        self.fail("Timed out waiting for surveillance worker")

    def test_start_process_stop_and_persist_known_state_once(self):
        started = self.manager.start(self.camera_id)
        self.wait_for(lambda: self.manager.status().frames_processed >= 2)

        latest = self.manager.latest_analysis()
        frame = self.manager.latest_frame_jpeg()
        stopped = self.manager.stop()

        self.assertEqual(started.state, LiveSurveillanceState.RUNNING)
        self.assertEqual(stopped.state, LiveSurveillanceState.STOPPED)
        self.assertFalse(stopped.running)
        self.assertGreaterEqual(stopped.frames_processed, 2)
        self.assertGreater(stopped.fps, 0)
        self.assertEqual(latest.member_names[1], "Known Member")
        self.assertEqual(latest.analysis.tracks[0].member_id, 1)
        self.assertTrue(frame.startswith(b"\xff\xd8"))
        self.assertTrue(self.captures[0].released)
        self.assertTrue(self.engine.reset_called)

        connection = self.connection_factory()
        session = connection.execute(
            """
            SELECT status, ended_at, frames_processed, average_fps
            FROM surveillance_sessions
            WHERE id = ?
            """,
            (stopped.session_id,),
        ).fetchone()
        log_count = connection.execute(
            "SELECT COUNT(*) FROM detection_logs"
        ).fetchone()[0]
        alert_count = connection.execute(
            "SELECT COUNT(*) FROM alerts"
        ).fetchone()[0]
        connection.close()

        self.assertEqual(session["status"], "stopped")
        self.assertIsNotNone(session["ended_at"])
        self.assertGreaterEqual(session["frames_processed"], 2)
        self.assertGreater(session["average_fps"], 0)
        self.assertEqual(log_count, 1)
        self.assertEqual(alert_count, 0)

    def test_start_rejects_missing_and_inactive_camera(self):
        with self.assertRaises(SurveillanceCameraNotFoundError):
            self.manager.start(999)
        with self.assertRaises(SurveillanceCameraInactiveError):
            self.manager.start(self.inactive_camera_id)

    def test_second_start_is_rejected_and_stop_is_not_idempotent(self):
        self.manager.start(self.camera_id)
        self.wait_for(lambda: self.manager.status().frames_processed >= 1)

        with self.assertRaises(SurveillanceAlreadyRunningError):
            self.manager.start(self.camera_id)

        self.manager.stop()
        with self.assertRaises(SurveillanceNotRunningError):
            self.manager.stop()

    def test_open_failure_marks_session_failed(self):
        manager = LiveSurveillanceManager(
            connection_factory=self.connection_factory,
            capture_factory=lambda source: LoopingCapture(
                source,
                opened=False,
            ),
            runtime_factory=lambda connection: AnalysisRuntime(
                engine=FakeAnalysisEngine(),
                member_names={},
            ),
            stop_timeout_seconds=1,
        )
        self.addCleanup(manager.shutdown)

        started = manager.start(self.camera_id)
        self.wait_for(
            lambda: manager.status().state is LiveSurveillanceState.FAILED
        )
        failed = manager.status()

        self.assertEqual(failed.session_id, started.session_id)
        self.assertFalse(failed.running)
        self.assertIn("Could not open camera source", failed.error_message)

        connection = self.connection_factory()
        session = connection.execute(
            """
            SELECT status, error_message
            FROM surveillance_sessions
            WHERE id = ?
            """,
            (failed.session_id,),
        ).fetchone()
        connection.close()
        self.assertEqual(session["status"], "failed")
        self.assertIn("Could not open camera source", session["error_message"])


if __name__ == "__main__":
    unittest.main()
