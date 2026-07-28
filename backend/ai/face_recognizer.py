from threading import RLock

import numpy as np

from backend.ai.contracts import FaceObservation
from backend.ai.embedding_manager import InsightFaceEmbeddingManager
from backend.app.config import TRACK_FACE_PADDING_RATIO


class InMemoryFaceGallery:
    def __init__(self) -> None:
        self._embeddings: dict[int, tuple[np.ndarray, ...]] = {}
        self._lock = RLock()

    def replace(self, embeddings: dict[int, list[np.ndarray]]) -> None:
        normalized = {
            member_id: tuple(self._normalize(vector) for vector in vectors)
            for member_id, vectors in embeddings.items()
            if vectors
        }
        with self._lock:
            self._embeddings = normalized

    def add(self, member_id: int, embedding: np.ndarray) -> None:
        normalized = self._normalize(embedding)
        with self._lock:
            current = self._embeddings.get(member_id, ())
            self._embeddings[member_id] = (*current, normalized)

    def remove(self, member_id: int) -> None:
        with self._lock:
            self._embeddings.pop(member_id, None)

    def match(self, embedding: np.ndarray) -> tuple[int | None, float]:
        query = self._normalize(embedding)
        with self._lock:
            candidates = tuple(self._embeddings.items())

        best_member_id = None
        best_similarity = -1.0
        for member_id, member_embeddings in candidates:
            for candidate in member_embeddings:
                similarity = float(np.dot(query, candidate))
                if similarity > best_similarity:
                    best_member_id = member_id
                    best_similarity = similarity
        return best_member_id, best_similarity

    @staticmethod
    def _normalize(embedding: np.ndarray) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.size == 0:
            raise ValueError("Face embedding cannot be empty")
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-10:
            raise ValueError("Face embedding norm must be greater than zero")
        return vector / norm


class InsightFaceTrackRecognizer:
    def __init__(
        self,
        gallery: InMemoryFaceGallery,
        *,
        embedding_manager: InsightFaceEmbeddingManager | None = None,
        padding_ratio: float = TRACK_FACE_PADDING_RATIO,
    ) -> None:
        self.gallery = gallery
        self.embedding_manager = embedding_manager or InsightFaceEmbeddingManager()
        self.padding_ratio = padding_ratio

    def observe(self, person_crop_bgr: np.ndarray) -> FaceObservation:
        embedding, face_confidence = (
            self.embedding_manager.extract_best_embedding_from_bgr(
                person_crop_bgr,
                padding_ratio=self.padding_ratio,
            )
        )
        if embedding is None:
            return FaceObservation(
                face_detected=False,
                candidate_member_id=None,
                similarity=None,
                face_confidence=face_confidence,
            )

        member_id, similarity = self.gallery.match(embedding)
        return FaceObservation(
            face_detected=True,
            candidate_member_id=member_id,
            similarity=similarity,
            face_confidence=face_confidence,
        )
