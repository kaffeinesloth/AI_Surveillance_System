from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """App Flutter ket noi vao day de nhan alert real-time. Khong can gui gi len -
    chi giu ket noi mo de server day du lieu xuong khi co alert moi."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)