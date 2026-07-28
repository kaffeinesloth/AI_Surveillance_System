import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.config import SNAPSHOTS_DIR, resolve_storage_path
from backend.app.database import db_session
from backend.app.schemas import AlertReadUpdate, AlertView
from backend.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alert_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> AlertService:
    return AlertService(connection)


@router.get("", response_model=list[AlertView])
def list_alerts(
    is_read: bool | None = None,
    camera_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: AlertService = Depends(get_alert_service),
):
    return service.list_alerts(
        is_read=is_read,
        camera_id=camera_id,
        limit=limit,
    )


@router.get("/latest", response_model=AlertView)
def get_latest_alert(service: AlertService = Depends(get_alert_service)):
    alert = service.latest_alert()
    if alert is None:
        raise HTTPException(status_code=404, detail="No alerts found")
    return alert


@router.get("/{alert_id}", response_model=AlertView)
def get_alert(
    alert_id: int,
    service: AlertService = Depends(get_alert_service),
):
    alert = service.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/read", response_model=AlertView)
def update_alert_read_status(
    alert_id: int,
    request: AlertReadUpdate,
    service: AlertService = Depends(get_alert_service),
):
    alert = service.update_read_status(alert_id, is_read=request.is_read)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/{alert_id}/snapshot")
def get_alert_snapshot(
    alert_id: int,
    service: AlertService = Depends(get_alert_service),
):
    alert = service.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    stored_path = alert["snapshot_path"]
    if not stored_path:
        raise HTTPException(status_code=404, detail="Alert has no snapshot")

    path = resolve_storage_path(stored_path)
    if not path.is_relative_to(SNAPSHOTS_DIR.resolve()):
        raise HTTPException(status_code=404, detail="Alert snapshot not found")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Alert snapshot not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
