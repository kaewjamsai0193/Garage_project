import os

from fastapi import HTTPException
from sqlalchemy import func, select

from app.auth import hash_password
from app.db import SessionLocal, get_or_404
from app.models import Setting, User

def ensure_admin():
    """ ตรวจสอบว่ามีผู้ใช้ admin อย่างน้อย 1 คน ถ้าไม่มีให้สร้างจาก environment """
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)) == 0:
            db.add(User(username=os.environ["ADMIN_USERNAME"], full_name="ผู้ดูแลระบบ", role="admin",
                        password_hash=hash_password(os.environ["ADMIN_PASSWORD"])))
            db.commit()

def create_user(db, data) -> User:
    """ สร้างผู้ใช้ใหม่ """
    if db.scalar(select(User.id).where(User.username == data.username)):
        raise HTTPException(409, "ชื่อผู้ใช้นี้มีแล้ว")
    user = User(username=data.username, full_name=data.full_name, role=data.role,
                password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return user

def update_user(db, user_id: int, data, actor: User) -> User:
    """ แก้ไขผู้ใช้ """
    user = get_or_404(db, User, user_id, "ผู้ใช้")
    if user.id == actor.id and (data.is_active is False or data.role not in (None, "admin")):
        raise HTTPException(409, "ปิดหรือลดสิทธิ์บัญชีตัวเองไม่ได้")
    for field in ("full_name", "role", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value)
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user

def update_settings(db, data) -> Setting:
    row = db.get(Setting, 1)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row