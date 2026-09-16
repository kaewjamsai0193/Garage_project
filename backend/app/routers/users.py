from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import current_user, require_role
from app.db import get_db
from app.models import Setting, User
from app.schemas.users import SettingsIn, SettingsOut, UserCreate, UserOut, UserUpdate
from app.services import users as svc

router = APIRouter(prefix="/api", tags=["users"])
admin = require_role("admin")

@router.get("/users", response_model=list[UserOut])
def list_users(db=Depends(get_db), _=Depends(admin)):
    """ ดึงรายชื่อผู้ใช้ทั้งหมด """
    return db.scalars(select(User).order_by(User.username)).all()

@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db=Depends(get_db), _=Depends(admin)):
    """ สร้างผู้ใช้ใหม่ """
    return svc.create_user(db, data)

@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db=Depends(get_db), actor=Depends(admin)):
    """ แก้ไขผู้ใช้ """
    return svc.update_user(db, user_id, data, actor)

@router.get("/users/mechanics", response_model=list[UserOut])
def list_mechanics(db=Depends(get_db), _=Depends(current_user)):
    """ ดึงรายชื่อช่างเทคนิค """
    return db.scalars(select(User).where(User.role == "mechanic", User.is_active)
                      .order_by(User.full_name)).all()

@router.get("/settings", response_model=SettingsOut)
def get_settings(db=Depends(get_db), _=Depends(current_user)):
    """ ดึงตั้งค่าร้าน """
    return db.get(Setting, 1)

@router.put("/settings", response_model=SettingsOut)
def update_settings(data: SettingsIn, db=Depends(get_db), _=Depends(admin)):
    """ แก้ไขตั้งค่าร้าน """
    return svc.update_settings(db, data)