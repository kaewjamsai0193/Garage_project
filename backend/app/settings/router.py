from fastapi import APIRouter, Depends

from app.auth import current_user, require_role
from app.db import get_db
from app.models import Setting
from app.settings import service
from app.settings.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_settings(db=Depends(get_db), _=Depends(current_user)):
    """GET /api/settings: ผู้ใช้ที่ล็อกอิน → คืนค่าตั้งอู่ (แถว id=1) จาก DB"""
    return db.get(Setting, 1)


@router.put("/settings", response_model=SettingsOut)
def update_settings(data: SettingsIn, db=Depends(get_db), _=Depends(require_role("admin"))):
    """PUT /api/settings: admin ส่ง SettingsIn → service.update_settings → คืนค่าที่บันทึกแล้ว"""
    return service.update_settings(db, data)
