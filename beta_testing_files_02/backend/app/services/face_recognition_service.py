"""
Service nhan dien khuon mat - dung insightface (buffalo_l = SCRFD detect + ArcFace recognition).
Logic get_embedding() port nguyen ven tu Notebook 02 (padding + det_thresh da kiem chung
tren du lieu that, KHONG doi lai so nay neu chua co ly do ro rang).

Model chi duoc load 1 LAN duy nhat luc server khoi dong (xem app/main.py, ham lifespan),
khong load lai moi request - vi load model mat vai giay, lam moi request se rat cham.
"""
from typing import Optional, Tuple, Dict

import cv2
import numpy as np

from app.config import FACE_DET_THRESH, FACE_PAD_RATIO


class FaceRecognitionService:
    def __init__(self):
        self.face_app = None
        # gallery: person_id (str) -> normalized embedding vector (512,)
        # Day la BAN SAO trong RAM de nhan dien nhanh - "nguon su that" van la
        # cot Person.embedding_path trong SQLite (file .npy), gallery nay duoc
        # nap lai tu do moi luc server khoi dong (xem load_gallery_from_db o main.py).
        self.gallery: Dict[str, np.ndarray] = {}

    def load_model(self) -> None:
        """Goi 1 LAN duy nhat, luc FastAPI khoi dong (lifespan startup)."""
        if self.face_app is not None:
            return

        from insightface.app import FaceAnalysis

        self.face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.face_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=FACE_DET_THRESH)

    def get_embedding(
        self, img_bgr: np.ndarray, pad_ratio: float = FACE_PAD_RATIO
    ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """Phat hien khuon mat co score cao nhat trong anh, tra ve (embedding_512d, det_score).
        Tra ve (None, None) neu khong tim thay mat nao hoac anh khong hop le."""
        if self.face_app is None:
            raise RuntimeError("Model chua duoc load - goi face_service.load_model() truoc")

        if img_bgr is None or img_bgr.size == 0:
            return None, None

        h, w = img_bgr.shape[:2]
        pad_h, pad_w = int(h * pad_ratio), int(w * pad_ratio)
        padded = cv2.copyMakeBorder(img_bgr, pad_h, pad_h, pad_w, pad_w, cv2.BORDER_REFLECT)

        faces = self.face_app.get(padded)
        if not faces:
            return None, None

        best = max(faces, key=lambda f: f.det_score)
        emb = best.embedding.astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-10)  # L2 normalize thu cong
        return emb, float(best.det_score)

    def match_raw(self, query_emb: Optional[np.ndarray]) -> Tuple[Optional[str], float]:
        """Tra ve (best_person_id, best_score) THO, KHONG ap threshold - dung de buffer
        nhieu frame roi moi quyet dinh (xem video_analysis_service.py)."""
        if query_emb is None or not self.gallery:
            return None, -1.0

        best_person_id, best_score = None, -1.0
        for person_id, gallery_emb in self.gallery.items():
            score = float(np.dot(query_emb, gallery_emb))
            if score > best_score:
                best_person_id, best_score = person_id, score
        return best_person_id, best_score
    
    def match(
        self, query_emb: Optional[np.ndarray], threshold: float
    ) -> Tuple[Optional[str], float]:
        """So khop voi gallery bang cosine similarity. Tra ve (person_id, score) neu >= threshold,
        nguoc lai (None, best_score) = nguoi la."""
        if query_emb is None or not self.gallery:
            return None, -1.0

        best_person_id, best_score = None, -1.0
        for person_id, gallery_emb in self.gallery.items():
            score = float(np.dot(query_emb, gallery_emb))
            if score > best_score:
                best_person_id, best_score = person_id, score

        if best_score >= threshold:
            return best_person_id, best_score
        return None, best_score

    def add_to_gallery(self, person_id, embedding: np.ndarray) -> None:
        self.gallery[str(person_id)] = embedding

    def remove_from_gallery(self, person_id) -> None:
        self.gallery.pop(str(person_id), None)


# Singleton - 1 instance dung chung cho toan bo app (import lai o dau cung ra CUNG 1 object)
face_service = FaceRecognitionService()
