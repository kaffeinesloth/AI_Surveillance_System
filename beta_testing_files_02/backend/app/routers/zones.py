from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneOut

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/", response_model=ZoneOut)
def create_zone(zone: ZoneCreate, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == zone.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Khong tim thay camera")

    polygon = [[p.x, p.y] for p in zone.points]

    new_zone = Zone(camera_id=zone.camera_id, name=zone.name, polygon=polygon)
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    return new_zone


@router.get("/", response_model=List[ZoneOut])
def list_zones(camera_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Zone)
    if camera_id is not None:
        query = query.filter(Zone.camera_id == camera_id)
    return query.all()


@router.delete("/{zone_id}")
def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Khong tim thay vung cam")

    db.delete(zone)
    db.commit()
    return {"detail": f"Da xoa vung cam '{zone.name}'"}