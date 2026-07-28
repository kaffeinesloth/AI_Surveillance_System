from typing import Optional
from pydantic import BaseModel

class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    source_url: str

class CameraOut(BaseModel):
    id: int
    name: str
    location: Optional[str]
    source_url: str
    is_active: bool

    class Config:
        from_attributes  = True