from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import auth, users
from app.services.users import ensure_admin


@asynccontextmanager
async def lifespan(_app):
    ensure_admin()
    yield

app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)

@app.exception_handler(IntegrityError)
def integrity_error(_request, _exc):
    """ ขัดกับกฎของฐานข้อมูล """
    return JSONResponse(status_code=409, content={"detail": "ข้อมูลขัดกับกฎของระบบ"})

@app.get("/api/health")
def health():
    return {"ok": True}
