from threading import Lock

import numpy as np

from backend.ai.contracts import BoundingBox, TrackedPerson
from backend.app.config import PERSON_DETECTION_THRESHOLD, YOLO_MODEL_PATH


class YoloByteTracker:
    """Lazy YOLO person detector with per-instance ByteTrack state."""

    def __init__(
        self,
        *,
        model_path: str = YOLO_MODEL_PATH,
        confidence: float = PERSON_DETECTION_THRESHOLD,
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self._model = None
        self._load_lock = Lock()

    def _get_model(self):
        with self._load_lock:
            if self._model is None:
                try:
                    from ultralytics import YOLO
                except ImportError as exc:
                    raise RuntimeError(
                        "Ultralytics is required for YOLOv8 + ByteTrack analysis. "
                        "Install backend/requirements.txt before running real analysis."
                    ) from exc
                self._model = YOLO(self.model_path)
            return self._model

    def track_frame(self, frame_bgr: np.ndarray) -> list[TrackedPerson]:
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        results = self._get_model().track(
            source=frame_bgr,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=self.confidence,
            verbose=False,
        )
        if not results:
            return []

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0 or boxes.id is None:
            return []

        coordinates = boxes.xyxy.cpu().numpy().astype(int)
        track_ids = boxes.id.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        return [
            TrackedPerson(
                track_id=int(track_id),
                bounding_box=BoundingBox(
                    x1=int(box[0]),
                    y1=int(box[1]),
                    x2=int(box[2]),
                    y2=int(box[3]),
                ),
                confidence=float(confidence),
            )
            for box, track_id, confidence in zip(
                coordinates,
                track_ids,
                confidences,
            )
        ]

    def reset(self) -> None:
        if self._model is not None:
            self._model.predictor = None
