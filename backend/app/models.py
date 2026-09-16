"""16 ตาราง — เฟส 1 เริ่มที่ users กับ settings แล้วเติมทีละเฟส

ตอนนี้ว่างไว้ก่อน มีไว้ให้ alembic/env.py import ได้ตั้งแต่เฟส 0
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base  # noqa: F401

MONEY = Numeric(12, 2)
PRICE = Numeric(14, 4)
QTY = Numeric(12, 3)
RATE = Numeric(5, 2)
TS = DateTime(timezone=True)

def fk(target, **kw):
    return mapped_column(ForeignKey(target, **kw), index=True)

def created():
    return mapped_column(TS, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (CheckConstraint("role in ('admin','employee','mechanic')", name="role"),)


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    shop_name: Mapped[str] = mapped_column(String(200), server_default="")
    shop_address: Mapped[str] = mapped_column(Text, server_default="")
    shop_tax_id: Mapped[str] = mapped_column(String(20), server_default="")
    vat_rate: Mapped[Decimal] = mapped_column(RATE, server_default="7")
    repair_warranty_days: Mapped[int] = mapped_column(server_default="30")
    dead_stock_days: Mapped[int] = mapped_column(server_default="90")
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("vat_rate >= 0", name="vat_rate"),
        CheckConstraint("repair_warranty_days >= 0", name="warranty_days"),
        CheckConstraint("dead_stock_days > 0", name="dead_stock_days"),
    )