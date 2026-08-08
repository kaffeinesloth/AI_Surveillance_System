import sqlite3
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.database import create_schema
from backend.camera.webcam import (
    CameraCaptureService,
    CameraSnapshot,
    CameraUnavailableError,
    open_camera_capture,
    resolve_camera_source,
)
from backend.main import create_app
from backend.routes.camera_routes import (
    get_camera_capture_service,
    get_camera_service,
)
from backend.routes.surveillance_routes import get_surveillance_manager
from backend.services.camera_service import CameraService


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


class FakeCaptureService:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.sources = []
        image = np.zeros((24, 32, 3), dtype=np.uint8)
        image[:, :] = (20, 80, 160)
        success, encoded = cv2.imencode(".jpg", image)
        if not success:
            raise RuntimeError("Test JPEG could not be encoded")
        self.snapshot = CameraSnapshot(
            content=encoded.tobytes(),
            width=32,
            height=24,
        )

    def capture_snapshot(self, source):
        self.sources.append(source)
        if self.error:
            raise self.error
        return self.snapshot


class FakeVideoCapture:
    def __init__(self, source, *, opened=True, frame=None):
        self.source = source
        self.opened = opened
        self.frame = (
            frame
            if frame is not None
            else np.zeros((10, 20, 3), dtype=np.uint8)
        )
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return self.opened, self.frame

    def release(self):
        self.released = True


class CameraApiTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = make_connection()
        self.service = CameraService(self.connection)
        self.capture_service = FakeCaptureService()
        self.app = create_app(initialize_database=False)
        self.app.dependency_overrides[get_camera_service] = lambda: self.service
        self.app.dependency_overrides[get_camera_capture_service] = (
            lambda: self.capture_service
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()
        self.connection.close()

    def create_camera(self):
        response = self.client.post(
            "/cameras",
            json={
                "name": "Laptop Webcam",
                "source": "0",
                "location": "Demo room",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_list_get_and_update_camera(self):
        created = self.create_camera()

        listed = self.client.get("/cameras")
        detail = self.client.get(f"/cameras/{created['id']}")
        updated = self.client.patch(
            f"/cameras/{created['id']}",
            json={"name": "Primary Webcam", "location": "Lab"},
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertEqual(detail.json()["source"], "0")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Primary Webcam")
        self.assertEqual(updated.json()["location"], "Lab")

    def test_delete_soft_deactivates_and_hides_camera(self):
        created = self.create_camera()

        deleted = self.client.delete(f"/cameras/{created['id']}")

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["message"], "Camera deactivated")
        self.assertFalse(deleted.json()["camera"]["is_active"])
        self.assertEqual(self.client.get("/cameras").json(), [])
        inactive = self.client.get("/cameras?include_inactive=true").json()
        self.assertEqual(len(inactive), 1)
        self.assertFalse(inactive[0]["is_active"])

    def test_deactivation_preserves_historical_session(self):
        created = self.create_camera()
        session = self.connection.execute(
            """
            INSERT INTO surveillance_sessions (camera_id, status)
            VALUES (?, ?)
            """,
            (created["id"], "stopped"),
        )
        self.connection.commit()

        response = self.client.delete(f"/cameras/{created['id']}")

        self.assertEqual(response.status_code, 200)
        saved_session = self.connection.execute(
            "SELECT camera_id FROM surveillance_sessions WHERE id = ?",
            (session.lastrowid,),
        ).fetchone()
        self.assertEqual(saved_session["camera_id"], created["id"])

    def test_snapshot_returns_non_cached_jpeg(self):
        created = self.create_camera()

        response = self.client.get(f"/cameras/{created['id']}/snapshot")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertGreater(len(response.content), 0)
        self.assertEqual(self.capture_service.sources, ["0"])

    def test_camera_test_returns_dimensions(self):
        created = self.create_camera()

        response = self.client.post(f"/cameras/{created['id']}/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "available": True,
                "width": 32,
                "height": 24,
                "message": "Camera source is available",
            },
        )

    def test_unavailable_camera_returns_503(self):
        created = self.create_camera()
        self.capture_service.error = CameraUnavailableError("Camera unavailable")

        response = self.client.get(f"/cameras/{created['id']}/snapshot")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Camera unavailable")

    def test_inactive_camera_cannot_be_opened(self):
        created = self.create_camera()
        self.client.delete(f"/cameras/{created['id']}")

        response = self.client.get(f"/cameras/{created['id']}/snapshot")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Camera is inactive")

    def test_preview_is_rejected_while_camera_is_live(self):
        class RunningManager:
            @staticmethod
            def is_camera_running(camera_id):
                return True

        created = self.create_camera()
        self.app.dependency_overrides[get_surveillance_manager] = (
            lambda: RunningManager()
        )

        response = self.client.get(f"/cameras/{created['id']}/snapshot")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Camera is currently used by live surveillance",
        )

    def test_missing_camera_returns_404(self):
        self.assertEqual(self.client.get("/cameras/999").status_code, 404)
        self.assertEqual(
            self.client.get("/cameras/999/snapshot").status_code,
            404,
        )


class CameraCaptureServiceTestCase(unittest.TestCase):
    def test_numeric_source_is_converted_to_webcam_index(self):
        self.assertEqual(resolve_camera_source("0"), 0)
        self.assertEqual(resolve_camera_source(" 2 "), 2)
        self.assertEqual(
            resolve_camera_source("rtsp://example/camera"),
            "rtsp://example/camera",
        )

    def test_capture_releases_camera_and_returns_jpeg(self):
        captures = []

        def factory(source):
            capture = FakeVideoCapture(source)
            captures.append(capture)
            return capture

        service = CameraCaptureService(
            capture_factory=factory,
            read_attempts=2,
        )

        snapshot = service.capture_snapshot("0")

        self.assertEqual(captures[0].source, 0)
        self.assertTrue(captures[0].released)
        self.assertEqual(snapshot.width, 20)
        self.assertEqual(snapshot.height, 10)
        self.assertTrue(snapshot.content.startswith(b"\xff\xd8"))

    def test_capture_releases_unavailable_camera(self):
        captures = []

        def factory(source):
            capture = FakeVideoCapture(source, opened=False)
            captures.append(capture)
            return capture

        service = CameraCaptureService(capture_factory=factory)

        with self.assertRaises(CameraUnavailableError):
            service.capture_snapshot("0")

        self.assertTrue(captures[0].released)

    def test_numeric_source_uses_avfoundation_fallback_on_macos(self):
        captures = []

        def factory(source, api_preference=None):
            capture = FakeVideoCapture(
                source,
                opened=api_preference == cv2.CAP_AVFOUNDATION,
            )
            capture.api_preference = api_preference
            captures.append(capture)
            return capture

        with patch("backend.camera.webcam.platform.system", return_value="Darwin"):
            capture = open_camera_capture(0, capture_factory=factory)

        self.assertTrue(capture.isOpened())
        self.assertEqual(captures[0].api_preference, None)
        self.assertEqual(captures[1].api_preference, cv2.CAP_AVFOUNDATION)
        self.assertTrue(captures[0].released)
        self.assertFalse(captures[1].released)


if __name__ == "__main__":
    unittest.main()
