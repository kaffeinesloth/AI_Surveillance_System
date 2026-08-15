import sqlite3
import unittest

from fastapi.testclient import TestClient

from backend.app.database import create_schema
from backend.main import create_app
from backend.routes.zone_routes import get_zone_service
from backend.services.zone_service import ZoneService


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


class ZoneApiTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = make_connection()
        camera = self.connection.execute(
            "INSERT INTO cameras (name, source) VALUES (?, ?)",
            ("Laptop Webcam", "0"),
        )
        self.connection.commit()
        self.camera_id = int(camera.lastrowid)
        self.app = create_app(initialize_database=False)
        self.app.dependency_overrides[get_zone_service] = (
            lambda: ZoneService(self.connection)
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()
        self.connection.close()

    def test_create_list_update_and_delete_zone(self):
        created = self.client.post(
            "/zones",
            json={
                "camera_id": self.camera_id,
                "name": "Entrance",
                "points": [
                    {"x": 1, "y": 2},
                    {"x": 10, "y": 2},
                    {"x": 10, "y": 12},
                    {"x": 1, "y": 12},
                ],
            },
        )

        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["name"], "Entrance")
        self.assertEqual(body["points"][0], {"x": 1, "y": 2})

        listed = self.client.get(f"/zones?camera_id={self.camera_id}")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        updated = self.client.patch(
            f"/zones/{body['id']}",
            json={"name": "Server door", "is_active": False},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Server door")
        self.assertFalse(updated.json()["is_active"])

        active_only = self.client.get(f"/zones?camera_id={self.camera_id}")
        self.assertEqual(active_only.json(), [])

        deleted = self.client.delete(f"/zones/{body['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["name"], "Server door")

    def test_missing_camera_is_rejected(self):
        response = self.client.post(
            "/zones",
            json={
                "camera_id": 999,
                "name": "No camera",
                "points": [
                    {"x": 1, "y": 2},
                    {"x": 10, "y": 2},
                    {"x": 10, "y": 12},
                    {"x": 1, "y": 12},
                ],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Active camera not found")

    def test_inactive_zones_are_hidden_unless_requested(self):
        created = self.client.post(
            "/zones",
            json={
                "camera_id": self.camera_id,
                "name": "Back door",
                "points": [
                    {"x": 1, "y": 2},
                    {"x": 10, "y": 2},
                    {"x": 10, "y": 12},
                    {"x": 1, "y": 12},
                ],
            },
        ).json()

        updated = self.client.patch(
            f"/zones/{created['id']}",
            json={"is_active": False},
        )

        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["is_active"])
        self.assertEqual(
            self.client.get(f"/zones?camera_id={self.camera_id}").json(),
            [],
        )
        all_zones = self.client.get(
            f"/zones?camera_id={self.camera_id}&include_inactive=true"
        )
        self.assertEqual(len(all_zones.json()), 1)
        self.assertFalse(all_zones.json()[0]["is_active"])


if __name__ == "__main__":
    unittest.main()
