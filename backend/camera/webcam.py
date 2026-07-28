from collections.abc import Callable
from dataclasses import dataclass

import cv2


class CameraUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class CameraSnapshot:
    content: bytes
    width: int
    height: int


def resolve_camera_source(source: str) -> int | str:
    clean_source = source.strip()
    if not clean_source:
        raise ValueError("Camera source is required")
    return int(clean_source) if clean_source.isdigit() else clean_source


class CameraCaptureService:
    def __init__(
        self,
        *,
        capture_factory: Callable = cv2.VideoCapture,
        read_attempts: int = 3,
    ) -> None:
        if read_attempts <= 0:
            raise ValueError("Camera read attempts must be positive")
        self.capture_factory = capture_factory
        self.read_attempts = read_attempts

    def capture_snapshot(self, source: str) -> CameraSnapshot:
        resolved_source = resolve_camera_source(source)
        capture = self.capture_factory(resolved_source)
        try:
            if not capture.isOpened():
                raise CameraUnavailableError(
                    f"Could not open camera source: {source}"
                )

            frame = None
            for _ in range(self.read_attempts):
                success, candidate = capture.read()
                if success and candidate is not None and candidate.size > 0:
                    frame = candidate

            if frame is None:
                raise CameraUnavailableError(
                    f"Could not read a frame from camera source: {source}"
                )

            encoded, buffer = cv2.imencode(".jpg", frame)
            if not encoded:
                raise CameraUnavailableError("Could not encode camera snapshot")

            height, width = frame.shape[:2]
            return CameraSnapshot(
                content=buffer.tobytes(),
                width=int(width),
                height=int(height),
            )
        finally:
            capture.release()
