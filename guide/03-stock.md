# เฟส 3 — สินค้า + Lot สต็อก

**จบเฟสนี้:** เพิ่ม/แก้สินค้า · ใส่สต็อกตั้งต้น · เห็นของแต่ละรอบเป็น **Lot** แยกต้นทุน · แจ้งของเสีย/สูญหายพร้อมเหตุผล · ดูสมุดสต็อก · พนักงานกับช่าง**ไม่เห็นต้นทุน**

ตารางใหม่: `products` · `stock_lots` · `stock_movements`

> โค้ดในไฟล์นี้คือของจริงใน repo ตอนจบเฟส 3

## ทำไมต้องมี Lot

ซื้อหัวเทียนรอบแรกชิ้นละ 80 รอบสองชิ้นละ 120 ถ้ารวมเป็น "มี 10 ชิ้น" จะตอบไม่ได้ว่าขายไปหนึ่งชิ้นกำไรเท่าไหร่ → เก็บของแต่ละรอบแยกก้อน = **Lot**

| ตาราง | เก็บอะไร |
|---|---|
| `products` | ป้ายชื่อ: รหัส ชื่อ หน่วย ราคาขาย จุดเตือนขั้นต่ำ |
| `stock_lots` | ก้อนของแต่ละรอบ: รับมากี่ · **เหลือกี่** · ต้นทุนต่อหน่วย |
| `stock_movements` | สมุด: ทุกการเข้า/ออก (+/−) ใครทำ เมื่อไหร่ เพราะอะไร · **เพิ่มได้อย่างเดียว** |

```
stock_lots                    stock_movements
Lot 1  รับ 2  เหลือ 1  ต้นทุน 80   ◄── +2 opening · −1 adjust (แตกหัก)
Lot 2  รับ 3  เหลือ 3  ต้นทุน 120  ◄── +3 adjust
คงเหลือสินค้า = 1 + 3 = 4
```

## ข้อมูลไหลยังไง

**รายการสินค้า**
```
/stock → ProductListPage   useQuery(["products"]) → GET /api/products
  → list_products   ทุกตัว + qty_on_hand (ผลรวม qty_remaining ของทุก Lot คิดสดตอนอ่าน)
  → ค้นหา / แท็บกรอง ทำในเบราว์เซอร์ (matchesFilter + matchesText)
```

**หน้าสินค้า** `/stock/:id` → `ProductDetailPage` ยิง 3 กุญแจใต้กลุ่ม `["products"]`
```
["products", id]               → GET /api/products/{id}
["products", id, "lots"]       → list_product_lots      เรียงเก่าก่อน · ต้นทุนเฉพาะ admin
["products", id, "movements"]  → list_product_movements 500 รายการล่าสุด + ชื่อคนทำ
```

**ของเสีย/สูญหาย** (admin / พนักงาน)
```
ปุ่ม "ของเสีย/สูญหาย" ด้านล่างหน้า → WasteDialog (เลือก Lot + จำนวน + เหตุผล)
  → POST /api/stock/adjust-down → service.adjust_down
       lock_shop → อ่าน Lot แบบ with_for_update → เกินที่เหลือ? → 409 "(เหลือ 2)"
       qty_remaining −= qty → movement ติดลบพร้อมเหตุผล → commit
  ← 204 → invalidate ["products"] → คงเหลือ · Lot · สมุด · รายการ โหลดใหม่หมด
```

**สต็อกตั้งต้น** (admin) — ปุ่ม "สต็อกตั้งต้น" มุมขวาบน → `OpeningDialog` → `POST /api/stock/opening` → `service.add_opening`: lock_shop → Lot ใหม่ → flush → movement ขาเข้า → commit
ของเข้ารอบถัดไปไม่สร้าง Lot เองจากหน้านี้ — มาจากใบรับของ (เฟส 4)
**เพิ่ม / แก้สินค้า** (admin / พนักงาน) — `ProductModal` → `POST` / `PUT /api/products` → `service.save_product`

## กฎหลัก

| กฎ | เพราะ |
|---|---|
| คงเหลือ = ผลรวม "เหลือ" ของทุก Lot ไม่มีคอลัมน์ `stock_qty` | เก็บสองที่วันหนึ่งไม่ตรงกัน |
| ผลรวม movement ของ Lot = ที่เหลือของ Lot · สมุดห้ามแก้ห้ามลบ | สมุดคือหลักฐาน |
| Lot เรียงเก่าก่อน (`created_at`, `id`) | เฟสเบิกของหยิบ Lot แรกก่อน (FIFO) |
| ทุกคำสั่งที่แตะสต็อกเรียก `lock_shop` ก่อน | สองคนกดพร้อมกันแล้วอ่านค่าเก่า = ของหายโดยไม่มีใครรู้ |
| หนึ่งคำสั่ง = หนึ่งทรานแซกชัน | Lot กับ movement เกิดพร้อมกันหรือไม่เกิดเลย |
| ต้นทุนส่งออกจาก server เฉพาะ admin | ซ่อนแค่บนจอ เปิด DevTools ก็เห็น |
| มีของเข้าคลังแล้วเปลี่ยนหน่วยไม่ได้ | Lot เก่าเก็บแค่ตัวเลข เปลี่ยน "ขวด" เป็น "ลิตร" = ข้อมูลเก่าผิดหมด |
| ของเสีย/สูญหาย: พนักงานได้ · สต็อกตั้งต้น: admin เท่านั้น | ของเสียหักจาก Lot เดิมใช้ต้นทุนเดิม · ตั้งต้นคือสร้างของพร้อมต้นทุนที่กรอกเอง ถ้าใครก็ทำได้ กำไรเชื่อไม่ได้ |
| ไม่มีปุ่มปรับเพิ่ม · ของเข้าต้องมีที่มา | ของเข้ามาจากใบรับของ (เฟส 4) หรือสต็อกตั้งต้นเท่านั้น — นับได้เกินให้ admin ลงตั้งต้น |
| ของเสีย/สูญหาย = ต้นทุนที่หายไป | มูลค่า (จำนวน × ต้นทุน Lot) ต้องหักจากกำไรในแดชบอร์ด (เฟส 9) |
| เงินเป็น `Decimal` ตลอด · หน้าจอส่งตัวเลขเป็น string | float ปัดเพี้ยน |

