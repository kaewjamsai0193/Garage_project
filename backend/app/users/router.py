from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import require_role
from app.db import get_db
from app.models import User
from app.users import service
from app.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])
admin = require_role("admin")


@router.get("/users", response_model=list[UserOut])
def list_users(db=Depends(get_db), _=Depends(admin)):
    """GET /api/users: admin ดูผู้ใช้ทั้งหมดเรียงตาม id"""
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db=Depends(get_db), _=Depends(admin)):
    """POST /api/users: admin สร้างผู้ใช้ผ่าน service.create_user"""
    return service.create_user(db, data)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db=Depends(get_db), actor=Depends(admin)):
    """PATCH /api/users/{id}: admin แก้ชื่อ/role/สถานะ/รหัสผ่าน ผ่าน service.update_user"""
    return service.update_user(db, user_id, data, actor)
