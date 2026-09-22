from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func, select, text
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db import Base

MONEY = Numeric(12, 2)
PRICE = Numeric(14, 4)
QTY = Numeric(12, 3)
RATE = Numeric(5, 2)
TS = DateTime(timezone=True)


def created():
    """คอลัมน์ created_at ที่ DB ใส่เวลาปัจจุบันให้เอง"""
    return mapped_column(TS, server_default=func.now())


def fk(target, **kw):
    """คอลัมน์ foreign key ไปยัง target พร้อม index"""
    return mapped_column(ForeignKey(target, **kw), index=True)


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
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("vat_rate >= 0", name="vat_rate"),
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(20))
    sale_price: Mapped[Decimal] = mapped_column(PRICE)
    min_stock: Mapped[Decimal] = mapped_column(QTY, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="sale_price"),
        CheckConstraint("min_stock >= 0", name="min_stock"),
    )


class StockLot(Base):
    __tablename__ = "stock_lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = fk("products.id")
    source_type: Mapped[str] = mapped_column(String(12))
    unit_cost: Mapped[Decimal] = mapped_column(PRICE)
    qty_received: Mapped[Decimal] = mapped_column(QTY)
    qty_remaining: Mapped[Decimal] = mapped_column(QTY)
    cost_total: Mapped[Decimal] = mapped_column(MONEY)
    created_by: Mapped[int] = fk("users.id")
    created_at: Mapped[datetime] = created()
    product: Mapped["Product"] = relationship()
    __table_args__ = (
        CheckConstraint("source_type in ('adjustment','opening')", name="source_type"),
        CheckConstraint("qty_received > 0 and qty_remaining >= 0 and qty_remaining <= qty_received", name="qty"),
        CheckConstraint("unit_cost >= 0 and cost_total >= 0", name="cost"),
        Index("ix_stock_lots_fifo", "product_id", "created_at", "id"),
    )


Product.qty_on_hand = column_property(
    select(func.coalesce(func.sum(StockLot.qty_remaining), 0))
    .where(StockLot.product_id == Product.id)
    .correlate_except(StockLot)
    .scalar_subquery()
)  # ponytail: subquery ต่อแถวสินค้า พอสำหรับแคตตาล็อกอู่เดียว


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = fk("stock_lots.id")
    qty: Mapped[Decimal] = mapped_column(QTY)
    movement_type: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = fk("users.id")
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        CheckConstraint("movement_type in ('adjust','opening')", name="type"),
        CheckConstraint(
            "(movement_type = 'opening' and qty > 0) or (movement_type = 'adjust' and qty <> 0)", name="direction"
        ),
        CheckConstraint("movement_type <> 'adjust' or reason is not null", name="adjust_reason"),
    )