---

# backend

## `app/db.py` — เติม `lock_shop`

```python
SHOP_LOCK = 71001


def lock_shop(db):
    """อู่สาขาเดียว ล็อกตัวเดียวพอ: คำสั่งที่แตะสต็อก จัดซื้อ บิล ทำทีละคำสั่ง"""
    db.execute(text("select pg_advisory_xact_lock(:k)"), {"k": SHOP_LOCK})
```

```
ไม่ล็อก:  คนที่ 1 อ่าน "เหลือ 3" · คนที่ 2 อ่าน "เหลือ 3" · ต่างคนต่างลด 2 → ฐานบอกเหลือ 1 ทั้งที่ออกไป 4
ล็อก:     คนที่ 2 รอ → อ่านใหม่ได้ "เหลือ 1" → ไม่พอ → ปฏิเสธถูกต้อง
```

- ล็อก**ทั้งอู่**ไม่ใช่รายแถว — บางกฎไม่มีแถวให้ล็อก (เลขบิลถัดไป · รับเกินยอดสั่ง) และไม่มีวันลืม · อู่เดียวไม่ช้าจนรู้สึก
- `_xact_` = ปลดเองตอน commit/rollback ไม่มีวันค้าง (`pg_advisory_lock` เฉย ๆ ต้องปลดเอง พังกลางทาง = ทั้งระบบค้าง)

## `app/auth.py` — เติม `staff`

```python
staff = require_role("admin", "employee")
```

## `app/models.py` — สามตาราง

```python
MONEY = Numeric(12, 2)
PRICE = Numeric(14, 4)
QTY = Numeric(12, 3)
RATE = Numeric(5, 2)
```

```python
def fk(target, **kw):
    """คอลัมน์ foreign key ไปยัง target พร้อม index"""
    return mapped_column(ForeignKey(target, **kw), index=True)


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
```

| ชนิด | ทศนิยม | ใช้กับ |
|---|---|---|
| `MONEY` | 2 | ยอดเงิน (`cost_total`) |
| `PRICE` | 4 | ราคา/ต้นทุนต่อหน่วย (มาจากการหาร) |
| `QTY` | 3 | จำนวน (ของขายเป็นลิตรได้) |

- `qty_on_hand` = subquery `sum(qty_remaining)` ติดมากับทุกครั้งที่โหลดสินค้า ในคิวรีเดียว (ไม่ใช่คอลัมน์จริง) · ประกาศหลัง `StockLot` เพราะต้องอ้างถึงมัน
- CHECK ในฐาน: เหลือ ≥ 0 และ ≤ ที่รับ · ต้นทุน ≥ 0 · `opening` ต้องบวก `adjust` ห้ามศูนย์ · `adjust` ต้องมีเหตุผล — โค้ดพลาดก็ไม่มีข้อมูลเสียเข้าฐาน
- `ix_stock_lots_fifo` index ตามลำดับที่ใช้เรียง Lot · `fk()` ใส่ index ให้ทุก foreign key

## `app/money.py`

```python
from decimal import ROUND_HALF_UP, Decimal


def round_money(x) -> Decimal:
    """ปัดเงินเป็นทศนิยม 2 ตำแหน่งแบบปัดครึ่งขึ้น"""
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def format_qty(d) -> str:
    """แปลงจำนวนเป็นข้อความไม่มีศูนย์ท้าย (เช่น 2.500 → "2.5") ใช้ในข้อความ error"""
    return f"{Decimal(d).normalize():f}"
```

- `round_money` ปัดครึ่งขึ้นแบบที่คนไทยคุ้น (float ปัดแบบธนาคาร `2.345` → `2.34`)
- `format_qty` ใช้ในข้อความ error ให้ได้ `2.5` ไม่ใช่ `2.500` หรือ `1E+2`

## `app/schemas.py` — เติม `serialize_for_role`

```python
def serialize_for_role(user, admin_schema, schema, obj):
    """ต้นทุนออกจากเซิร์ฟเวอร์เฉพาะตอนที่คนขอเป็น admin"""
    return (admin_schema if user.role == "admin" else schema).model_validate(obj)
```

`serialize_for_role(user, LotAdminOut, LotOut, lot)` — admin ได้ schema ที่มีต้นทุน คนอื่นได้ schema ที่**ไม่มีช่องต้นทุนเลย**

## `app/stock/schemas.py`

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas import In, Out


class ProductIn(In):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=20)
    sale_price: Decimal = Field(ge=0, decimal_places=4)
    min_stock: Decimal = Field(default=Decimal(0), ge=0, decimal_places=3)
    is_active: bool = True


class ProductOut(ProductIn, Out):
    id: int
    qty_on_hand: Decimal


class LotOut(Out):
    id: int
    product_id: int
    source_type: str
    qty_received: Decimal
    qty_remaining: Decimal
    created_at: datetime


class LotAdminOut(LotOut):
    unit_cost: Decimal
    cost_total: Decimal


class MovementOut(BaseModel):
    id: int
    lot_id: int
    qty: Decimal
    movement_type: str
    reason: str | None
    created_by_name: str
    created_at: datetime


class AdjustDownIn(In):
    lot_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    reason: str = Field(min_length=1)


class OpeningIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, decimal_places=4)
    reason: str = Field(min_length=1)
```

- `LotAdminOut` = `LotOut` + ต้นทุน — ทุกที่ที่มีต้นทุนจะมี schema คู่แบบนี้
- `ProductOut` สืบจาก `ProductIn` ช่องตรงกัน + `id` + `qty_on_hand`
- `reason: str = Field(min_length=1)` + `In` ตัดช่องว่าง → เหตุผลเป็นช่องว่างล้วนได้ 422

## `app/stock/service.py`

```python
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


