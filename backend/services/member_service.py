import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.ai.embedding_manager import (
    EmbeddingExtractionError,
    InsightFaceEmbeddingManager,
)
from backend.ai.face_cropper import CroppedFaceImage, crop_face_image
from backend.ai.image_validator import ImageValidationError, validate_uploaded_image
from backend.app.config import (
    EMBEDDINGS_DIR,
    KNOWN_FACES_DIR,
    resolve_storage_path,
    serialize_storage_path,
)


@dataclass(frozen=True)
class RegistrationFaceImage:
    original_filename: str
    cropped_image: CroppedFaceImage
    embedding: object


@dataclass(frozen=True)
class RejectedRegistrationImage:
    filename: str
    reason: str


class MemberService:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        embedding_manager: InsightFaceEmbeddingManager | None = None,
    ) -> None:
        self.connection = connection
        self._embedding_manager = embedding_manager

    @property
    def embedding_manager(self) -> InsightFaceEmbeddingManager:
        if self._embedding_manager is None:
            self._embedding_manager = InsightFaceEmbeddingManager()
        return self._embedding_manager

    async def register_member(self, name: str, images: list[UploadFile]) -> dict:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Person name is required")
        if not images:
            raise ValueError("At least one face image is required")

        upload_images = [image for image in images if image.filename]
        if not upload_images:
            raise ValueError("At least one face image is required")

        registration_images: list[RegistrationFaceImage] = []
        rejected_images: list[RejectedRegistrationImage] = []

        for image in upload_images:
            filename = image.filename or "unnamed image"
            try:
                content = await image.read()
            finally:
                await image.close()
            try:
                validated_image = validate_uploaded_image(image.filename, content)
            except ImageValidationError as exc:
                rejected_images.append(
                    RejectedRegistrationImage(filename=filename, reason=str(exc))
                )
                continue

            try:
                face_embedding = self.embedding_manager.extract_single_face_embedding(
                    validated_image.content,
                    validated_image.filename,
                )
                cropped_image = crop_face_image(
                    validated_image.content,
                    face_embedding.face_box,
                )
                registration_images.append(
                    RegistrationFaceImage(
                        original_filename=validated_image.filename,
                        cropped_image=cropped_image,
                        embedding=face_embedding.embedding,
                    )
                )
            except EmbeddingExtractionError as exc:
                rejected_images.append(
                    RejectedRegistrationImage(filename=filename, reason=str(exc))
                )

        if not registration_images:
            reasons = "; ".join(
                f"{image.filename}: {image.reason}" for image in rejected_images
            )
            raise ValueError(f"No valid face images were registered. {reasons}")

        cursor = self.connection.execute(
            "INSERT INTO people (name) VALUES (?)",
            (clean_name,),
        )
        person_id = int(cursor.lastrowid)
        person_dir = KNOWN_FACES_DIR / f"{person_id}_{self._slugify(clean_name)}"
        embedding_dir = EMBEDDINGS_DIR / f"{person_id}_{self._slugify(clean_name)}"

        saved_paths: list[str] = []
        saved_embedding_paths: list[str] = []
        try:
            person_dir.mkdir(parents=True, exist_ok=False)
            embedding_dir.mkdir(parents=True, exist_ok=False)
            for index, image in enumerate(registration_images, start=1):
                file_stem = f"{index:03d}_{uuid4().hex}"
                filename = f"{file_stem}{image.cropped_image.extension}"
                target_path = person_dir / filename
                with target_path.open("wb") as output:
                    output.write(image.cropped_image.content)
                saved_paths.append(serialize_storage_path(target_path))
                embedding_path = embedding_dir / f"{file_stem}.npy"
                saved_embedding_paths.append(
                    self.embedding_manager.save_embedding(
                        image.embedding,
                        embedding_path,
                    )
                )
                self.connection.execute(
                    """
                    INSERT INTO face_embeddings (person_id, image_path, embedding_path)
                    VALUES (?, ?, ?)
                    """,
                    (person_id, saved_paths[-1], saved_embedding_paths[-1]),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            self._cleanup_registration_artifacts(
                saved_paths + saved_embedding_paths,
                (person_dir, embedding_dir),
            )
            raise

        member = self.get_member(person_id)
        accepted_count = len(saved_paths)
        rejected_count = len(rejected_images)
        return {
            "member": member,
            "accepted_images": [
                {
                    "filename": image.original_filename,
                    "status": "accepted",
                    "reason": "Face crop and embedding saved.",
                }
                for image in registration_images
            ],
            "rejected_images": [
                {
                    "filename": image.filename,
                    "status": "rejected",
                    "reason": image.reason,
                }
                for image in rejected_images
            ],
            "message": (
                f"Registered {clean_name} with {accepted_count} image(s)."
                if rejected_count == 0
                else (
                    f"Registered {clean_name} with {accepted_count} image(s); "
                    f"{rejected_count} image(s) rejected."
                )
            ),
        }

    def list_members(self) -> list[dict]:
        rows = self.connection.execute(
            """
            SELECT p.id, p.name, p.created_at, COUNT(f.id) AS image_count
            FROM people p
            LEFT JOIN face_embeddings f ON f.person_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC, p.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_member(self, member_id: int) -> dict | None:
        row = self.connection.execute(
            """
            SELECT p.id, p.name, p.created_at, COUNT(f.id) AS image_count
            FROM people p
            LEFT JOIN face_embeddings f ON f.person_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (member_id,),
        ).fetchone()
        if row is None:
            return None

        images = self.connection.execute(
            """
            SELECT id, image_path, embedding_path, created_at
            FROM face_embeddings
            WHERE person_id = ?
            ORDER BY id ASC
            """,
            (member_id,),
        ).fetchall()
        member = dict(row)
        member["images"] = [dict(image) for image in images]
        return member

    def delete_member(self, member_id: int) -> bool:
        member = self.get_member(member_id)
        if member is None:
            return False

        file_paths = []
        for image in member["images"]:
            file_paths.append(image["image_path"])
            if image["embedding_path"]:
                file_paths.append(image["embedding_path"])

        self.connection.execute(
            "DELETE FROM face_embeddings WHERE person_id = ?",
            (member_id,),
        )
        self.connection.execute("DELETE FROM people WHERE id = ?", (member_id,))
        self.connection.commit()

        for file_path in file_paths:
            self._delete_local_file(file_path)
        return True

    @staticmethod
    def _delete_local_file(relative_path: str) -> None:
        target = resolve_storage_path(relative_path)
        try:
            allowed_roots = (
                KNOWN_FACES_DIR.resolve(),
                EMBEDDINGS_DIR.resolve(),
            )
            if not any(target.is_relative_to(root) for root in allowed_roots):
                return
            if target.exists() and target.is_file():
                target.unlink()
                parent = target.parent
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
        except OSError:
            return

    @classmethod
    def _cleanup_registration_artifacts(
        cls,
        stored_paths: list[str],
        directories: tuple[Path, Path],
    ) -> None:
        for stored_path in stored_paths:
            cls._delete_local_file(stored_path)
        for directory in directories:
            try:
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()
            except OSError:
                continue

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "member"
