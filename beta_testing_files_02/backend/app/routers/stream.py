from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.services.pipeline_runner import run_camera_stream
from app.services.stream_manager import stream_manager

router = APIRouter(prefix="/cameras", tags=["stream"])


@router.post("/{camera_id}/start-stream")
def start_stream(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="Khong tim thay camera")

    if not camera.source_url:
        raise HTTPException(status_code=400, detail="Camera chua co source_url, khong the stream")

    if stream_manager.is_streaming(camera_id):
        raise HTTPException(status_code=409, detail="Camera nay dang stream roi")

    stream_manager.start(camera_id, run_camera_stream, args=(camera_id,))
    return {"detail": f"Da bat dau stream cho camera '{camera.name}'", "camera_id": camera_id}


@router.post("/{camera_id}/stop-stream")
def stop_stream(camera_id: int):
    if not stream_manager.is_streaming(camera_id):
        raise HTTPException(status_code=400, detail="Camera nay khong dang stream")

    stream_manager.stop(camera_id)
    return {"detail": f"Da gui tin hieu dung stream cho camera {camera_id} (co the mat vai giay de dung han)"}


@router.get("/{camera_id}/stream-status")
def get_stream_status(camera_id: int):
    return {"camera_id": camera_id, "is_streaming": stream_manager.is_streaming(camera_id)}