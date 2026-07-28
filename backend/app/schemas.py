from pydantic import BaseModel


class FaceImage(BaseModel):
    id: int
    image_path: str
    embedding_path: str | None = None
    created_at: str


class Member(BaseModel):
    id: int
    name: str
    created_at: str
    image_count: int


class MemberDetail(Member):
    images: list[FaceImage]


class RegisterMemberResponse(BaseModel):
    member: MemberDetail
    message: str
