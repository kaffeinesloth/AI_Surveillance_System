import unittest

from pydantic import ValidationError

from backend.app.models import AlertType, DetectionStatus, SurveillanceSessionStatus
from backend.app.schemas import (
    Alert,
    CameraCreate,
    DetectionLog,
    SurveillanceSession,
    ZoneCreate,
)


class SurveillanceSchemaTestCase(unittest.TestCase):
    def test_camera_requires_name_and_source(self):
        with self.assertRaises(ValidationError):
            CameraCreate(name="", source="0")

        with self.assertRaises(ValidationError):
            CameraCreate(name="Laptop Webcam", source="")

    def test_zone_requires_at_least_three_points(self):
        with self.assertRaises(ValidationError):
            ZoneCreate(
                camera_id=1,
                name="Invalid Zone",
                points=[
                    {"x": 0, "y": 0},
                    {"x": 100, "y": 0},
                ],
            )

    def test_typed_live_records_accept_supported_values(self):
        session = SurveillanceSession(
            id=1,
            camera_id=1,
            status="running",
            started_at="2026-07-28 10:00:00",
            ended_at=None,
            average_fps=None,
            frames_processed=0,
            error_message=None,
        )
        log = DetectionLog(
            id=1,
            session_id=1,
            camera_id=1,
            member_id=None,
            track_id=7,
            status="unknown",
            confidence=0.22,
            snapshot_path=None,
            detected_at="2026-07-28 10:00:05",
        )
        alert = Alert(
            id=1,
            session_id=1,
            camera_id=1,
            detection_log_id=1,
            member_id=None,
            alert_type="unknown_person",
            message="Unknown person detected",
            confidence=0.22,
            snapshot_path="data/snapshots/alert.jpg",
            is_read=False,
            created_at="2026-07-28 10:00:05",
        )

        self.assertEqual(session.status, SurveillanceSessionStatus.RUNNING)
        self.assertEqual(log.status, DetectionStatus.UNKNOWN)
        self.assertEqual(alert.alert_type, AlertType.UNKNOWN_PERSON)

    def test_typed_live_records_reject_unsupported_values(self):
        with self.assertRaises(ValidationError):
            SurveillanceSession(
                id=1,
                camera_id=1,
                status="uploaded",
                started_at="2026-07-28 10:00:00",
                ended_at=None,
                average_fps=None,
                frames_processed=0,
                error_message=None,
            )


if __name__ == "__main__":
    unittest.main()
