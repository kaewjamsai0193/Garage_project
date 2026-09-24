from fastapi import HTTPException
from sqlalchemy import select

from app.db import get_or_404, lock_shop
from app.models import Product, StockLot, StockMovement
from app.money import format_qty, round_money


def save_product(db, product_id, data) -> Product:
    """ล็อกร้าน → สร้าง (product_id=None) หรือแก้สินค้า: กันรหัสซ้ำ, กันเปลี่ยนหน่วยเมื่อมี Lot แล้ว → commit"""
    lock_shop(db)  # กัน add_opening สร้าง Lot แรกแทรกระหว่างเช็คหน่วยกับ commit
    product = get_or_404(db, Product, product_id, "สินค้า") if product_id else Product()
    code_owner = db.scalar(select(Product.id).where(Product.code == data.code))  # รหัสนี้เป็นของสินค้าตัวไหน
    if code_owner is not None and code_owner != product_id:
        raise HTTPException(409, "รหัสสินค้านี้มีแล้ว")
    unit_changed = product_id is not None and data.unit != product.unit
    if unit_changed and db.scalar(select(StockLot.id).where(StockLot.product_id == product_id).limit(1)):
        raise HTTPException(409, "เปลี่ยนหน่วยไม่ได้ เพราะสินค้านี้มีของเข้าคลังแล้ว")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def adjust_lot(db, data, user, sign) -> None:
    """ล็อกร้าน → ปรับ qty_remaining ของ Lot (sign=-1 ลด ห้ามต่ำกว่า 0, sign=1 เพิ่ม ห้ามเกินที่รับเข้า) + บันทึก movement"""
    lock_shop(db)
    lot = db.scalar(select(StockLot).where(StockLot.id == data.lot_id).with_for_update())
    if lot is None:
        raise HTTPException(404, "ไม่พบ Lot")
    if sign < 0 and data.qty > lot.qty_remaining:
        raise HTTPException(409, f"ปรับลดเกินคงเหลือของ Lot (เหลือ {format_qty(lot.qty_remaining)})")
    room = lot.qty_received - lot.qty_remaining
    if sign > 0 and data.qty > room:
        raise HTTPException(409, f"ปรับเพิ่มเกินจำนวนรับเข้าของ Lot (เพิ่มได้อีก {format_qty(room)})")
    lot.qty_remaining += sign * data.qty
    db.add(
        StockMovement(
            lot_id=lot.id, qty=sign * data.qty, movement_type="adjust", reason=data.reason, created_by=user.id
        )
    )
    db.commit()


def add_opening(db, data, user) -> StockLot:
    """ล็อกร้าน → สร้าง Lot สต็อกตั้งต้นตามจำนวน/ต้นทุน + บันทึก movement ขาเข้า (ของเข้าปกติจะมาจากใบรับของ)"""
    lock_shop(db)
    get_or_404(db, Product, data.product_id, "สินค้า")
    lot = StockLot(
        product_id=data.product_id,
        source_type="opening",
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
            movement_type="opening",
        )
    )
    db.commit()
    return lot
