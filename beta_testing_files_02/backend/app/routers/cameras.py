from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraOut
from app.services.stream_manager import stream_manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("/", response_model=CameraOut)
def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    new_camera = Camera(name=camera.name, location=camera.location, source_url=camera.source_url)
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)
    return new_camera


@router.get("/", response_model=List[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Khong tim thay camera")
    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Khong tim thay camera")

    if stream_manager.is_streaming(camera_id):
        raise HTTPException(
            status_code=409,
            detail="Camera nay dang stream - dung stream (POST /cameras/{id}/stop-stream) truoc khi xoa",
        )

    db.delete(camera)
    db.commit()
    return {"detail": f"Da xoa camera '{camera.name}'"}

@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db)):
    """Lay 1 khung hinh HIEN TAI tu camera - dung de app hien thi cho nguoi dung nhin
    thay roi moi bam chon 4 toa do vung cam (giong buoc xem luoi toa do o Notebook 03).

    LUU Y QUAN TRONG: se KHONG hoat dong khi camera dang stream (webcam/RTSP thuong
    chi cho 1 tien trinh mo cung luc) - lay snapshot va cau hinh vung cam TRUOC khi
    bam start-stream.
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Khong tim thay camera")

    if not camera.source_url:
        raise HTTPException(status_code=400, detail="Camera chua co source_url")

    if stream_manager.is_streaming(camera_id):
        raise HTTPException(
            status_code=409,
            detail="Camera dang stream, khong the lay snapshot cung luc - dung stream truoc",
        )

    source = int(camera.source_url) if camera.source_url.isdigit() else camera.source_url
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        cap.release()
        raise HTTPException(status_code=500, detail=f"Khong mo duoc nguon: {camera.source_url}")

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Khong doc duoc khung hinh tu camera")

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise HTTPException(status_code=500, detail="Loi encode anh")

    return Response(content=buffer.tobytes(), media_type="image/jpeg")