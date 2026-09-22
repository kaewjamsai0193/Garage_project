from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import create_token, current_user, verify_password
from app.db import get_db
from app.models import User
from app.users.schemas import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, db=Depends(get_db)):
    """POST /api/auth/login: รับ username/password → เช็คกับ DB → คืน JWT + ข้อมูลผู้ใช้"""
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return {"access_token": create_token(user.id), "user": user}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    """GET /api/auth/me: คืนข้อมูลผู้ใช้เจ้าของ token (frontend ใช้ตอนเปิดแอป)"""
    return user
