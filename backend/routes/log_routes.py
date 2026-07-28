import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.database import db_session
from backend.app.models import DetectionStatus
from backend.app.schemas import DetectionLogView
from backend.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["logs"])


def get_log_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> LogService:
    return LogService(connection)


@router.get("", response_model=list[DetectionLogView])
def list_logs(
    status: DetectionStatus | None = None,
    camera_id: int | None = Query(default=None, gt=0),
    session_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: LogService = Depends(get_log_service),
):
    return service.list_logs(
        status=status,
        camera_id=camera_id,
        session_id=session_id,
        limit=limit,
    )


@router.get("/latest", response_model=DetectionLogView)
def get_latest_log(service: LogService = Depends(get_log_service)):
    log = service.latest_log()
    if log is None:
        raise HTTPException(status_code=404, detail="No detection logs found")
    return log
