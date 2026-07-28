from typing import List

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: int
    y: int


class ZoneCreate(BaseModel):
    camera_id: int
    name: str
    points: List[Point] = Field(min_length=4, max_length=4)  # bat buoc DUNG 4 diem (tu giac)


class ZoneOut(BaseModel):
    id: int
    camera_id: int
    name: str
    polygon: List[List[int]]

    class Config:
        from_attributes = True