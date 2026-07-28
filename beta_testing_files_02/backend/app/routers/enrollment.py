import os
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import EMBEDDINGS_DIR
from app.database import get_db
from app.models.person import Person
from app.schemas.person import PersonOut
from app.services.face_recognition_service import face_service

router = APIRouter(prefix="/enroll", tags=["enrollment"])


@router.post("/", response_model=PersonOut)
async def enroll_person(
    name: str = Form(...),
    role: str = Form("authorized"),
    photos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Dang ky 1 nguoi moi: nhan 1 hoac nhieu anh, tinh embedding TRUNG BINH (khong train
    lai model - chi chay forward qua model da co san, xem giai thich o cau hoi truoc).
    Luu vector vao file .npy + ghi record vao SQLite, va them ngay vao gallery dang chay
    trong RAM de nhan dien duoc NGAY, khong can restart server."""
    if not photos:
        raise HTTPException(status_code=400, detail="Can it nhat 1 anh de dang ky")

    embeddings = []
    n_no_face = 0

    for photo in photos:
        contents = await photo.read()
        img_array = np.frombuffer(contents, dtype=np.uint8)
        img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img_bgr is None:
            continue

        emb, det_score = face_service.get_embedding(img_bgr)
        if emb is not None:
            embeddings.append(emb)
        else:
            n_no_face += 1

    if not embeddings:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Khong phat hien duoc khuon mat ro rang trong bat ky anh nao "
                f"({n_no_face}/{len(photos)} anh khong thay mat). Thu anh khac ro hon."
            ),
        )

    mean_emb = np.mean(embeddings, axis=0)
    mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-10)

    # 1) Tao record Person truoc de lay id (dung id lam ten file .npy - id la duy nhat,
    #    khac voi ten nguoi co the trung nhau)
    new_person = Person(name=name, role=role)
    db.add(new_person)
    db.commit()
    db.refresh(new_person)

    # 2) Luu embedding ra file .npy
    embedding_path = os.path.join(EMBEDDINGS_DIR, f"{new_person.id}.npy")
    np.save(embedding_path, mean_emb)

    new_person.embedding_path = embedding_path
    db.commit()
    db.refresh(new_person)

    # 3) Them vao gallery trong RAM - co the nhan dien nguoi nay NGAY LAP TUC
    face_service.add_to_gallery(new_person.id, mean_emb)

    return new_person


@router.get("/", response_model=List[PersonOut])
def list_enrolled_persons(db: Session = Depends(get_db)):
    return db.query(Person).all()


@router.delete("/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi nay")

    if person.embedding_path and os.path.exists(person.embedding_path):
        os.remove(person.embedding_path)

    face_service.remove_from_gallery(person.id)

    db.delete(person)
    db.commit()
    return {"detail": f"Da xoa '{person.name}' khoi he thong"}
