from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import create_token, current_user, verify_password
from app.db import get_db
from app.models import User
from app.schemas.users import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, db=Depends(get_db)):
    """ เข้าสู่ระบบ """
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return {"access_token": create_token(user.id), "user": user}


@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    """ดึงข้อมูลผู้ใช้ปัจจุบันว่าเป็นใคร"""
    return user