"""
Rule-based behavior engine - port nguyen ven tu Notebook 03. Nhan tung 'su kien' theo
DUNG THU TU THOI GIAN (track_id, bbox, is_known, timestamp), tra ve list ten alert
duoc kich hoat tai thoi diem do.

QUAN TRONG: moi VideoSession (moi lan start-stream) can 1 instance MOI cua class nay -
state (lich su tung track_id) khong duoc dung chung giua cac session/camera khac nhau
(xem pipeline_runner.py, engine duoc tao moi o dau moi lan chay).
"""
import cv2
import numpy as np


class BehaviorRuleEngine:
    def __init__(self, restricted_zones=None, loitering_seconds=30,
                 unknown_min_frames=5, alert_cooldown_seconds=10):
        self.restricted_zones = restricted_zones or []
        self.loitering_seconds = loitering_seconds
        self.unknown_min_frames = unknown_min_frames
        self.alert_cooldown_seconds = alert_cooldown_seconds

        self.track_state = {}

    def _point_in_zone(self, point, polygon):
        contour = np.array(polygon, dtype=np.int32)
        result = cv2.pointPolygonTest(contour, point, False)
        return result >= 0

    def _should_fire(self, state, alert_key, timestamp):
        last_time = state["last_alert_time"].get(alert_key)
        if last_time is None or (timestamp - last_time) >= self.alert_cooldown_seconds:
            state["last_alert_time"][alert_key] = timestamp
            return True
        return False

    def evaluate(self, track_id, bbox, is_known, timestamp):
        x1, y1, x2, y2 = bbox
        foot_point = (int((x1 + x2) / 2), int(y2))

        state = self.track_state.setdefault(track_id, {
            "first_seen": timestamp,
            "last_seen": timestamp,
            "unknown_streak": 0,
            "last_alert_time": {},
        })
        state["last_seen"] = timestamp

        triggered = []

        if not is_known:
            state["unknown_streak"] += 1
        else:
            state["unknown_streak"] = 0

        if state["unknown_streak"] >= self.unknown_min_frames:
            if self._should_fire(state, "unknown_face", timestamp):
                triggered.append("unknown_face")

        for zone in self.restricted_zones:
            if self._point_in_zone(foot_point, zone["polygon"]):
                alert_key = f"zone_intrusion:{zone['name']}"
                if self._should_fire(state, alert_key, timestamp):
                    triggered.append(alert_key)

        dwell_seconds = state["last_seen"] - state["first_seen"]
        if dwell_seconds >= self.loitering_seconds:
            if self._should_fire(state, "loitering", timestamp):
                triggered.append("loitering")

        return triggered