def adjust_down(db, data, user) -> None:
    """ของเสีย/สูญหาย: ล็อกร้าน → หัก qty_remaining ของ Lot (ห้ามเกินคงเหลือ) + บันทึก movement ติดลบ"""
    lock_shop(db)
    lot = db.scalar(select(StockLot).where(StockLot.id == data.lot_id).with_for_update())
    if lot is None:
        raise HTTPException(404, "ไม่พบ Lot")
    if data.qty > lot.qty_remaining:
        raise HTTPException(409, f"เกินคงเหลือของ Lot (เหลือ {format_qty(lot.qty_remaining)})")
    lot.qty_remaining -= data.qty
    db.add(StockMovement(lot_id=lot.id, qty=-data.qty, movement_type="adjust", reason=data.reason, created_by=user.id))
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
```

**`save_product`** — สร้าง (`product_id=None`) หรือแก้ ใช้ฟังก์ชันเดียว
- `code_owner` = รหัสนี้เป็นของสินค้าตัวไหน · มีเจ้าของและไม่ใช่ตัวเอง → 409
- `unit_changed` + มี Lot แล้ว → 409 · `lock_shop` บรรทัดแรกกัน `add_opening` สร้าง Lot แรกแทรกระหว่างเช็คกับ commit
- `db.refresh(product)` เพื่อได้ `qty_on_hand` ล่าสุด

**`adjust_down`** (ของเสีย/สูญหาย) — ล็อกสองชั้น: `lock_shop` (ทั้งอู่) + `with_for_update` (แถว Lot) · อ่าน `qty_remaining` ใต้ล็อกเท่านั้นถึงเชื่อได้ · ข้อความ error บอกตัวเลขที่เหลือ

**`add_opening`** — `flush()` กลางทางเพื่อได้ `lot.id` ไปใส่ movement (ยังย้อนได้ จนถึง `commit` ครั้งเดียวตอนท้าย) · `cost_total` ปัด 2 ตำแหน่งเพราะเป็นยอดเงิน · Lot เป็น `opening` เสมอ (ค่า `adjustment` ในฐานเหลือไว้ให้ข้อมูลเก่า)

## `app/stock/router.py`

```python
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
```

| คำสั่ง | admin | employee | mechanic |
|---|:---:|:---:|:---:|
| ดูสินค้า · Lot · สมุดสต็อก | ✅ | ✅ | ✅ (ไม่เห็นต้นทุน) |
| เพิ่ม/แก้สินค้า · ของเสีย/สูญหาย | ✅ | ✅ | – |
| สต็อกตั้งต้น | ✅ | – | – |

- `/lots` ใช้ `response_model=None` เพราะ schema ขึ้นกับคนถาม ให้ `serialize_for_role` จัดการ
- `/movements` `join(User)` เอาชื่อคนทำมาในคำขอเดียว · `limit(500)` สินค้าขายดีมีเป็นหมื่นแถว
- `adjust-down` คืน 204 (หน้าจอ invalidate โหลดใหม่เองอยู่แล้ว) · `opening` คืน Lot ใหม่

อย่าลืมเติม router ใน `app/main.py` (ดูเฟส 1)

## เทสต์

```python
from decimal import Decimal

from app.money import format_qty, round_money


def test_round_money_rounds_half_up():
    assert round_money("2.345") == Decimal("2.35")  # float ปัดแบบธนาคารได้ 2.34
    assert round_money(Decimal("1.5") * Decimal("33.333")) == Decimal("50.00")


def test_format_qty_drops_trailing_zeros():
    assert format_qty(Decimal("2.000")) == "2"
    assert format_qty(Decimal("0.500")) == "0.5"
    assert format_qty(Decimal("100")) == "100"  # ไม่กลายเป็น 1E+2
```

```python
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import SessionLocal

PRODUCT = {"code": "OIL-1", "name": "น้ำมันเครื่อง", "unit": "ลิตร", "sale_price": "250", "min_stock": "2"}


