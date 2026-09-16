import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from app.db import get_db
from app.models import User

ROUNDS = 600_000

def hash_password(pw: str) -> str:
    """ แฮชรหัสผ่านด้วย PBKDF2-HMAC-SHA256 """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ROUNDS)
    return f"pbkdf2_sha256${ROUNDS}${salt.hex()}${digest.hex()}"

def verify_password(pw: str, stored: str) -> bool:
    """ ตรวจสอบรหัสผ่าน """
    _, rounds, salt, digest = stored.split("$")
    got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(got.hex(), digest)

def create_token(user_id: int) -> str:
    """ สร้าง JWT token """
    exp = datetime.now(timezone.utc) + timedelta(minutes=int(os.environ["JWT_EXPIRE_MINUTES"]))
    return jwt.encode({"sub": str(user_id), "exp": exp}, os.environ["JWT_SECRET"], algorithm="HS256")

bearer = HTTPBearer(auto_error=False)

def current_user(cred=Depends(bearer), db=Depends(get_db)) -> User:
    """ ดึงผู้ใช้ปัจจุบันจาก JWT token """
    try:
        payload = jwt.decode(cred.credentials, os.environ["JWT_SECRET"], algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (AttributeError, jwt.PyJWTError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(401, "กรุณาเข้าสู่ระบบ")
    return user

def require_role(*roles):
    """ ตรวจสอบสิทธิ์ผู้ใช้ """
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
        return user
    return dep