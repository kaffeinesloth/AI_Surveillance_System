from io import BytesIO
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from PIL import Image, ImageOps

from backend.app.config import (
    EMBEDDINGS_DIR,
    INSIGHTFACE_DET_SIZE,
    INSIGHTFACE_MODEL_NAME,
    INSIGHTFACE_ROOT,
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
        return str(target_path.relative_to(EMBEDDINGS_DIR.parents[1]))

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
                app.prepare(ctx_id=-1, det_size=INSIGHTFACE_DET_SIZE)
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
