import asyncio
import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from backend.ai.embedding_manager import SingleFaceEmbedding
from backend.ai.face_detector import FaceBox
from backend.app.database import create_schema
from backend.main import create_app
from backend.routes.member_routes import get_member_service
from backend.services.member_service import MemberService


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


class FakeMemberService:
    def __init__(
        self,
        *,
        members=None,
        member=None,
        deleted=False,
        registration_error=None,
    ):
        self.members = members or []
        self.member = member
        self.deleted = deleted
        self.registration_error = registration_error

    async def register_member(self, name, images):
        if self.registration_error:
            raise ValueError(self.registration_error)
        raise AssertionError("Successful registration is outside this test double")

    def list_members(self):
        return self.members

    def get_member(self, member_id):
        return self.member

    def delete_member(self, member_id):
        return self.deleted


class FakeEmbeddingManager:
    def extract_single_face_embedding(self, image_content, filename):
        return SingleFaceEmbedding(
            face_box=FaceBox(x=30, y=30, width=100, height=100),
            embedding=np.array([0.1, 0.2, 0.3], dtype=np.float32),
        )

    def save_embedding(self, embedding, target_path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(target_path, embedding)
        return str(target_path)


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content

    async def close(self):
        return None


def make_jpeg_bytes(width: int = 180, height: int = 180) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color=(120, 120, 120)).save(
        output,
        format="JPEG",
    )
    return output.getvalue()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(initialize_database=False)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def override_member_service(self, service):
        self.app.dependency_overrides[get_member_service] = lambda: service

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_empty_member_list(self):
        connection = make_connection()
        self.addCleanup(connection.close)
        self.override_member_service(MemberService(connection))

        response = self.client.get("/members")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_member_list_with_seeded_data(self):
        connection = make_connection()
        self.addCleanup(connection.close)
        cursor = connection.execute(
            "INSERT INTO people (name) VALUES (?)",
            ("Test Member",),
        )
        connection.execute(
            """
            INSERT INTO face_embeddings (person_id, image_path, embedding_path)
            VALUES (?, ?, ?)
            """,
            (cursor.lastrowid, "data/known_faces/test.jpg", "data/embeddings/test.npy"),
        )
        connection.commit()
        self.override_member_service(MemberService(connection))

        response = self.client.get("/members")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["name"], "Test Member")
        self.assertEqual(body[0]["image_count"], 1)

    def test_member_not_found(self):
        self.override_member_service(FakeMemberService(member=None))

        response = self.client.get("/members/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Member not found")

    def test_registration_validation_failure_does_not_load_ai(self):
        self.override_member_service(
            FakeMemberService(registration_error="Person name is required")
        )

        response = self.client.post(
            "/members/register",
            data={"name": " "},
            files={"images": ("face.jpg", b"not-used", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Person name is required")

    def test_delete_member_route(self):
        self.override_member_service(FakeMemberService(deleted=True))

        response = self.client.delete("/members/7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Member deleted"})

    def test_delete_member_removes_database_rows_and_files(self):
        connection = make_connection()
        self.addCleanup(connection.close)

        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_root = Path(temporary_directory)
            known_faces_dir = storage_root / "known_faces"
            embeddings_dir = storage_root / "embeddings"
            known_faces_dir.mkdir()
            embeddings_dir.mkdir()
            image_path = known_faces_dir / "face.jpg"
            embedding_path = embeddings_dir / "face.npy"
            image_path.write_bytes(b"face")
            embedding_path.write_bytes(b"embedding")

            cursor = connection.execute(
                "INSERT INTO people (name) VALUES (?)",
                ("Disposable Member",),
            )
            member_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO face_embeddings (person_id, image_path, embedding_path)
                VALUES (?, ?, ?)
                """,
                (member_id, str(image_path), str(embedding_path)),
            )
            connection.commit()

            service = MemberService(connection)
            with (
                patch(
                    "backend.services.member_service.KNOWN_FACES_DIR",
                    known_faces_dir,
                ),
                patch(
                    "backend.services.member_service.EMBEDDINGS_DIR",
                    embeddings_dir,
                ),
            ):
                deleted = service.delete_member(member_id)

            self.assertTrue(deleted)
            self.assertIsNone(service.get_member(member_id))
            self.assertFalse(image_path.exists())
            self.assertFalse(embedding_path.exists())

    def test_blank_name_is_rejected_before_ai_initialization(self):
        connection = make_connection()
        self.addCleanup(connection.close)
        service = MemberService(connection)

        with self.assertRaisesRegex(ValueError, "Person name is required"):
            asyncio.run(service.register_member(" ", []))

        self.assertIsNone(service._embedding_manager)

    def test_register_member_uses_embedding_face_box_without_opencv_cascade(self):
        connection = make_connection()
        self.addCleanup(connection.close)

        with tempfile.TemporaryDirectory() as temporary_directory:
            known_faces_dir = Path(temporary_directory) / "known_faces"
            embeddings_dir = Path(temporary_directory) / "embeddings"
            service = MemberService(
                connection,
                embedding_manager=FakeEmbeddingManager(),
            )
            with (
                patch(
                    "backend.services.member_service.KNOWN_FACES_DIR",
                    known_faces_dir,
                ),
                patch(
                    "backend.services.member_service.EMBEDDINGS_DIR",
                    embeddings_dir,
                ),
            ):
                result = asyncio.run(
                    service.register_member(
                        "Registered Member",
                        [FakeUpload("face.jpg", make_jpeg_bytes())],
                    )
                )

        self.assertEqual(result["member"]["name"], "Registered Member")
        self.assertEqual(len(result["accepted_images"]), 1)
        self.assertEqual(result["rejected_images"], [])


if __name__ == "__main__":
    unittest.main()
