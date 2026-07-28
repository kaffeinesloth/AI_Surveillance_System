"""Service wrap YOLOv8 person detection + ByteTrack tracking - phat hien va theo doi
TOAN BO nguoi trong khung hinh (khong phu thuoc mat co nhin thay hay khong)."""


class PersonDetectorService:
    def __init__(self):
        self.model = None

    def load_model(self, model_path: str = "yolov8n.pt") -> None:
        """Goi 1 LAN duy nhat, luc FastAPI khoi dong."""
        if self.model is not None:
            return
        from ultralytics import YOLO

        self.model = YOLO(model_path)

    def track(self, video_path: str, conf: float = 0.4):
        """Tra ve generator ket qua tracking (giong ultralytics .track(stream=True)).
        Chi lay class 0 = 'person' trong COCO."""
        if self.model is None:
            raise RuntimeError("Model chua duoc load - goi person_detector.load_model() truoc")

        return self.model.track(
            source=video_path,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=conf,
            stream=True,
            verbose=False,
        )


person_detector = PersonDetectorService()