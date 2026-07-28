from dataclasses import dataclass

import cv2
import numpy as np

from backend.app.config import MIN_DETECTED_FACE_SIZE


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    width: int
    height: int


class FaceDetectionError(ValueError):
    pass


class FaceDetector:
    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._classifier = cv2.CascadeClassifier(cascade_path)
        if self._classifier.empty():
            raise RuntimeError("OpenCV face detector could not be loaded")

    def require_single_face(self, image_content: bytes, filename: str) -> FaceBox:
        image_array = np.frombuffer(image_content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise FaceDetectionError(f"Unreadable image file: {filename}")

        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self._classifier.detectMultiScale(
            grayscale,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(MIN_DETECTED_FACE_SIZE, MIN_DETECTED_FACE_SIZE),
        )

        if len(faces) == 0:
            raise FaceDetectionError(f"No face detected: {filename}")
        if len(faces) > 1:
            raise FaceDetectionError(f"Multiple faces detected: {filename}")

        x, y, width, height = faces[0]
        return FaceBox(x=int(x), y=int(y), width=int(width), height=int(height))
