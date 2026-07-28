"""
Quan ly cac ket noi WebSocket dang mo (app Flutter dang lang nghe alert real-time).

Vi pipeline_runner.py chay trong THREAD RIENG (khong phai asyncio event loop chinh),
can dung asyncio.run_coroutine_threadsafe() de "bac cau" tu ham dong bo (thread nen)
sang coroutine bat dong bo mot cach AN TOAN - khong the goi truc tiep await tu 1 ham
dong bo binh thuong.
"""
import asyncio
from typing import List, Optional
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        """Goi 1 LAN luc FastAPI khoi dong (xem app/main.py) - luu lai event loop
        CHINH, de sau nay thread nen (pipeline_runner.py) biet phai gui coroutine vao dau."""
        self.main_loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def broadcast_from_thread(self, message: dict) -> None:
        """Goi ham nay TU THREAD NEN (pipeline_runner.py) - an toan vi dung
        run_coroutine_threadsafe() de dua coroutine vao dung main event loop,
        khong goi await truc tiep (se loi vi thread nen khong co event loop rieng)."""
        if self.main_loop is None:
            print("[websocket] Chua co main_loop (server chua khoi dong xong?), bo qua broadcast")
            return

        asyncio.run_coroutine_threadsafe(self._broadcast(message), self.main_loop)

manager = ConnectionManager()