def opening(client, headers, pid, qty, cost):
    r = client.post(
        "/api/stock/opening",
        headers=headers["admin"],
        json={"product_id": pid, "qty": qty, "unit_cost": cost, "reason": "ตั้งต้น"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_product_create_list_and_unit_lock(client, headers):
    r = client.post("/api/products", json=PRODUCT, headers=headers["employee"])
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    duplicate = client.post("/api/products", json=PRODUCT, headers=headers["employee"])
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "รหัสสินค้านี้มีแล้ว")  # service จับได้ ไม่ใช่ DB
    assert client.post("/api/products", json={**PRODUCT, "code": "X"}, headers=headers["mechanic"]).status_code == 403
    opening(client, headers, pid, "1.500", "180")
    [p] = client.get("/api/products", headers=headers["mechanic"]).json()
    assert Decimal(p["qty_on_hand"]) == Decimal("1.5")
    one = client.get(f"/api/products/{pid}", headers=headers["mechanic"]).json()
    assert one["code"] == "OIL-1" and Decimal(one["qty_on_hand"]) == Decimal("1.5")
    assert client.get("/api/products/999", headers=headers["mechanic"]).status_code == 404
    unit_change = client.put(f"/api/products/{pid}", json={**PRODUCT, "unit": "ขวด"}, headers=headers["admin"])
    assert unit_change.status_code == 409  # มีของเข้าคลังแล้ว เปลี่ยนหน่วยไม่ได้
    price_change = client.put(
        f"/api/products/{pid}", json={**PRODUCT, "sale_price": "260"}, headers=headers["employee"]
    )
    assert price_change.status_code == 200
    other = client.post("/api/products", json={**PRODUCT, "code": "OIL-2"}, headers=headers["employee"]).json()
    taken = client.put(f"/api/products/{other['id']}", json=PRODUCT, headers=headers["employee"])  # เอารหัสคนอื่น
    assert (taken.status_code, taken.json()["detail"]) == (409, "รหัสสินค้านี้มีแล้ว")


def test_lots_are_separate_and_oldest_first(client, headers, make_product):
    pid = make_product()
    opening(client, headers, pid, "2", "80")
    opening(client, headers, pid, "3", "120")
    lots = client.get(f"/api/products/{pid}/lots", headers=headers["admin"]).json()
    assert [Decimal(lot["unit_cost"]) for lot in lots] == [80, 120]
    [p] = client.get("/api/products", headers=headers["admin"]).json()
    assert Decimal(p["qty_on_hand"]) == 5


def test_adjustments_and_cost_visibility(client, headers, make_product):
    pid = make_product()
    lot_id = opening(client, headers, pid, "2", "100")
    up = {"product_id": pid, "qty": "1", "unit_cost": "1", "reason": "นับเจอ"}
    assert client.post("/api/stock/opening", json=up, headers=headers["employee"]).status_code == 403
    down = {"lot_id": lot_id, "qty": "1", "reason": "เสีย"}
    too_much = client.post("/api/stock/adjust-down", json={**down, "qty": "3"}, headers=headers["employee"])
    assert too_much.status_code == 409
    no_reason = client.post("/api/stock/adjust-down", json={**down, "reason": " "}, headers=headers["employee"])
    assert no_reason.status_code == 422
    assert client.post("/api/stock/adjust-down", json=down, headers=headers["mechanic"]).status_code == 403
    assert client.post("/api/stock/adjust-down", json=down, headers=headers["employee"]).status_code == 204
    [admin_lot] = client.get(f"/api/products/{pid}/lots", headers=headers["admin"]).json()
    [emp_lot] = client.get(f"/api/products/{pid}/lots", headers=headers["employee"]).json()
    assert Decimal(admin_lot["unit_cost"]) == 100 and Decimal(admin_lot["qty_remaining"]) == 1
    assert not {"unit_cost", "cost_total"} & emp_lot.keys()
    moves = client.get(f"/api/products/{pid}/movements", headers=headers["mechanic"]).json()
    assert [m["movement_type"] for m in moves] == ["adjust", "opening"]
    assert moves[0]["created_by_name"] == "employee"


def test_lot_qty_cannot_go_negative(users, make_product):
    with SessionLocal() as s:
        s.add(
            models.StockLot(
                product_id=make_product(),
                source_type="opening",
                unit_cost=1,
                qty_received=1,
                qty_remaining=-1,
                cost_total=1,
                created_by=users["admin"].id,
            )
        )
        with pytest.raises(IntegrityError):
            s.flush()
```

| เทสต์ | ยืนยันว่า |
|---|---|
| `product_create_list_and_unit_lock` | รหัสซ้ำ 409 (ทั้งตอนสร้างและตอนแก้เป็นรหัสคนอื่น) · ช่างสร้างไม่ได้ · ไม่มี 404 · เปลี่ยนหน่วยหลังมีของไม่ได้ |
| `lots_are_separate_and_oldest_first` | Lot แยกต้นทุนจริง และเรียงเก่าก่อน |
| `adjustments_and_cost_visibility` | สิทธิ์ครบทุกบทบาท · **ต้นทุนไม่หลุดถึงพนักงาน** · สมุดบันทึกชื่อคนทำ |
| `lot_qty_cannot_go_negative` | ฐานกันของติดลบเองได้ |

---

# หน้าจอ

## `src/api.js` — เติมตัวจัดรูปแบบ

```js
// จัดรูปตัวเลขไว้โชว์: เงิน (2 ตำแหน่งเสมอ), ต้นทุน/ราคาต่อหน่วย (ทศนิยมเท่าที่มีจริง ≤4), จำนวน (≤3), วันที่ไทยเวลากรุงเทพ
export const formatMoney = (v) =>
  Number(v).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const formatUnitPrice = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 4 });

export const formatQty = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 3 });
```

```js
export const formatDate = (v) =>
  v ? new Date(v).toLocaleDateString("th-TH-u-ca-gregory", { timeZone: "Asia/Bangkok", dateStyle: "medium" }) : "-";
```

- `Number()` ใช้**แสดงผล**เท่านั้น ค่าที่ส่งกลับ backend ยังเป็น string ให้ pydantic แปลงเป็น `Decimal`
- `formatDate` บังคับเวลากรุงเทพ + ปีคริสต์ศักราช (`th-TH-u-ca-gregory`)

## `components/StatusBadge.jsx` — เติมสถานะสินค้า

```jsx
// สถานะสินค้า: เลิกใช้ → inactive, คงเหลือ ≤ ขั้นต่ำ → low, ปกติ → null
export function productStatus(p) {
  if (!p.is_active) return "inactive";
  const hasMinimum = Number(p.min_stock) > 0;
  if (hasMinimum && Number(p.qty_on_hand) <= Number(p.min_stock)) return "low";
  return null;
}
```

- เลิกใช้ → `inactive` · คงเหลือ ≤ ขั้นต่ำ (เมื่อตั้งขั้นต่ำ > 0) → `low` ป้าย "ถึงจุดเตือน" (ถึงจุดที่ควรสั่งของแล้ว ไม่ใช่ "ต่ำกว่า")
- **คำนวณตอนแสดง ไม่เก็บในฐาน** เลยถูกเสมอ

## `components/SearchBar.jsx`

```jsx
import Icon from "./Icon";

