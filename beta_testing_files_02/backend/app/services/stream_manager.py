"""
Quan ly cac stream dang chay trong tien trinh FastAPI - moi camera 1 thread rieng,
dieu khien bang threading.Event (cach 1 - "background task don gian" da chon).

Han che da biet: neu server restart, toan bo thread dang chay se mat (khong tu phuc
hoi) - chap nhan duoc voi quy mo do an, ghi lai o day de khong quen.
"""
import threading


class StreamManager:
    def __init__(self):
        self._threads = {}       # camera_id -> threading.Thread
        self._stop_events = {}   # camera_id -> threading.Event

    def is_streaming(self, camera_id: int) -> bool:
        self.cleanup_finished()
        return camera_id in self._threads and self._threads[camera_id].is_alive()

    def start(self, camera_id: int, target_fn, args: tuple):
        if self.is_streaming(camera_id):
            raise RuntimeError(f"Camera {camera_id} da dang stream roi")

        stop_event = threading.Event()
        self._stop_events[camera_id] = stop_event

        thread = threading.Thread(target=target_fn, args=(*args, stop_event), daemon=True)
        self._threads[camera_id] = thread
        thread.start()

    def stop(self, camera_id: int):
        if camera_id in self._stop_events:
            self._stop_events[camera_id].set()

    def cleanup_finished(self):
        finished = [cid for cid, t in self._threads.items() if not t.is_alive()]
        for cid in finished:
            self._threads.pop(cid, None)
            self._stop_events.pop(cid, None)


stream_manager = StreamManager()