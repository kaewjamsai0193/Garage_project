import os

from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def get_db():
    """Dependency: เปิด DB session ให้ endpoint แล้วปิดเองเมื่อจบ request"""
    with SessionLocal() as db:
        yield db


SHOP_LOCK = 71001


def lock_shop(db):
    """อู่สาขาเดียว ล็อกตัวเดียวพอ: คำสั่งที่แตะสต็อก จัดซื้อ บิล ทำทีละคำสั่ง"""
    db.execute(text("select pg_advisory_xact_lock(:k)"), {"k": SHOP_LOCK})


def get_or_404(db, model, id, label):
    """ดึงแถวจาก DB ตาม id ถ้าไม่เจอโยน 404 ไม่พบ{label}"""
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, f"ไม่พบ{label}")
    return obj
