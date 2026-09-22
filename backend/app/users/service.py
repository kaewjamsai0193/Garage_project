import os

from fastapi import HTTPException
from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal, get_or_404
from app.models import User


def ensure_admin():
    """ถ้า DB ยังไม่มี admin เลย สร้างจาก env ADMIN_USERNAME/ADMIN_PASSWORD (เรียกจาก lifespan)"""
    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.role == "admin"))
        if admin_user is None:
            db.add(
                User(
                    username=os.environ["ADMIN_USERNAME"],
                    full_name="ผู้ดูแลระบบ",
                    role="admin",
                    password_hash=hash_password(os.environ["ADMIN_PASSWORD"]),
                )
            )
            db.commit()


def create_user(db, data) -> User:
    """กันชื่อผู้ใช้ซ้ำ → hash รหัสผ่าน → บันทึก User ใหม่"""
    if db.scalar(select(User.id).where(User.username == data.username)):
        raise HTTPException(409, "ชื่อผู้ใช้นี้มีแล้ว")
    user = User(
        username=data.username, full_name=data.full_name, role=data.role, password_hash=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    return user


def update_user(db, user_id: int, data, actor: User) -> User:
    """แก้เฉพาะฟิลด์ที่ส่งมา, กัน admin ปิด/ลดสิทธิ์ตัวเอง, มีรหัสใหม่ก็ hash ใหม่"""
    user = get_or_404(db, User, user_id, "ผู้ใช้")
    is_self = user.id == actor.id
    disabling = data.is_active is False
    demoting = data.role is not None and data.role != "admin"
    if is_self and (disabling or demoting):
        raise HTTPException(409, "ปิดหรือลดสิทธิ์บัญชีตัวเองไม่ได้")
    for key, value in data.model_dump(exclude_none=True, exclude={"password"}).items():
        setattr(user, key, value)
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user
