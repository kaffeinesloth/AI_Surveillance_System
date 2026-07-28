import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.app.database import db_session
from backend.app.schemas import (
    Camera,
    CameraCreate,
    CameraDeleteResponse,
    CameraTestResponse,
    CameraUpdate,
)
from backend.camera.webcam import CameraCaptureService, CameraUnavailableError
from backend.services.camera_service import CameraService
from backend.services.surveillance_manager import LiveSurveillanceManager
from backend.routes.surveillance_routes import get_surveillance_manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


def get_camera_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> CameraService:
    return CameraService(connection)


def get_camera_capture_service() -> CameraCaptureService:
    return CameraCaptureService()


@router.post("", response_model=Camera, status_code=201)
def create_camera(
    request: CameraCreate,
    service: CameraService = Depends(get_camera_service),
):
    try:
        return service.create_camera(
            name=request.name,
            source=request.source,
            location=request.location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Camera])
def list_cameras(
    include_inactive: bool = False,
    service: CameraService = Depends(get_camera_service),
):
    return service.list_cameras(include_inactive=include_inactive)


@router.get("/{camera_id}", response_model=Camera)
def get_camera(
    camera_id: int,
    service: CameraService = Depends(get_camera_service),
):
    camera = service.get_camera(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.patch("/{camera_id}", response_model=Camera)
def update_camera(
    camera_id: int,
    request: CameraUpdate,
    service: CameraService = Depends(get_camera_service),
):
    try:
        camera = service.update_camera(
            camera_id,
            request.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.delete("/{camera_id}", response_model=CameraDeleteResponse)
def deactivate_camera(
    camera_id: int,
    service: CameraService = Depends(get_camera_service),
):
    camera = service.deactivate_camera(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {
        "message": "Camera deactivated",
        "camera": camera,
    }


def _camera_and_snapshot(
    camera_id: int,
    camera_service: CameraService,
    capture_service: CameraCaptureService,
    surveillance: LiveSurveillanceManager,
):
    camera = camera_service.get_camera(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not camera["is_active"]:
        raise HTTPException(status_code=409, detail="Camera is inactive")
    if surveillance.is_camera_running(camera_id):
        raise HTTPException(
            status_code=409,
            detail="Camera is currently used by live surveillance",
        )
    try:
        snapshot = capture_service.capture_snapshot(camera["source"])
    except (CameraUnavailableError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return camera, snapshot


@router.post("/{camera_id}/test", response_model=CameraTestResponse)
def test_camera(
    camera_id: int,
    camera_service: CameraService = Depends(get_camera_service),
    capture_service: CameraCaptureService = Depends(
        get_camera_capture_service
    ),
    surveillance: LiveSurveillanceManager = Depends(
        get_surveillance_manager
    ),
):
    _, snapshot = _camera_and_snapshot(
        camera_id,
        camera_service,
        capture_service,
        surveillance,
    )
    return {
        "available": True,
        "width": snapshot.width,
        "height": snapshot.height,
        "message": "Camera source is available",
    }


@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(
    camera_id: int,
    camera_service: CameraService = Depends(get_camera_service),
    capture_service: CameraCaptureService = Depends(
        get_camera_capture_service
    ),
    surveillance: LiveSurveillanceManager = Depends(
        get_surveillance_manager
    ),
):
    _, snapshot = _camera_and_snapshot(
        camera_id,
        camera_service,
        capture_service,
        surveillance,
    )
    return Response(
        content=snapshot.content,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
