from datetime import datetime
from pydantic import BaseModel


class PersonOut(BaseModel):
    id: int
    name: str
    role: str
    enrolled_at: datetime

    class Config:
        from_attributes = True


# Luu y: khong dung PersonCreate (Pydantic body JSON) cho endpoint /enroll, vi endpoint
# do nhan ca file anh (multipart/form-data) - FastAPI khong cho tron 1 Pydantic body voi
# File() trong cung 1 request de dang, nen enrollment.py dung Form(...) rieng cho name/role.
