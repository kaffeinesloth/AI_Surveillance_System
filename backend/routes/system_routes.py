import sqlite3

from fastapi import APIRouter, Depends

from backend.app.database import db_session
from backend.services.readiness_service import ReadinessService
from backend.services.surveillance_manager import surveillance_manager
from backend.services.video_analysis_manager import video_analysis_manager

router = APIRouter(tags=["system"])


def get_readiness_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> ReadinessService:
    return ReadinessService(connection)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/readiness")
def readiness_check(
    service: ReadinessService = Depends(get_readiness_service),
) -> dict:
    result = service.inspect()
    result["workers"] = {
        "live_surveillance_running": surveillance_manager.status().running,
        "video_analysis_running": video_analysis_manager.has_active_job(),
    }
    return result
