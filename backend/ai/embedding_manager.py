from io import BytesIO
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from PIL import Image, ImageOps

from backend.app.config import (
    EMBEDDINGS_DIR,
    FACE_DETECTION_THRESHOLD,
    INSIGHTFACE_DET_SIZE,
    INSIGHTFACE_MODEL_NAME,
    INSIGHTFACE_ROOT,
    serialize_storage_path,
)


class EmbeddingExtractionError(ValueError):
    pass


class InsightFaceEmbeddingManager:
    _app = None
    _lock = Lock()

    def extract_embedding(self, image_content: bytes, filename: str) -> np.ndarray:
        app = self._get_app()
        image = self._decode_image(image_content, filename)
        faces = app.get(image)

        if len(faces) == 0:
            raise EmbeddingExtractionError(
                f"Embedding model could not detect a face: {filename}"
            )
        if len(faces) > 1:
            raise EmbeddingExtractionError(
                f"Embedding model detected multiple faces: {filename}"
            )

        embedding = np.asarray(faces[0].normed_embedding, dtype=np.float32)
        if embedding.size == 0:
            raise EmbeddingExtractionError(
                f"Embedding model returned an empty vector: {filename}"
            )
        return embedding

    def save_embedding(self, embedding: np.ndarray, target_path: Path) -> str:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(target_path, embedding)
        return serialize_storage_path(target_path)

    def extract_best_embedding_from_bgr(
        self,
        image_bgr: np.ndarray,
        *,
        padding_ratio: float = 0.0,
    ) -> tuple[np.ndarray | None, float | None]:
        if image_bgr is None or image_bgr.size == 0:
            return None, None

        image = image_bgr
        if padding_ratio > 0:
            height, width = image.shape[:2]
            pad_y = int(height * padding_ratio)
            pad_x = int(width * padding_ratio)
            image = cv2.copyMakeBorder(
                image,
                pad_y,
                pad_y,
                pad_x,
                pad_x,
                cv2.BORDER_REFLECT,
            )

        faces = self._get_app().get(image)
        if not faces:
            return None, None

        best_face = max(faces, key=lambda face: float(face.det_score))
        embedding = np.asarray(best_face.normed_embedding, dtype=np.float32)
        if embedding.size == 0:
            return None, float(best_face.det_score)
        embedding /= np.linalg.norm(embedding) + 1e-10
        return embedding, float(best_face.det_score)

    @classmethod
    def _get_app(cls):
        with cls._lock:
            if cls._app is None:
                from insightface.app import FaceAnalysis

                INSIGHTFACE_ROOT.mkdir(parents=True, exist_ok=True)
                app = FaceAnalysis(
                    name=INSIGHTFACE_MODEL_NAME,
                    root=str(INSIGHTFACE_ROOT),
                    providers=["CPUExecutionProvider"],
                )
                app.prepare(
                    ctx_id=-1,
                    det_size=INSIGHTFACE_DET_SIZE,
                    det_thresh=FACE_DETECTION_THRESHOLD,
                )
                cls._app = app
            return cls._app

    @staticmethod
    def _decode_image(image_content: bytes, filename: str) -> np.ndarray:
        try:
            with Image.open(BytesIO(image_content)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
        except OSError as exc:
            raise EmbeddingExtractionError(f"Unreadable face crop: {filename}") from exc

        rgb_array = np.asarray(image)
        return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
