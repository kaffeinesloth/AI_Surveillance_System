import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.app.database import db_session
from backend.app.schemas import (
    DeleteMemberResponse,
    Member,
    MemberDetail,
    RegisterMemberResponse,
)
from backend.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])


def get_member_service(
    connection: sqlite3.Connection = Depends(db_session),
) -> MemberService:
    return MemberService(connection)


@router.post("/register", response_model=RegisterMemberResponse)
async def register_member(
    name: str = Form(...),
    images: list[UploadFile] = File(...),
    service: MemberService = Depends(get_member_service),
):
    try:
        return await service.register_member(name=name, images=images)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Member])
def list_members(service: MemberService = Depends(get_member_service)):
    return service.list_members()


@router.get("/{member_id}", response_model=MemberDetail)
def get_member(
    member_id: int,
    service: MemberService = Depends(get_member_service),
):
    member = service.get_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.delete("/{member_id}", response_model=DeleteMemberResponse)
def delete_member(
    member_id: int,
    service: MemberService = Depends(get_member_service),
):
    deleted = service.delete_member(member_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member deleted"}
