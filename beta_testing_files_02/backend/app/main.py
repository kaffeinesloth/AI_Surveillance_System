import os
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
import asyncio
from fastapi.middleware.cors import CORSMiddleware

from app.services.websocket_manager import manager
from app.database import Base, SessionLocal, engine
from app.models.person import Person
from app.routers import alerts, cameras, enrollment, stream, videos, zones, websocket_alerts
from app.services.face_recognition_service import face_service
from app.services.person_detector_service import person_detector


def load_gallery_from_db() -> None:
    db = SessionLocal()
    try:
        persons = db.query(Person).all()
        loaded = 0
        for p in persons:
            if p.embedding_path and os.path.exists(p.embedding_path):
                embedding = np.load(p.embedding_path)
                face_service.add_to_gallery(p.id, embedding)
                loaded += 1
        print(f"[startup] Da nap {loaded}/{len(persons)} nguoi vao gallery")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    print("[startup] Dang load model face recognition (insightface buffalo_l)...")
    face_service.load_model()

    print("[startup] Dang load model person detection (YOLOv8)...")
    person_detector.load_model()

    load_gallery_from_db()
    print("[startup] San sang nhan request")

    manager.set_main_loop(asyncio.get_running_loop()) #websocket manager can main loop de gui message tu background thread

    yield


app = FastAPI(title="Face Security System API", lifespan=lifespan)

#CORS (Cross-Origin Resource Sharing) — mặc định FastAPI từ chối mọi request đến từ origin khác (domain/IP khác với chính nó)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo/do an: cho phep tat ca. San xuat that thi gioi han lai domain cu the
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrollment.router)
app.include_router(alerts.router)
app.include_router(videos.router)
app.include_router(cameras.router)
app.include_router(stream.router)
app.include_router(zones.router)
app.include_router(websocket_alerts.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "gallery_size": len(face_service.gallery)}