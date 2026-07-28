import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.database import create_schema
from backend.main import create_app
from backend.routes.alert_routes import get_alert_service
from backend.routes.log_routes import get_log_service
from backend.services.alert_service import AlertService
from backend.services.log_service import LogService


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


class LogAlertApiTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = make_connection()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.snapshots_dir = Path(self.temporary_directory.name)
        self.snapshot_path = self.snapshots_dir / "alert.jpg"
        self.snapshot_path.write_bytes(b"\xff\xd8test-jpeg\xff\xd9")

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
        known_log = self.connection.execute(
            """
            INSERT INTO detection_logs (
                session_id,
                camera_id,
                member_id,
                track_id,
                status,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session.lastrowid,
                camera.lastrowid,
                member.lastrowid,
                1,
                "known",
                0.78,
            ),
        )
        unknown_log = self.connection.execute(
            """
            INSERT INTO detection_logs (
                session_id,
                camera_id,
                track_id,
                status,
                confidence,
                snapshot_path
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session.lastrowid,
                camera.lastrowid,
                2,
                "unknown",
                0.20,
                str(self.snapshot_path),
            ),
        )
        alert = self.connection.execute(
            """
            INSERT INTO alerts (
                session_id,
                camera_id,
                detection_log_id,
                alert_type,
                message,
                confidence,
                snapshot_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.lastrowid,
                camera.lastrowid,
                unknown_log.lastrowid,
                "unknown_person",
                "Unknown person detected",
                0.20,
                str(self.snapshot_path),
            ),
        )
        self.connection.commit()
        self.camera_id = int(camera.lastrowid)
        self.known_log_id = int(known_log.lastrowid)
        self.alert_id = int(alert.lastrowid)

        self.app = create_app(initialize_database=False)
        self.app.dependency_overrides[get_log_service] = lambda: LogService(
            self.connection
        )
        self.app.dependency_overrides[get_alert_service] = (
            lambda: AlertService(self.connection)
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()
        self.connection.close()

    def test_log_listing_filter_and_latest(self):
        all_logs = self.client.get("/logs")
        known_logs = self.client.get("/logs?status=known")
        latest = self.client.get("/logs/latest")

        self.assertEqual(all_logs.status_code, 200)
        self.assertEqual(len(all_logs.json()), 2)
        self.assertEqual(len(known_logs.json()), 1)
        self.assertEqual(known_logs.json()[0]["member_name"], "Known Member")
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json()["status"], "unknown")

    def test_alert_listing_detail_latest_and_read_update(self):
        alerts = self.client.get("/alerts?is_read=false")
        latest = self.client.get("/alerts/latest")
        detail = self.client.get(f"/alerts/{self.alert_id}")
        updated = self.client.patch(
            f"/alerts/{self.alert_id}/read",
            json={"is_read": True},
        )

        self.assertEqual(len(alerts.json()), 1)
        self.assertEqual(latest.json()["id"], self.alert_id)
        self.assertEqual(
            detail.json()["snapshot_url"],
            f"/alerts/{self.alert_id}/snapshot",
        )
        self.assertTrue(updated.json()["is_read"])
        self.assertEqual(
            self.client.get("/alerts?is_read=false").json(),
            [],
        )

    def test_alert_snapshot_is_contained_and_non_cached(self):
        with patch(
            "backend.routes.alert_routes.SNAPSHOTS_DIR",
            self.snapshots_dir,
        ):
            response = self.client.get(
                f"/alerts/{self.alert_id}/snapshot"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.content, self.snapshot_path.read_bytes())

    def test_snapshot_outside_configured_directory_is_rejected(self):
        different_directory = self.snapshots_dir / "allowed"
        different_directory.mkdir()
        with patch(
            "backend.routes.alert_routes.SNAPSHOTS_DIR",
            different_directory,
        ):
            response = self.client.get(
                f"/alerts/{self.alert_id}/snapshot"
            )

        self.assertEqual(response.status_code, 404)

    def test_missing_records_return_404(self):
        self.assertEqual(self.client.get("/alerts/999").status_code, 404)
        self.assertEqual(
            self.client.patch(
                "/alerts/999/read",
                json={"is_read": True},
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