// ช่องค้นหา (q/setQ) + แท็บกรอง (filter/setFilter) ถ้าส่ง filters มา
export default function SearchBar({ q, setQ, placeholder, filters, filter, setFilter }) {
  return (
    <div className="space-y-2">
      <label className="relative block">
        <span className="sr-only">{placeholder}</span>
        <Icon
          name="search"
          size={20}
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          className="input pl-10"
          placeholder={placeholder}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>
      {filters && (
        <div role="tablist" aria-label="กรอง" className="tabs -mx-4 px-4 md:mx-0 md:px-0">
          {filters.map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={filter === key}
              onClick={() => setFilter(key)}
              className="tab"
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

ช่องค้น + แท็บกรอง (ไม่ส่ง `filters` = ช่องค้นอย่างเดียว) · `type="search"` ได้ปุ่มล้างข้อความฟรี · state อยู่กับคนเรียก

## `components/DetailLayout.jsx`

```jsx
import { Link } from "react-router-dom";
import Icon from "./Icon";

// ปุ่ม ⋯ เปิดเมนูคำสั่งเพิ่มเติม คลิกแล้วปิดเมนูและเรียก onClick
function MoreMenu({ items }) {
  return (
    <details className="relative">
      <summary
        aria-label="คำสั่งเพิ่มเติม"
        className="btn btn-ghost btn-icon list-none [&::-webkit-details-marker]:hidden"
      >
        <Icon name="more" />
      </summary>
      <ul className="absolute right-0 z-20 mt-1 w-60 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lg">
        {items.map((m) => (
          <li key={m.label}>
            <button
              type="button"
              onClick={(e) => {
                e.currentTarget.closest("details").open = false;
                m.onClick();
              }}
              className="flex min-h-11 w-full items-center px-4 text-left hover:bg-surface"
            >
              {m.label}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}

// โครงหน้ารายละเอียด: ลิงก์กลับ + หัวเรื่อง (+ ปุ่ม action / เมนู ⋯) + เนื้อหา + แถบปุ่มหลัก (มือถือติดขอบล่าง จอใหญ่อยู่ท้ายเนื้อหา)
export default function DetailLayout({ back, backLabel, title, subtitle, badge, action, menu = [], footer, children }) {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <header>
        <Link
          to={back}
          className="-ml-2 inline-flex min-h-11 items-center gap-1 px-2 text-sm text-muted hover:text-ink"
        >
          <Icon name="back" size={18} />
          {backLabel}
        </Link>
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <h1 className="page-title break-words">{title}</h1>
            {subtitle && <div className="text-sm text-muted">{subtitle}</div>}
          </div>
          {badge && <div className="pt-1">{badge}</div>}
          {action}
          {menu.length > 0 && <MoreMenu items={menu} />}
        </div>
      </header>
      {children}
      {footer && (
        <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-white px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:static md:mx-0 md:border-0 md:px-0">
          {footer}
        </div>
      )}
    </div>
  );
}
```

- ลิงก์กลับ · หัวเรื่อง · ป้าย · ปุ่ม `action` · เมนู ⋯ · แถบปุ่มหลัก (มือถือติดขอบล่าง)
- `action` = ปุ่มเดี่ยวที่ใช้บ่อย วางตรง ๆ · `menu` = คำสั่งรอง หลายอัน ซ่อนใน ⋯ (หน้าสินค้าใช้ `action` · หน้า PO เฟส 4 ใช้ `menu`)
- เมนู ⋯ ใช้ `<details>` เปิดปิดเองไม่ต้องมี state · กดรายการแล้วปิด `details` ก่อนเรียกคำสั่ง

## `components/ReasonDialog.jsx`

```jsx
import Modal from "./Modal";

// popup ที่มีช่อง "เหตุผล" ท้ายฟอร์ม: ฟอร์ม (register/onSubmit) และ mutation มาจากคนเรียก
// render เมื่อจะเปิด เลิก render = ปิด ค่าในฟอร์มล้างเอง
export default function ReasonDialog({ title, onClose, onSubmit, register, mutation, children }) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      onSubmit={onSubmit}
      footer={
        <>
          {mutation.error && (
            <p role="alert" className="field-error mb-2">
              {mutation.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              ยกเลิก
            </button>
            <button className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? "กำลังบันทึก…" : "ยืนยัน"}
            </button>
          </div>
        </>
      }
    >
      {children}
      <label className="block">
        <span className="label">เหตุผล</span>
        <textarea className="input" rows={3} required {...register("reason")} />
      </label>
    </Modal>
  );
}
```

ป๊อปอัพที่ท้ายฟอร์มมีช่อง "เหตุผล" บังคับกรอกเสมอ — ฟอร์ม (`register` / `onSubmit`) กับ `mutation` มาจากคนเรียก ใช้ได้กับทุกคำสั่งที่ต้องมีเหตุผล

## `components/ProductModal.jsx` — ฟอร์มสินค้า (ใช้สองที่)

```jsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, plainNumber } from "../api";
import Field from "./Field";
import Modal from "./Modal";

// ฟอร์มสินค้า: มี id → PUT /products/{id}, ไม่มี → POST /products, สำเร็จแล้วให้ข้อมูลสินค้าทุกหน้าโหลดใหม่
export default function ProductModal({ initial, onClose, onSaved }) {
  const isEdit = !!initial.id;
  const queryClient = useQueryClient();
  const { register, handleSubmit } = useForm({
    defaultValues: {
      ...initial,
      sale_price: plainNumber(initial.sale_price),
      min_stock: plainNumber(initial.min_stock),
    },
  });
  const save = useMutation({
    mutationFn: (form) =>
      api(isEdit ? `/products/${initial.id}` : "/products", { method: isEdit ? "PUT" : "POST", body: form }),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onSaved(saved);
    },
  });

  return (
    <Modal
      title={isEdit ? `แก้ไข ${initial.code}` : "เพิ่มสินค้า"}
      onClose={onClose}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {save.error && (
            <p role="alert" className="field-error mb-2">
              {save.error.message}
            </p>
          )}
          <button className="btn btn-primary w-full" disabled={save.isPending}>
            {save.isPending ? "กำลังบันทึก…" : "บันทึกสินค้า"}
          </button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="รหัสสินค้า" required autoCapitalize="characters" {...register("code")} />
        <Field label="หน่วย" required placeholder="ชิ้น, ขวด" {...register("unit")} />
      </div>
      <Field label="ชื่อสินค้า" required {...register("name")} />
      <Field
        label="ราคาขาย (รวม VAT)"
        type="number"
        inputMode="decimal"
        step="0.01"
        min="0"
        required
        {...register("sale_price")}
      />
      <Field
        label="จุดเตือนขั้นต่ำ"
        hint="0 = ไม่เตือน"
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0"
        required
        {...register("min_stock")}
      />
      <label className="flex min-h-11 cursor-pointer items-center gap-3">
        <input type="checkbox" role="switch" className="size-5 accent-accent" {...register("is_active")} />
        ใช้งานอยู่
      </label>
    </Modal>
  );
}
```

- มี `id` → PUT · ไม่มี → POST (`isEdit` ใช้สามที่: URL · method · หัวป๊อปอัพ)
- บันทึกแล้ว invalidate `["products"]` เองเสมอ · หลังจากนั้นทำอะไรต่อให้คนเรียกบอกผ่าน `onSaved`
- `plainNumber` ก่อนใส่ฟอร์ม (`"150.0000"` → `"150"`) · ส่ง `form` ทั้งก้อน ช่องเกิน (`id` `qty_on_hand`) pydantic ทิ้งให้เอง
- "จุดเตือนขั้นต่ำ" ก็ `required` ไม่งั้นลบจนว่างแล้วได้ error กว้าง ๆ

## `pages/ProductFormPage.jsx` — route `/stock/new`

```jsx
import { useNavigate, useOutletContext } from "react-router-dom";
import ProductModal from "../components/ProductModal";

const EMPTY_PRODUCT = { code: "", name: "", unit: "", sale_price: "", min_stock: "0", is_active: true };

// /stock/new: popup เพิ่มสินค้าบนหน้ารายการ บันทึกแล้วไปหน้าสินค้าตัวใหม่
export default function ProductFormPage() {
  const { close } = useOutletContext();
  const navigate = useNavigate();
  return <ProductModal initial={EMPTY_PRODUCT} onClose={close} onSaved={(p) => navigate(`/stock/${p.id}`)} />;
}
```

แค่ห่อ `ProductModal` · บันทึกแล้วไปหน้าสินค้าตัวใหม่ เพราะงานถัดไปเกือบทุกครั้งคือใส่สต็อกตั้งต้น

## `pages/ProductListPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { formatMoney, formatQty } from "../api";
import { useAuth } from "../auth";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import StatusBadge, { productStatus } from "../components/StatusBadge";
import SearchBar from "../components/SearchBar";

const FILTERS = [
  ["active", "ใช้งานอยู่"],
  ["low", "ถึงจุดเตือน"],
  ["inactive", "เลิกใช้"],
];

// หน้า /stock: GET /products แล้วค้น/กรองฝั่ง client, route ลูก new เปิด popup เพิ่มสินค้า
export default function ProductListPage() {
  const { user } = useAuth();
  const { data, error } = useQuery({ queryKey: ["products"] });
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("active");
  const text = q.trim().toLowerCase();
  // แท็บ "ใช้งานอยู่" ดูที่ is_active · แท็บอื่นดูที่ป้ายสถานะ
  const matchesFilter = (p) => (filter === "active" ? p.is_active : productStatus(p) === filter);
  const matchesText = (p) => !text || p.code.toLowerCase().includes(text) || p.name.toLowerCase().includes(text);
  const items = data?.filter((p) => matchesFilter(p) && matchesText(p));

  return (
    <ListLayout
      title="สต็อก"
      basePath="/stock"
      action={user.role !== "mechanic" && { label: "เพิ่มสินค้า", to: "/stock/new" }}
      toolbar={
        <SearchBar
          q={q}
          setQ={setQ}
          placeholder="ค้นรหัสหรือชื่อสินค้า"
          filters={FILTERS}
          filter={filter}
          setFilter={setFilter}
        />
      }
    >
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      <DataTable
        items={items}
        to={(p) => `/stock/${p.id}`}
        empty="ไม่พบสินค้า"
        card={(p) => (
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-semibold">{p.name}</div>
              <div className="text-sm text-muted">
                {p.code} · ขาย {formatMoney(p.sale_price)}
              </div>
              <div className="mt-2">
                <StatusBadge status={productStatus(p)} />
              </div>
            </div>
            <div className="text-right">
              <div className="num text-2xl font-bold">{formatQty(p.qty_on_hand)}</div>
              <div className="text-sm text-muted">{p.unit}</div>
            </div>
          </div>
        )}
        columns={[
          { label: "รหัส", render: (p) => p.code },
          { label: "ชื่อ", render: (p) => p.name },
          { label: "ราคาขาย", align: "right", render: (p) => formatMoney(p.sale_price) },
          { label: "คงเหลือ", align: "right", render: (p) => `${formatQty(p.qty_on_hand)} ${p.unit}` },
          { label: "สถานะ", render: (p) => <StatusBadge status={productStatus(p)} /> },
        ]}
      />
    </ListLayout>
  );
}
```

- ค้นหาและกรอง**ในเบราว์เซอร์** — สินค้าอู่มีไม่กี่ร้อยตัว โหลดทีเดียวแล้วกรองได้ผลทุกตัวอักษร
- `matchesFilter` / `matchesText` ตั้งชื่อเงื่อนไขก่อนใช้ · `data?.filter` ยังโหลดไม่เสร็จได้ `undefined` → `DataTable` โชว์ "กำลังโหลด…"
- ช่างไม่มีปุ่มเพิ่ม (`action` เป็น `false`)

## `pages/ProductDetailPage.jsx`

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { api, formatMoney, formatQty, formatDate, formatUnitPrice } from "../api";
import { useAuth } from "../auth";
import Field from "../components/Field";
import Icon from "../components/Icon";
import DetailLayout from "../components/DetailLayout";
import ReasonDialog from "../components/ReasonDialog";
import ProductModal from "../components/ProductModal";
import StatusBadge, { productStatus } from "../components/StatusBadge";

const SOURCE_LABEL = { opening: "สต็อกตั้งต้น" };
const MOVE_LABEL = { adjust: "ของเสีย/สูญหาย", opening: "ตั้งต้น" };
const TABS = [
  ["lots", "Lot"],
  ["moves", "สมุดสต็อก"],
];

// หน้าสินค้า /stock/:id: ดึงสินค้า + Lot + สมุดสต็อก, เปิด popup แก้สินค้า / ของเสีย/สูญหาย (ปุ่มล่าง) / สต็อกตั้งต้น (ปุ่มบน)
export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const isStaff = user.role !== "mechanic";
  const product = useQuery({ queryKey: ["products", id] });
  const lots = useQuery({ queryKey: ["products", id, "lots"] });
  const moves = useQuery({ queryKey: ["products", id, "movements"] });
  const [tab, setTab] = useState("lots");
  const [dialog, setDialog] = useState(null); // ป๊อปอัพที่เปิดอยู่: null หรือ { type: "edit" | "opening" | "waste" }
  const closeDialog = () => setDialog(null);
  const stockedLots = lots.data?.filter((l) => Number(l.qty_remaining) > 0) ?? []; // Lot ที่ยังมีของให้แจ้งเสีย

  const p = product.data;
  if (!p) return <DetailLayout back="/stock" backLabel="สต็อก" title={product.error?.message || "กำลังโหลด…"} />;

  return (
    <DetailLayout
      back="/stock"
      backLabel="สต็อก"
      title={p.name}
      subtitle={p.code}
      badge={<StatusBadge status={productStatus(p)} />}
      action={
        isAdmin && (
          <button type="button" className="btn btn-secondary" onClick={() => setDialog({ type: "opening" })}>
            <Icon name="plus" size={20} />
            สต็อกตั้งต้น
          </button>
        )
      }
      footer={
        isStaff && (
          <div className="flex gap-2">
            <button
              type="button"
              className="btn btn-secondary flex-1"
              disabled={!stockedLots.length}
              onClick={() => setDialog({ type: "waste" })}
            >
              <Icon name="minus" size={20} />
              ของเสีย/สูญหาย
            </button>
            <button type="button" className="btn btn-primary flex-1" onClick={() => setDialog({ type: "edit" })}>
              <Icon name="edit" size={20} />
              แก้สินค้า
            </button>
          </div>
        )
      }
    >
      <div>
        <div className="text-sm text-muted">คงเหลือ</div>
        <div className="num text-4xl font-bold">
          {formatQty(p.qty_on_hand)} <span className="text-lg font-medium text-muted">{p.unit}</span>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <Fact label="ราคาขาย" value={formatMoney(p.sale_price)} />
        <Fact label="ขั้นต่ำ" value={Number(p.min_stock) > 0 ? formatQty(p.min_stock) : "-"} />
      </dl>

      <div role="tablist" aria-label="มุมมอง" className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className="tab"
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "lots" ? <LotList lots={lots} showCost={isAdmin} /> : <MovementList moves={moves} />}

      {dialog?.type === "edit" && <ProductModal initial={p} onClose={closeDialog} onSaved={closeDialog} />}
      {dialog?.type === "opening" && <OpeningDialog productId={p.id} onClose={closeDialog} />}
      {dialog?.type === "waste" && <WasteDialog lots={stockedLots} onClose={closeDialog} />}
    </DetailLayout>
  );
}

// กล่องข้อมูลสั้น หัวข้อ + ค่า
function Fact({ label, value }) {
  return (
    <div className="rounded-lg bg-surface p-2">
      <dt className="text-muted">{label}</dt>
      <dd className="num font-semibold">{value}</dd>
    </div>
  );
}

// รายการ Lot เก่า→ใหม่: ต้นทุนโชว์เฉพาะ admin, Lot ที่ของหมดเป็นสีจาง
function LotList({ lots, showCost }) {
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {lots.error && (
        <li role="alert" className="field-error p-4">
          {lots.error.message}
        </li>
      )}
      {lots.data?.length === 0 && <li className="p-4 text-muted">ยังไม่มีของเข้าคลัง</li>}
      {lots.data?.map((lot) => {
        const hasStock = Number(lot.qty_remaining) > 0;
        return (
          <li key={lot.id} className={`space-y-1 px-4 py-3 ${hasStock ? "" : "text-muted"}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">
                Lot #{lot.id} · {SOURCE_LABEL[lot.source_type]}
              </span>
              <span className="text-sm">{formatDate(lot.created_at)}</span>
            </div>
            <div className="num text-sm">
              รับเข้า {formatQty(lot.qty_received)} · <b>เหลือ {formatQty(lot.qty_remaining)}</b>
            </div>
            {showCost && <div className="num text-sm">ต้นทุน/หน่วย {formatUnitPrice(lot.unit_cost)}</div>}
          </li>
        );
      })}
    </ul>
  );
}

