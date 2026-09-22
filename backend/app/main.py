from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.settings import router as settings
from app.stock import router as stock
from app.users import auth_router as auth
from app.users import router as users
from app.users.service import ensure_admin


@asynccontextmanager
async def lifespan(_app):
    """ตอนเซิร์ฟเวอร์เริ่ม: สร้างบัญชี admin จาก env ถ้ายังไม่มี"""
    ensure_admin()
    yield


app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings.router)
app.include_router(stock.router)


@app.exception_handler(IntegrityError)
def handle_integrity_error(_request, _exc):
    """แปลง IntegrityError จาก DB (ชน unique/check) → HTTP 409 ข้อความไทย"""
    return JSONResponse(status_code=409, content={"detail": "ข้อมูลขัดกับกฎของระบบ"})


@app.get("/api/health")
def health():
    """GET /api/health: เช็คว่าเซิร์ฟเวอร์ยังทำงาน"""
    return {"ok": True}
