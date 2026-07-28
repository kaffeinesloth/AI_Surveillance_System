import unittest

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.ai.contracts import (
    BoundingBox,
    FrameAnalysis,
    TrackAnalysis,
)
from backend.app.models import DetectionStatus, LiveSurveillanceState
from backend.main import create_app
from backend.routes.surveillance_routes import get_surveillance_manager
from backend.routes.surveillance_routes import (
    get_video_analysis_activity_manager,
)
from backend.services.surveillance_manager import (
    LatestAnalysisSnapshot,
    SurveillanceCameraNotFoundError,
    SurveillanceStatusSnapshot,
)


class FakeSurveillanceManager:
    def __init__(self):
        self.raise_on_start = None
        self.status_value = SurveillanceStatusSnapshot(
            state=LiveSurveillanceState.IDLE,
            running=False,
            camera_id=None,
            session_id=None,
            frames_processed=0,
            fps=0.0,
            started_at=None,
            error_message=None,
        )
        frame = np.zeros((12, 16, 3), dtype=np.uint8)
        success, encoded = cv2.imencode(".jpg", frame)
        if not success:
            raise RuntimeError("Could not create test JPEG")
        self.frame = encoded.tobytes()
        self.latest = LatestAnalysisSnapshot(
            analysis=FrameAnalysis(
                frame_index=5,
                timestamp_seconds=0.5,
                width=16,
                height=12,
                tracks=(
                    TrackAnalysis(
                        track_id=2,
                        bounding_box=BoundingBox(1, 1, 10, 11),
                        person_confidence=0.9,
                        status=DetectionStatus.KNOWN,
                        member_id=4,
                        similarity=0.72,
                        face_confidence=0.95,
                    ),
                ),
            ),
            member_names={4: "Known Member"},
        )

    def start(self, camera_id):
        if self.raise_on_start:
            raise self.raise_on_start
        self.status_value = SurveillanceStatusSnapshot(
            state=LiveSurveillanceState.RUNNING,
            running=True,
            camera_id=camera_id,
            session_id=3,
            frames_processed=0,
            fps=0.0,
            started_at="2026-07-28 10:00:00",
            error_message=None,
        )
        return self.status_value

    def stop(self):
        self.status_value = SurveillanceStatusSnapshot(
            state=LiveSurveillanceState.STOPPED,
            running=False,
            camera_id=1,
            session_id=3,
            frames_processed=10,
            fps=8.2,
            started_at="2026-07-28 10:00:00",
            error_message=None,
        )
        return self.status_value

    def status(self):
        return self.status_value

    def latest_analysis(self):
        return self.latest

    def latest_frame_jpeg(self):
        return self.frame


class FakeVideoActivityManager:
    def __init__(self):
        self.active = False

    def has_active_job(self):
        return self.active


class SurveillanceApiTestCase(unittest.TestCase):
    def setUp(self):
        self.manager = FakeSurveillanceManager()
        self.video_manager = FakeVideoActivityManager()
        self.app = create_app(initialize_database=False)
        self.app.dependency_overrides[get_surveillance_manager] = (
            lambda: self.manager
        )
        self.app.dependency_overrides[
            get_video_analysis_activity_manager
        ] = lambda: self.video_manager
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_start_status_and_stop(self):
        started = self.client.post(
            "/surveillance/start",
            json={"camera_id": 1},
        )
        status = self.client.get("/surveillance/status")
        stopped = self.client.post("/surveillance/stop")

        self.assertEqual(started.status_code, 200)
        self.assertTrue(started.json()["running"])
        self.assertEqual(status.json()["session_id"], 3)
        self.assertEqual(stopped.json()["state"], "stopped")

    def test_latest_analysis_includes_member_name(self):
        response = self.client.get("/surveillance/latest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["frame_index"], 5)
        self.assertEqual(
            response.json()["tracks"][0]["member_name"],
            "Known Member",
        )

    def test_latest_frame_is_non_cached_jpeg(self):
        response = self.client.get("/surveillance/frame")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertTrue(response.content.startswith(b"\xff\xd8"))

    def test_missing_camera_is_translated_to_404(self):
        self.manager.raise_on_start = SurveillanceCameraNotFoundError(
            "Camera not found"
        )

        response = self.client.post(
            "/surveillance/start",
            json={"camera_id": 999},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Camera not found")

    def test_active_video_analysis_blocks_live_start(self):
        self.video_manager.active = True

        response = self.client.post(
            "/surveillance/start",
            json={"camera_id": 1},
        )

        self.assertEqual(response.status_code, 409)

    def test_missing_latest_results_return_404(self):
        self.manager.latest = None
        self.manager.frame = None

        self.assertEqual(
            self.client.get("/surveillance/latest").status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/surveillance/frame").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
