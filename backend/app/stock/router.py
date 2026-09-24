from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from app.auth import admin, current_user, staff
from app.db import get_db, get_or_404
from app.models import Product, StockLot, StockMovement, User
from app.schemas import serialize_for_role
from app.stock import service
from app.stock.schemas import AdjustDownIn, LotAdminOut, LotOut, MovementOut, OpeningIn, ProductIn, ProductOut

router = APIRouter(prefix="/api", tags=["stock"])


@router.get("/products", response_model=list[ProductOut])
def list_products(db=Depends(get_db), _=Depends(current_user)):
    """GET /api/products: สินค้าทุกตัวเรียงตามรหัส พร้อม qty_on_hand (หน้าจอค้น/กรองเอง)"""
    return db.scalars(select(Product).order_by(Product.code)).all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db=Depends(get_db), _=Depends(current_user)):
    """GET /api/products/{id}: สินค้าตัวเดียวพร้อม qty_on_hand, ไม่เจอ 404"""
    return get_or_404(db, Product, product_id, "สินค้า")


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductIn, db=Depends(get_db), _=Depends(staff)):
    """POST /api/products: admin/พนักงาน สร้างสินค้าใหม่ผ่าน service.save_product"""
    return service.save_product(db, None, data)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductIn, db=Depends(get_db), _=Depends(staff)):
    """PUT /api/products/{id}: admin/พนักงาน แก้สินค้าผ่าน service.save_product"""
    return service.save_product(db, product_id, data)


@router.get("/products/{product_id}/lots", response_model=None)
def list_product_lots(product_id: int, db=Depends(get_db), user=Depends(current_user)):
    """GET /api/products/{id}/lots: Lot ของสินค้าเรียงเก่า→ใหม่ (FIFO), ต้นทุนส่งเฉพาะ admin"""
    lots = db.scalars(
        select(StockLot).where(StockLot.product_id == product_id).order_by(StockLot.created_at, StockLot.id)
    ).all()
    return [serialize_for_role(user, LotAdminOut, LotOut, lot) for lot in lots]


@router.get("/products/{product_id}/movements", response_model=list[MovementOut])
def list_product_movements(product_id: int, db=Depends(get_db), _=Depends(current_user)):
    """GET /api/products/{id}/movements: สมุดสต็อก 500 รายการล่าสุด พร้อมชื่อคนทำ"""
    rows = db.execute(
        select(StockMovement, User.full_name)
        .join(StockLot, StockLot.id == StockMovement.lot_id)
        .join(User, User.id == StockMovement.created_by)
        .where(StockLot.product_id == product_id)
        .order_by(StockMovement.id.desc())
        .limit(500)
    ).all()
    return [
        MovementOut(
            id=m.id,
            lot_id=m.lot_id,
            qty=m.qty,
            movement_type=m.movement_type,
            reason=m.reason,
            created_by_name=name,
            created_at=m.created_at,
        )
        for m, name in rows
    ]


@router.post("/stock/adjust-down", status_code=204)
def adjust_down(data: AdjustDownIn, db=Depends(get_db), user=Depends(staff)):
    """POST /api/stock/adjust-down: admin/พนักงาน แจ้งของเสีย/สูญหาย หักจาก Lot พร้อมเหตุผล → 204"""
    service.adjust_down(db, data, user)
    return Response(status_code=204)


@router.post("/stock/opening", response_model=LotAdminOut, status_code=201)
def add_opening(data: OpeningIn, db=Depends(get_db), user=Depends(admin)):
    """POST /api/stock/opening: admin ลงสต็อกตั้งต้นเป็น Lot ใหม่ → คืน Lot"""
    return service.add_opening(db, data, user)