// สมุดสต็อก: รายการเข้า/ออกล่าสุดก่อน ตัวเลขติดลบเป็นสีแดง
function MovementList({ moves }) {
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {moves.error && (
        <li role="alert" className="field-error p-4">
          {moves.error.message}
        </li>
      )}
      {moves.data?.length === 0 && <li className="p-4 text-muted">ยังไม่มีรายการ</li>}
      {moves.data?.map((m) => {
        const qty = Number(m.qty);
        return (
          <li key={m.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
            <div className="min-w-0 text-sm">
              <div className="font-semibold">
                {MOVE_LABEL[m.movement_type]} · Lot #{m.lot_id}
              </div>
              <div className="text-muted">
                {formatDate(m.created_at)} · {m.created_by_name}
              </div>
              {m.reason && <div className="text-muted">{m.reason}</div>}
            </div>
            <span className={`num font-bold ${qty < 0 ? "text-danger" : ""}`}>
              {qty > 0 ? "+" : ""}
              {formatQty(m.qty)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// POST คำสั่งปรับสต็อก สำเร็จแล้วให้ข้อมูลสินค้าทุกหน้าโหลดใหม่ (คงเหลือ, Lot, สมุดสต็อก, รายการสินค้า) แล้วปิด popup
function useAdjustStock(path, onDone) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => api(path, { method: "POST", body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onDone();
    },
  });
}

// popup ของเสีย/สูญหาย (เลือก Lot ค่าเริ่ม Lot เก่าสุด): POST /stock/adjust-down { lot_id, qty, reason }
function WasteDialog({ lots, onClose }) {
  const { register, handleSubmit, watch } = useForm({
    defaultValues: { lot_id: String(lots[0].id), qty: "", reason: "" },
  });
  const waste = useAdjustStock("/stock/adjust-down", onClose);
  const lot = lots.find((l) => String(l.id) === watch("lot_id"));
  return (
    <ReasonDialog
      title="ของเสีย/สูญหาย"
      onClose={onClose}
      register={register}
      mutation={waste}
      onSubmit={handleSubmit((form) => waste.mutate({ ...form, lot_id: Number(form.lot_id) }))}
    >
      <label className="block">
        <span className="label">Lot</span>
        <select className="input" {...register("lot_id")}>
          {lots.map((l) => (
            <option key={l.id} value={l.id}>
              Lot #{l.id} · {formatDate(l.created_at)} · เหลือ {formatQty(l.qty_remaining)}
            </option>
          ))}
        </select>
      </label>
      <Field
        label={`จำนวน (เหลือ ${formatQty(lot.qty_remaining)})`}
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0.001"
        max={lot.qty_remaining}
        required
        {...register("qty")}
      />
    </ReasonDialog>
  );
}

// popup สต็อกตั้งต้น (admin): POST /stock/opening สร้าง Lot ใหม่ (ของเข้าปกติมาจากใบรับของ)
function OpeningDialog({ productId, onClose }) {
  const { register, handleSubmit } = useForm({ defaultValues: { qty: "", unit_cost: "", reason: "" } });
  const opening = useAdjustStock("/stock/opening", onClose);
  return (
    <ReasonDialog
      title="สต็อกตั้งต้น"
      onClose={onClose}
      register={register}
      mutation={opening}
      onSubmit={handleSubmit((form) => opening.mutate({ ...form, product_id: productId }))}
    >
      <Field label="จำนวน" type="number" inputMode="decimal" step="0.001" min="0.001" required {...register("qty")} />
      <Field
        label="ต้นทุนต่อหน่วย (ก่อน VAT)"
        type="number"
        inputMode="decimal"
        step="0.0001"
        min="0"
        required
        {...register("unit_cost")}
      />
    </ReasonDialog>
  );
}
```

- ยิง 3 กุญแจ ทุกตัวขึ้นต้น `"products"` → invalidate ครั้งเดียวโหลดใหม่หมด
- `dialog` = ป๊อปอัพที่เปิดอยู่ `{ type: "edit" | "opening" | "waste" }` · เปิดได้ทีละอัน · ปิด = `setDialog(null)`
- ปุ่ม "ของเสีย/สูญหาย" อยู่ด้านล่างคู่กับแก้สินค้า · `stockedLots` (Lot ที่ยังมีของ) เป็นตัวเลือกใน dropdown ค่าเริ่ม Lot เก่าสุด · ไม่มีของเลย → ปุ่มจาง
- ป๊อปอัพปรับสต็อกใช้ **state** ไม่ใช้ route (เป็นคำสั่งย่อยในหน้า ไม่ต้องมี URL) ต่างจากฟอร์มเพิ่ม/แก้
- `useAdjustStock` ตัวเดียวใช้ทั้งของเสียและตั้งต้น · Lot ที่หมดแล้วสีจาง · ตัวเลขติดลบในสมุดสีแดง

## เมนูและ route

เมนู "สต็อก" อยู่ใน `MENU` ของ `AppLayout.jsx` · route ใน `main.jsx` (ทั้งสองไฟล์ดูเฟส 1):

```jsx
<Route index element={<Navigate to="/stock" replace />} />
<Route path="stock" element={<ProductListPage />}>
  <Route
    path="new"
    element={
      <Guard roles={STAFF}>
        <ProductFormPage />
      </Guard>
    }
  />
</Route>
<Route path="stock/:id" element={<ProductDetailPage />} />
```

`/stock/new` เป็นลูกของรายการ (ป๊อปอัพทับรายการ) ครอบ `Guard roles={STAFF}` · `/stock/:id` เป็นพี่น้อง (หน้าเต็ม)

---

## เช็คว่าเสร็จ

- pytest เขียว · `npm run build` ผ่าน
- เพิ่มสินค้า → ไปหน้าสินค้าเอง → ใส่สต็อกตั้งต้นสองรอบต้นทุนต่างกัน → เห็นสอง Lot เรียงเก่าก่อน
- ของเสีย/สูญหายเกินที่เหลือ → ขึ้นข้อความพร้อมตัวเลข · ไม่กรอกเหตุผล → กดไม่ผ่าน
- มีหลาย Lot → แจ้งของเสียจาก Lot ที่เลือก คงเหลือลดถูก · สมุดขึ้น "ของเสีย/สูญหาย" ตัวแดง
- ตั้งขั้นต่ำสูงกว่าของที่มี → ป้าย "ถึงจุดเตือน" · แท็บ "ถึงจุดเตือน" เจอ · ตั้งกลับเป็น 0 → ป้ายหาย
- มีของแล้วลองเปลี่ยนหน่วย → 409
- ล็อกอินเป็นพนักงาน → ไม่เห็นต้นทุน · DevTools → Network → `/lots` ต้องไม่มี `unit_cost`
