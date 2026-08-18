import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.app.database import db_session
from backend.app.schemas import Zone, ZoneCreate, ZoneUpdate
from backend.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["zones"])


def get_zone_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> ZoneService:
    return ZoneService(connection)


@router.post("", response_model=Zone, status_code=201)
def create_zone(
    request: ZoneCreate,
    service: ZoneService = Depends(get_zone_service),
):
    try:
        return service.create_zone(
            camera_id=request.camera_id,
            name=request.name,
            points=[point.model_dump() for point in request.points],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="A zone with this name already exists for the camera",
        ) from exc


@router.get("", response_model=list[Zone])
def list_zones(
    camera_id: int | None = None,
    include_inactive: bool = False,
    service: ZoneService = Depends(get_zone_service),
):
    return service.list_zones(
        camera_id=camera_id,
        include_inactive=include_inactive,
    )


@router.patch("/{zone_id}", response_model=Zone)
def update_zone(
    zone_id: int,
    request: ZoneUpdate,
    service: ZoneService = Depends(get_zone_service),
):
    try:
        zone = service.update_zone(zone_id, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="A zone with this name already exists for the camera",
        ) from exc
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.delete("/{zone_id}", response_model=Zone)
def delete_zone(
    zone_id: int,
    service: ZoneService = Depends(get_zone_service),
):
    zone = service.delete_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone
