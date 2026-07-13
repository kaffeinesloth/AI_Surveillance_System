from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.app.database import db_session
from backend.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/register")
async def register_member(
    name: str = Form(...),
    images: list[UploadFile] = File(...),
    connection=Depends(db_session),
):
    try:
        return await MemberService(connection).register_member(name=name, images=images)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_members(connection=Depends(db_session)):
    return MemberService(connection).list_members()


@router.get("/{member_id}")
def get_member(member_id: int, connection=Depends(db_session)):
    member = MemberService(connection).get_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.delete("/{member_id}")
def delete_member(member_id: int, connection=Depends(db_session)):
    result = MemberService(connection).delete_member(member_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return result
