import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import get_db
from app.services.video_analysis_service import analyze_video

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")


@router.post("/upload")
def upload_and_analyze_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload 1 video, chay cascade, tra ket qua TRUC TIEP ve response.

    KHONG ghi gi vao video_sessions/tracks/detections - xu ly hoan toan trong bo nho.
    Tat/mo lai app la mat ket qua nay, DUNG Y THIET KE (video upload la thao tac
    kiem tra 1 lan, khong phai giam sat lien tuc can luu lich su).

    `db` van duoc truyen vao analyze_video() nhung CHI DE DOC (tra ten Person tu
    person_id khop duoc trong gallery) - khong co dong INSERT/UPDATE/COMMIT nao
    trong toan bo luong xu ly nay.
    """
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Chi ho tro file video ({', '.join(ALLOWED_EXTENSIONS)})",
        )

    temp_filename = f"{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    with open(temp_path, "wb") as f:
        f.write(file.file.read())

    try:
        result = analyze_video(temp_path, db)

        return {
            "filename": file.filename,
            "status": "completed",
            "total_frames": result["total_frames"],
            "duration_seconds": result["duration_seconds"],
            "people_detected": result["people_detected"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xu ly video: {e}")

    finally:
        # Video goc cung khong giu lai - khong con gi tham chieu toi no sau khi tra response
        if os.path.exists(temp_path):
            os.remove(temp_path)