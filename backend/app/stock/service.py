from fastapi import HTTPException
from sqlalchemy import select

from app.db import get_or_404, lock_shop
from app.models import Product, StockLot, StockMovement
from app.money import format_qty, round_money


def save_product(db, product_id, data) -> Product:
    """สร้าง (product_id=None) หรือแก้สินค้า: กันรหัสซ้ำ, กันเปลี่ยนหน่วยเมื่อมี Lot แล้ว → commit"""
    product = get_or_404(db, Product, product_id, "สินค้า") if product_id else Product()
    if db.scalar(select(Product.id).where(Product.code == data.code, Product.id != product_id)):
        raise HTTPException(409, "รหัสสินค้านี้มีแล้ว")
    has_lots = product_id and db.scalar(select(StockLot.id).where(StockLot.product_id == product_id).limit(1))
    if has_lots and data.unit != product.unit:
        raise HTTPException(409, "เปลี่ยนหน่วยไม่ได้ เพราะสินค้านี้มีของเข้าคลังแล้ว")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def adjust_down(db, data, user) -> None:
    """ล็อกร้าน → หัก qty_remaining ของ Lot (ห้ามเกินคงเหลือ) + บันทึก movement ติดลบ"""
    lock_shop(db)
    lot = db.scalar(select(StockLot).where(StockLot.id == data.lot_id).with_for_update())
    if lot is None:
        raise HTTPException(404, "ไม่พบ Lot")
    if data.qty > lot.qty_remaining:
        raise HTTPException(409, f"ปรับลดเกินคงเหลือของ Lot (เหลือ {format_qty(lot.qty_remaining)})")
    lot.qty_remaining -= data.qty
    db.add(StockMovement(lot_id=lot.id, qty=-data.qty, movement_type="adjust", reason=data.reason, created_by=user.id))
    db.commit()


def adjust_up(db, data, user) -> StockLot:
    """ล็อกร้าน → สร้าง Lot ใหม่ตามจำนวน/ต้นทุน + บันทึก movement ขาเข้า"""
    lock_shop(db)
    get_or_404(db, Product, data.product_id, "สินค้า")
    lot = StockLot(
        product_id=data.product_id,
        source_type=data.source_type,
        unit_cost=data.unit_cost,
        qty_received=data.qty,
        qty_remaining=data.qty,
        cost_total=round_money(data.qty * data.unit_cost),
        created_by=user.id,
    )
    db.add(lot)
    db.flush()
    db.add(
        StockMovement(
            lot_id=lot.id,
            qty=data.qty,
            reason=data.reason,
            created_by=user.id,
            movement_type="adjust" if data.source_type == "adjustment" else "opening",
        )
    )
    db.commit()
    return lot
