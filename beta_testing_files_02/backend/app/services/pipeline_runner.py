"""
Vong lap xu ly stream lien tuc tu 1 camera - chay trong THREAD RIENG (xem stream_manager.py),
khac han video upload (1 request roi ket thuc). Ghi truc tiep vao Track/Detection theo
tung frame, va goi BehaviorRuleEngine de tao Alert khi can - vi day la luong "giam sat
lien tuc can luu lich su" (khac video upload da quyet dinh la ephemeral).
"""
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import cv2
import numpy as np
from app.models.person import Person
from app.services.websocket_manager import manager

from app.config import FACE_MATCH_THRESHOLD, TRACK_BUFFER_SIZE
from app.database import SessionLocal
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.detection import Detection
from app.models.track import Track
from app.models.video_session import VideoSession
from app.models.zone import Zone
from app.services.behavior_rule_engine import BehaviorRuleEngine
from app.services.face_recognition_service import face_service
from app.services.person_detector_service import person_detector


def _resolve_source(source_url: str):
    """Webcam thi source_url la so ('0', '1'...) - can doi sang int cho cv2/ultralytics.
    RTSP URL hoac duong dan file thi giu nguyen string."""
    return int(source_url) if source_url.isdigit() else source_url


def run_camera_stream(camera_id: int, stop_event):
    """Ham chay trong 1 THREAD RIENG (goi tu stream_manager.start()). Tu tao Session DB
    RIENG cho thread nay - KHONG dung chung Session voi request da goi start-stream,
    vi SQLAlchemy Session khong thread-safe giua nhieu thread."""
    db = SessionLocal()

    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera is None or not camera.source_url:
            print(f"[stream {camera_id}] Khong tim thay camera hoac chua co source_url, dung lai")
            return

        # Nap vung cam da cau hinh cho camera nay - chi nap MOT LAN luc bat dau stream.
        # Neu sua/them vung cam trong luc dang stream, phai dung roi start lai moi ap dung.
        zones = db.query(Zone).filter(Zone.camera_id == camera_id).all()
        restricted_zones = [{"name": z.name, "polygon": z.polygon} for z in zones]
        print(f"[stream {camera_id}] Da nap {len(restricted_zones)} vung cam")

        session = VideoSession(camera_id=camera_id, status="streaming")
        db.add(session)
        db.commit()
        db.refresh(session)

        engine = BehaviorRuleEngine(restricted_zones=restricted_zones)  # instance RIENG cho session nay
        track_objects = {}   # track_id (ByteTrack) -> Track (SQLAlchemy object, cache trong RAM)
        track_buffers = defaultdict(lambda: deque(maxlen=TRACK_BUFFER_SIZE))

        source = _resolve_source(camera.source_url)
        frame_idx = 0
        width, height = None, None
        start_time = time.time()

        results_gen = person_detector.track(source, conf=0.4)

        for r in results_gen:
            if stop_event.is_set():
                print(f"[stream {camera_id}] Nhan tin hieu dung, thoat vong lap")
                break

            frame = r.orig_img
            if width is None:
                height, width = frame.shape[:2]
                session.frame_width = width
                session.frame_height = height
                db.commit()

            boxes = r.boxes
            # Dung DONG HO THUC (wall-clock), KHONG dung frame_idx/fps - vi toc do xu ly
            # thuc te co the cham hon FPS camera (CPU chay YOLOv8+insightface), dung
            # frame_idx/fps se tinh SAI thoi gian that, anh huong truc tiep rule loitering.
            timestamp_sec = time.time() - start_time

            if boxes is not None and len(boxes) > 0 and boxes.id is not None:
                xyxy = boxes.xyxy.cpu().numpy().astype(int)
                track_ids = boxes.id.cpu().numpy().astype(int)
                confs = boxes.conf.cpu().numpy()

                for (x1, y1, x2, y2), track_id, conf in zip(xyxy, track_ids, confs):
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)
                    person_crop = frame[y1:y2, x1:x2]
                    if person_crop.size == 0:
                        continue

                    track_id_int = int(track_id)

                    if track_id_int not in track_objects:
                        track = Track(
                            video_session_id=session.id,
                            track_id=track_id_int,
                            first_seen_frame=frame_idx,
                            first_seen_timestamp=round(timestamp_sec, 2),
                            last_seen_frame=frame_idx,
                            last_seen_timestamp=round(timestamp_sec, 2),
                        )
                        db.add(track)
                        db.flush()  # co track.id ngay de gan cho Detection ben duoi
                        track_objects[track_id_int] = track
                    else:
                        track = track_objects[track_id_int]
                        track.last_seen_frame = frame_idx
                        track.last_seen_timestamp = round(timestamp_sec, 2)

                    emb, det_score = face_service.get_embedding(person_crop)
                    buffer = track_buffers[track_id_int]

                    raw_person_id_str, raw_score = None, None
                    if emb is not None:
                        raw_person_id_str, raw_score = face_service.match_raw(emb)
                        buffer.append((raw_person_id_str, raw_score))
                    # Khong thay mat frame nay: KHONG xoa buffer, giu nguyen lich su cu

                    db.add(Detection(
                        video_session_id=session.id,
                        track_id=track.id,
                        frame_number=frame_idx,
                        timestamp_sec=round(timestamp_sec, 2),
                        bbox_x1=int(x1), bbox_y1=int(y1), bbox_x2=int(x2), bbox_y2=int(y2),
                        matched_person_id=int(raw_person_id_str) if raw_person_id_str else None,
                        match_score=raw_score,
                        person_conf=float(conf),
                    ))

                    avg_score = None
                    is_known = False
                    if len(buffer) > 0:
                        avg_score = float(np.mean([s for _, s in buffer]))
                        names_in_buffer = [n for n, _ in buffer if n is not None]
                        majority_person_id_str = (
                            max(set(names_in_buffer), key=names_in_buffer.count)
                            if names_in_buffer else None
                        )
                        is_known = majority_person_id_str is not None and avg_score >= FACE_MATCH_THRESHOLD
                        track.matched_person_id = int(majority_person_id_str) if is_known else None
                        track.avg_match_score = avg_score

                    triggered_alerts = engine.evaluate(
                        track_id=track_id_int,
                        bbox=(x1, y1, x2, y2),
                        is_known=is_known,
                        timestamp=timestamp_sec,
                    )

                    for alert_type in triggered_alerts:
                        alert = Alert(
                            video_session_id=session.id,
                            camera_id=camera_id,
                            track_id=track.id,
                            person_id=track.matched_person_id,
                            alert_type=alert_type,
                            confidence=avg_score,
                        )
                        db.add(alert)
                        db.flush()  # co alert.id ngay de gui kem trong broadcast

                        person_name = None
                        if track.matched_person_id:
                            person = db.query(Person).filter(Person.id == track.matched_person_id).first()
                            person_name = person.name if person else None

                        manager.broadcast_from_thread({
                            "type": "new_alert",
                            "alert_id": alert.id,
                            "camera_id": camera_id,
                            "camera_name": camera.name,
                            "alert_type": alert_type,
                            "person_name": person_name,
                            "track_id": track_id_int,
                            "confidence": avg_score,
                            "timestamp": round(timestamp_sec, 2),
                        })

            db.commit()
            frame_idx += 1

        elapsed = time.time() - start_time
        session.status = "stopped"
        session.ended_at = datetime.now(timezone.utc)
        session.fps = round(frame_idx / elapsed, 2) if elapsed > 0 else None  # FPS THUC TE dat duoc
        db.commit()
        print(f"[stream {camera_id}] Da dung, tong {frame_idx} frame trong {elapsed:.1f}s")

    except Exception as e:
        print(f"[stream {camera_id}] Loi: {e}")
        db.rollback()

    finally:
        db.close()