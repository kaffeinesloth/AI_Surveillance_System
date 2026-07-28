"""
Chay cascade YOLOv8+ByteTrack (person) + insightface (face, co padding) tren 1 video da upload.
Dung buffer theo TUNG track_id (giong het Notebook 02) de quyet dinh danh tinh on dinh hon,
thay vi tin 1 frame don le. KHONG ghi Track/Detection vao DB - chi tra ve dict ket qua,
router se tra thang ve response API (dung persist_detections=False cho video upload).
"""
from collections import defaultdict, deque

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import FACE_MATCH_THRESHOLD, TRACK_BUFFER_SIZE
from app.models.person import Person
from app.services.face_recognition_service import face_service
from app.services.person_detector_service import person_detector


def analyze_video(video_path: str, db: Session) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Khong mo duoc video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()  # person_detector.track() se tu mo lai video

    # Moi track_id co 1 deque RIENG - danh tinh cua nguoi nay khong lien quan gi den
    # track_id khac dang xuat hien trong CUNG frame
    track_buffers = defaultdict(lambda: deque(maxlen=TRACK_BUFFER_SIZE))
    track_meta = {}  # track_id -> {first_frame, first_timestamp, last_frame, last_timestamp}

    frame_idx = 0
    results_gen = person_detector.track(video_path, conf=0.4)

    for r in results_gen:
        frame = r.orig_img
        boxes = r.boxes
        timestamp_sec = frame_idx / fps

        if boxes is not None and len(boxes) > 0 and boxes.id is not None:
            xyxy = boxes.xyxy.cpu().numpy().astype(int)
            track_ids = boxes.id.cpu().numpy().astype(int)

            for (x1, y1, x2, y2), track_id in zip(xyxy, track_ids):
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)
                person_crop = frame[y1:y2, x1:x2]

                if person_crop.size == 0:
                    continue

                emb, det_score = face_service.get_embedding(person_crop)
                buffer = track_buffers[track_id]

                if emb is not None:
                    raw_person_id, raw_score = face_service.match_raw(emb)
                    buffer.append((raw_person_id, raw_score))
                # Khong thay mat frame nay: KHONG xoa buffer, giu nguyen lich su cu

                track_id_int = int(track_id)
                if track_id_int not in track_meta:
                    track_meta[track_id_int] = {
                        "first_frame": frame_idx,
                        "first_timestamp": round(timestamp_sec, 2),
                        "last_frame": frame_idx,
                        "last_timestamp": round(timestamp_sec, 2),
                    }
                else:
                    track_meta[track_id_int]["last_frame"] = frame_idx
                    track_meta[track_id_int]["last_timestamp"] = round(timestamp_sec, 2)

        frame_idx += 1

    # Tong hop ket qua CUOI CUNG cho tung track (sau khi da xem het video)
    people_detected = []
    for track_id, buffer in track_buffers.items():
        if len(buffer) == 0:
            continue

        avg_score = float(np.mean([s for _, s in buffer]))
        names_in_buffer = [n for n, _ in buffer if n is not None]
        majority_person_id = (
            max(set(names_in_buffer), key=names_in_buffer.count) if names_in_buffer else None
        )
        is_known = majority_person_id is not None and avg_score >= FACE_MATCH_THRESHOLD

        person_name = None
        if is_known:
            person = db.query(Person).filter(Person.id == int(majority_person_id)).first()
            person_name = person.name if person else None
            is_known = person is not None  # phong truong hop person bi xoa nhung gallery chua kip nap lai

        meta = track_meta.get(track_id, {})
        people_detected.append(
            {
                "track_id": track_id,
                "person_id": int(majority_person_id) if is_known else None,
                "person_name": person_name,
                "avg_match_score": round(avg_score, 3),
                "is_known": is_known,
                "first_seen_timestamp": meta.get("first_timestamp"),
                "last_seen_timestamp": meta.get("last_timestamp"),
            }
        )

    duration_seconds = round(frame_idx / fps, 2) if fps else None

    return {
        "fps": fps,
        "width": width,
        "height": height,
        "total_frames": frame_idx,
        "duration_seconds": duration_seconds,
        "people_detected": people_detected,
    }