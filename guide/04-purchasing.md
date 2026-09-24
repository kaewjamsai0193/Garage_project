# เฟส 4 — ใบสั่งซื้อ + รับของเข้าคลัง

**จบเฟสนี้:** ออกใบสั่งซื้อ (PO) แล้วพิมพ์ส่งร้าน · รับของทยอยตาม PO · ซื้อด่วนไม่มี PO ก็บันทึกได้ · แยก VAT ซื้อออกจากต้นทุน · ของที่รับเป็น **Lot ใหม่พร้อมต้นทุนจริง** · PO ปิดเองเมื่อรับครบ

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 3 · `data_model.md` หัวข้อ 4 · กรณีตรวจรับข้อ 3, 13, 14, 15
**ยังไม่ทำ** รายงานภาษีซื้อ (เฟส 9 อ่านจาก `vat_amount` ที่เฟสนี้เก็บ)

> เฟสนี้**ยังไม่ได้ลงมือทำ** — โค้ดหน้าจอผ่าน `npm run build` แล้วแต่ยังไม่ได้กดกับ backend จริง เจอจุดพังให้แก้ในคู่มือด้วย

## ข้อมูลไหลยังไง

```
① ออก PO   PurchaseOrderFormPage → POST /api/purchase-orders → purchasing/service.py:create_po
           สต็อกยังไม่ขยับ · พิมพ์ส่งร้านที่ /print/po/:id
② รับของ   GoodsReceiptFormPage → POST /api/goods-receipts → create_goods_receipt
           lock_shop → ตรวจ PO / ชื่อร้าน / ใบกำกับ → สร้างใบรับของ
           → สินค้าละ 1 Lot ใหม่ (ต้นทุน = ยอดจ่าย − VAT) + movement "receive"
           → รับครบทุกรายการแล้ว → PO ปิดเอง
③ หน้าจอ   invalidate ["goods-receipts"] ["purchase-orders"] ["products"] → ทุกหน้าที่เกี่ยวอัปเดตเอง
```

## กฎหลัก

| กฎ | เพราะ |
|---|---|
| ไม่มีทะเบียนร้าน กรอกชื่อร้านสดบนเอกสารทุกครั้ง | อู่ซื้อจากไม่กี่เจ้า ตารางผู้ขาย + หน้าจัดการไม่คุ้ม |
| ราคาบน PO = ราคาคาด · ต้นทุนจริงมาจากใบรับของ | บิลจริงอาจไม่เท่าที่คาด ระบบยึดใบรับของ |
| รับของ = Lot ใหม่ สินค้าละ 1 Lot ต่อใบ | ต้นทุนจริงของแต่ละรอบแยกกัน (ต่อจากแนวคิด Lot เฟส 3) |
| ยอดรับแล้วคำนวณจาก Lot ไม่เก็บบน PO | เก็บสองที่วันหนึ่งไม่ตรงกัน (เหมือน `qty_on_hand`) |
| ใบรับของบันทึกแล้วแก้ไม่ได้ | รับเกินให้แจ้งของเสีย/สูญหาย · รับขาดให้รับเพิ่มอีกใบ พร้อมเหตุผล เหลือร่องรอย |
| ช่างรับของได้ (ซื้อด่วน) แต่ออก PO ไม่ได้ · เห็นเฉพาะใบที่ตัวเองบันทึก | ช่างขับไปซื้อของข้างอู่จริง |
| ราคาคาดบน PO: ช่างไม่เห็น · ต้นทุน/VAT บนใบรับของ: admin เท่านั้น | ราคาคาดแค่ประมาณการ ต้นทุนจริงคือข้อมูลกำไร |
| มีใบกำกับ → ถอด VAT ออกจากต้นทุน (ค่าเริ่ม 7/107 แก้ได้) · ไม่มี → ต้นทุน = ยอดจ่าย | VAT ซื้อขอคืนได้ ไม่ใช่ต้นทุน |
| ใบกำกับหนึ่งใบบันทึกซ้ำไม่ได้ (เลขผู้เสียภาษี + เลขที่) | partial unique index + ทำรูปแบบให้เหมือนกันก่อนเก็บ (`digits` · `.upper()`) |
| ทุกคำสั่งจัดซื้อเรียก `lock_shop` | สองคนกดรับพร้อมกันต้องไม่เกินยอดสั่ง (เทสต์ยิงสองเธรดพิสูจน์) |
| เลขเอกสาร `PO-00007` คำนวณจาก id | ข้ามเลขได้ไม่เป็นไร (ต่างจากเลขบิลขายเฟส 6 ที่ห้ามข้าม) |

**สถานะ PO** — ในฐานมีแค่ `open` `closed` `cancelled`

```
เปิดอยู่ ──รับครบทุกรายการ──────────────────────────────> ปิดแล้ว (ระบบปิดเอง)
   │   └─ปิดก่อนครบ (ต้องมีเหตุผล · เฉพาะใบที่เคยรับของแล้ว)──> ปิดแล้ว
   └─ยกเลิก (เฉพาะใบที่ยังไม่เคยรับของเลย · ต้องมีเหตุผล)────> ยกเลิก
```

"รอของ" / "รับบางส่วน" บนจอ**คำนวณสด** (`receive_state`) จากยอดที่รับแล้ว ไม่ได้เก็บ

---

# backend

## 1. `app/models.py` — ตารางใหม่ 3 ตัว + แก้ Lot และสมุดสต็อก

**import**

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func, select, text,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship
```

**ตารางใหม่** วางก่อน `class StockLot`

```python
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(200))
    supplier_phone: Mapped[str | None] = mapped_column(String(20))
    supplier_tax_id: Mapped[str | None] = mapped_column(String(20))
    supplier_address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10))
    close_reason: Mapped[str | None] = mapped_column(Text)
    closed_by: Mapped[int | None] = fk("users.id")
    closed_at: Mapped[datetime | None] = mapped_column(TS)
    created_by: Mapped[int] = fk("users.id")
    created_at: Mapped[datetime] = created()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(order_by="PurchaseOrderItem.id")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    __table_args__ = (
        CheckConstraint("status in ('open','closed','cancelled')", name="status"),
        CheckConstraint("(closed_at is null) = (status = 'open')", name="closed_at"),
        CheckConstraint("(closed_by is null) = (closed_at is null)", name="closed_by"),
        CheckConstraint("status <> 'cancelled' or close_reason is not null", name="cancel_reason"),
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = fk("purchase_orders.id")
    product_id: Mapped[int] = fk("products.id")
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_price: Mapped[Decimal | None] = mapped_column(PRICE)
    product: Mapped["Product"] = relationship()
    __table_args__ = (
        UniqueConstraint("po_id", "product_id"),
        CheckConstraint("qty > 0", name="qty"),
        CheckConstraint("unit_price is null or unit_price >= 0", name="unit_price"),
    )


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int | None] = fk("purchase_orders.id")
    supplier_name: Mapped[str] = mapped_column(String(200))
    supplier_tax_id: Mapped[str | None] = mapped_column(String(20))
    supplier_invoice_no: Mapped[str | None] = mapped_column(String(50))
    supplier_invoice_date: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int] = fk("users.id")
    created_at: Mapped[datetime] = created()
    lots: Mapped[list["StockLot"]] = relationship(order_by="StockLot.id")
    creator: Mapped["User"] = relationship()
    __table_args__ = (
        CheckConstraint("(supplier_invoice_no is null) = (supplier_invoice_date is null)", name="invoice_date"),
        CheckConstraint("supplier_invoice_no is null or supplier_tax_id is not null", name="invoice_tax_id"),
        Index("goods_receipts_supplier_invoice", "supplier_tax_id", "supplier_invoice_no",
              unique=True, postgresql_where=text("supplier_invoice_no is not null")),
    )
```

- `CHECK (a) = (b)` อ่านว่า "สองข้างต้องจริงหรือเท็จพร้อมกัน" เช่น `open` ⇔ ไม่มี `closed_at` — สถานะขัดกันเองเกิดไม่ได้ที่ระดับฐาน
- `cancel_reason` บังคับเหตุผลเฉพาะ `cancelled` (PO ที่ระบบปิดเองเพราะรับครบไม่ต้องมีเหตุผล)
- `UniqueConstraint("po_id", "product_id")` สินค้าหนึ่งตัวอยู่แถวเดียวในใบ ยอดค้างรับจะได้ไม่ต้องรวมหลายแถว
- **partial unique index** บังคับ "ใบกำกับห้ามซ้ำ" เฉพาะแถวที่มีเลขใบกำกับ — unique ธรรมดาจะทำให้ใบไม่มีใบกำกับ `(null, null)` บันทึกได้ใบเดียว
- `creator: relationship(foreign_keys=[created_by])` ต้องระบุเพราะ PO มี FK ไป users สองตัว (`created_by` `closed_by`)

**แก้ `StockLot`** — เพิ่มสองคอลัมน์ (ใต้ `source_type` และใต้ `cost_total`)

```python
    receipt_id: Mapped[int | None] = fk("goods_receipts.id")
```

```python
    vat_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, server_default="0")
```

แทน `__table_args__` ทั้งก้อน

```python
    __table_args__ = (
        CheckConstraint("source_type in ('receipt','adjustment','opening')", name="source_type"),
        CheckConstraint("(source_type = 'receipt') = (receipt_id is not null)", name="receipt"),
        CheckConstraint("source_type = 'receipt' or vat_amount = 0", name="adjust_vat"),
        CheckConstraint("qty_received > 0 and qty_remaining >= 0 and qty_remaining <= qty_received", name="qty"),
        CheckConstraint("unit_cost >= 0 and cost_total >= 0 and vat_amount >= 0", name="cost"),
        UniqueConstraint("receipt_id", "product_id"),
        Index("ix_stock_lots_fifo", "product_id", "created_at", "id"),
    )
```

- `source_type` เพิ่ม `receipt` · `receipt` (ใหม่): Lot จากรับของ**ต้อง**มี `receipt_id` Lot จากการปรับ**ต้องไม่มี** · `adjust_vat` (ใหม่): ปรับสต็อกไม่มี VAT
- `UniqueConstraint("receipt_id", "product_id")` = ใบรับของหนึ่งใบ สินค้าละ Lot เดียว

**แก้ `StockMovement`** — เพิ่มประเภท `receive`

```python
        CheckConstraint("movement_type in ('receive','adjust','opening')", name="type"),
        CheckConstraint("(movement_type in ('receive','opening') and qty > 0) or (movement_type = 'adjust' and qty <> 0)", name="direction"),
```

## 2. migration — ต้องแก้มือ

```
docker compose run --rm api alembic revision --autogenerate -m "purchase orders and goods receipts"
```

autogenerate เห็นตาราง/คอลัมน์/index ใหม่ครบ (เช็คว่า partial index มี `postgresql_where`) แต่**มองไม่เห็นการแก้เนื้อหา CHECK เดิม**
ไม่เติมเอง → ฐานยังใช้ CHECK เฟส 3 → รับของครั้งแรกพัง "ข้อมูลขัดกับกฎของระบบ"
เติมได้เพราะ `naming_convention` (เฟส 1) ทำให้รู้ชื่อ constraint แน่นอน

**① เหนือ `def upgrade()`**

```python
CHECKS_NEW = [
    ("stock_lots", "source_type", "source_type in ('receipt','adjustment','opening')"),
    ("stock_lots", "cost", "unit_cost >= 0 and cost_total >= 0 and vat_amount >= 0"),
    ("stock_movements", "type", "movement_type in ('receive','adjust','opening')"),
    ("stock_movements", "direction",
     "(movement_type in ('receive','opening') and qty > 0) or (movement_type = 'adjust' and qty <> 0)"),
]
CHECKS_OLD = [
    ("stock_lots", "source_type", "source_type in ('adjustment','opening')"),
    ("stock_lots", "cost", "unit_cost >= 0 and cost_total >= 0"),
    ("stock_movements", "type", "movement_type in ('adjust','opening')"),
    ("stock_movements", "direction", "(movement_type = 'opening' and qty > 0) or (movement_type = 'adjust' and qty <> 0)"),
]
```

**② ท้าย `upgrade()`** ก่อน `# ### end Alembic commands ###`

```python
    # --- เติมมือ: autogenerate มองไม่เห็นการแก้ CHECK ---
    for table, name, cond in CHECKS_NEW:
        op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, cond)
    op.create_check_constraint(op.f("ck_stock_lots_receipt"), "stock_lots",
                               "(source_type = 'receipt') = (receipt_id is not null)")
    op.create_check_constraint(op.f("ck_stock_lots_adjust_vat"), "stock_lots",
                               "source_type = 'receipt' or vat_amount = 0")
```

**③ ต้น `downgrade()`** ใต้ `# ### commands auto generated ...`

```python
    # --- เติมมือ: คืน CHECK แบบเฟส 3 ---
    op.drop_constraint(op.f("ck_stock_lots_receipt"), "stock_lots", type_="check")
    op.drop_constraint(op.f("ck_stock_lots_adjust_vat"), "stock_lots", type_="check")
    for table, name, cond in CHECKS_OLD:
        op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, cond)
```

- ลำดับ: `upgrade` = add_column ก่อน แล้วค่อยแก้ CHECK · `downgrade` = คืน CHECK ก่อน แล้วค่อย drop_column (CHECK ใหม่อ้างคอลัมน์ใหม่)
- `op.f("ck_...")` = "ชื่อเต็มแล้ว อย่าผ่าน naming_convention ซ้ำ" ลืมใส่ได้ `ck_stock_lots_ck_stock_lots_source_type`
- Postgres แก้ CHECK ตรง ๆ ไม่ได้ ต้อง drop + create · ทั้งไฟล์อยู่ในทรานแซกชันเดียว พังก็ย้อนหมด
- ข้อมูลเฟส 3 ผ่าน CHECK ใหม่ครบ (`vat_amount` ได้ 0 จาก `server_default`)
- **ห้ามแก้ไฟล์ migration เก่า** ฐานที่ upgrade ไปแล้วจะไม่รันซ้ำ — สร้างไฟล์ใหม่เสมอ

ทดสอบไป-กลับ:

```
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic downgrade -1
docker compose run --rm api alembic upgrade head
docker compose exec db psql -U garage -d garage -c "\d stock_lots"      # เห็น ck_stock_lots_receipt
```

## 3. ตัวช่วย

**`app/money.py`** — เติมท้ายไฟล์

```python
def q4(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.0001"), ROUND_HALF_UP)


def line_total(qty, unit_price) -> Decimal:
    return round_money(Decimal(qty) * Decimal(unit_price))


def purchase_vat(total_paid, rate) -> Decimal:
    """ยอดจ่ายรวม VAT แล้ว ถอด VAT ออก: ปัดฐานครั้งเดียว VAT คือส่วนที่เหลือ"""
    total_paid = Decimal(total_paid)
    return total_paid - round_money(total_paid * 100 / (100 + Decimal(rate)))


def unit_cost(cost_total, qty) -> Decimal:
    return q4(Decimal(cost_total) / Decimal(qty))
```

- `purchase_vat` ปัดครั้งเดียวที่ "ฐาน" แล้วให้ VAT เป็นส่วนที่เหลือ → ฐาน + VAT = ยอดจ่ายเป๊ะทุกกรณี (ปัดแยกสองตัวบางยอดขาด/เกิน 1 สตางค์)
- `unit_cost` เก็บ 4 ตำแหน่ง เพราะมาจากการหาร (1,000 ÷ 3 = 333.3333 · ปัด 2 ตำแหน่งแล้วคูณกลับหายไปสตางค์นึง)

**`tests/test_money.py`** — แก้ import แล้วเติม

```python
from app.money import format_qty, line_total, purchase_vat, round_money, unit_cost
```

```python
def test_purchase_vat_7_of_107():
    assert purchase_vat("856", 7) == Decimal("56.00")
    for paid in ("100", "999.99", "3800"):
        vat = purchase_vat(paid, 7)
        assert Decimal(paid) - vat == round_money(Decimal(paid) * 100 / 107)   # ฐาน + VAT = ยอดจ่ายเป๊ะ


def test_unit_cost_keeps_four_places():
    assert unit_cost("1000", 3) == Decimal("333.3333")


def test_line_total():
    assert line_total("1.5", "33.333") == Decimal("50.00")
```

**`app/textutil.py`** — ไฟล์ใหม่

```python
import re


def digits(s):
    """เก็บเฉพาะตัวเลข (เลขผู้เสียภาษี) · ว่างหรือไม่มีตัวเลขเลย → None"""
    only_digits = re.sub(r"\D", "", s or "")
    return only_digits or None
```

- `0-1055-55555-55-5` กับ `0105555555555` คือร้านเดียวกัน ต้องเหลือแต่ตัวเลขก่อนเก็บ ไม่งั้น index กันใบกำกับซ้ำจับไม่ได้
- ไม่มีตัวเลขเลย → `None` (CHECK เช็คด้วย `is null` ไม่ใช่ข้อความว่าง)
- อยู่ไฟล์กลางเพราะไม่ใช่ของโดเมนไหน (เฟส 5 เบอร์โทรลูกค้าก็ใช้)

**`app/schemas.py`** — แก้ import เป็น `from pydantic import BaseModel, ConfigDict, Field` แล้วเติมใต้ `class Out`

```python
class ReasonIn(In):
    reason: str = Field(min_length=1)
```

ปิด PO ก่อนครบกับยกเลิก PO รับแค่เหตุผลเหมือนกัน (เฟส 5–6 ยกเลิกใบงาน/บิลก็ใช้)

**`app/stock/service.py`** — เติม `products_by_id` เหนือ `save_product`

```python
def products_by_id(db, ids, label) -> dict[int, Product]:
    if len(set(ids)) != len(ids):
        raise HTTPException(422, f"สินค้าใน{label}ซ้ำกัน")
    found = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
    if len(found) != len(ids):
        raise HTTPException(422, "ไม่พบสินค้าบางรายการ")
    return found
```

- ตรวจสองอย่าง: สินค้าซ้ำในเอกสาร (`set` ตัดตัวซ้ำแล้วจำนวนลด) · มี id ที่ไม่มีจริง แล้วคืน `{id: Product}` ไว้ใช้ต่อ
- query ครั้งเดียวด้วย `in_(ids)` ไม่วนถามทีละตัว · อยู่ใน `stock/` เพราะเป็นเรื่องสินค้า โดเมนไหนก็ใช้ได้

**`app/stock/`** — ให้หน้าสต็อกรู้ว่า Lot มาจากใบรับของไหน

`stock/schemas.py`: `LotOut` เติม `receipt_id: int | None` ใต้ `source_type` · `LotAdminOut` เติม `vat_amount: Decimal` · `MovementOut` เติม `receipt_id: int | None` ใต้ `lot_id`

`stock/router.py`: `list_product_movements` ดึง `receipt_id` มาด้วย

```python
    rows = db.execute(
        select(StockMovement, StockLot.receipt_id, User.full_name)
        .join(StockLot, StockLot.id == StockMovement.lot_id)
        .join(User, User.id == StockMovement.created_by)
        .where(StockLot.product_id == product_id)
        .order_by(StockMovement.id.desc()).limit(500)
    ).all()
    return [MovementOut(id=m.id, lot_id=m.lot_id, receipt_id=receipt_id, qty=m.qty, movement_type=m.movement_type,
                        reason=m.reason, created_by_name=name, created_at=m.created_at) for m, receipt_id, name in rows]
```

`tests/test_stock.py`: บรรทัดเช็คต้นทุนหลุด เติม `vat_amount`

```python
    assert not {"unit_cost", "cost_total", "vat_amount"} & emp_lot.keys()
```

## 4. โดเมน `app/purchasing/`

สร้างโฟลเดอร์ `backend/app/purchasing/` พร้อม `__init__.py` ว่าง

### `purchasing/schemas.py`

```python
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas import In


class POItemIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=0, decimal_places=4)


class POIn(In):
    supplier_name: str = Field(min_length=1, max_length=200)
    supplier_phone: str | None = None
    supplier_tax_id: str | None = None
    supplier_address: str | None = None
    note: str | None = None
    items: list[POItemIn] = Field(min_length=1)


class POItemOut(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    unit: str
    qty: Decimal
    qty_received: Decimal
    qty_remaining: Decimal


class POItemPricedOut(POItemOut):
    unit_price: Decimal | None


class POOut(BaseModel):
    id: int
    display_number: str
    supplier_name: str
    supplier_phone: str | None
    supplier_tax_id: str | None
    supplier_address: str | None
    note: str | None
    status: str
    receive_state: str | None
    close_reason: str | None
    closed_at: datetime | None
    created_at: datetime
    created_by_name: str
    items: list[POItemOut]


class POPricedOut(POOut):
    items: list[POItemPricedOut]
    estimated_total: Decimal


class GRItemIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    total_paid: Decimal = Field(ge=0, decimal_places=2)
    vat_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class GRIn(In):
    po_id: int | None = None
    supplier_name: str | None = None
    supplier_tax_id: str | None = None
    supplier_invoice_no: str | None = None
    supplier_invoice_date: date | None = None
    items: list[GRItemIn] = Field(min_length=1)


class GRItemOut(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    unit: str
    qty: Decimal


class GRItemAdminOut(GRItemOut):
    unit_cost: Decimal
    cost_total: Decimal
    vat_amount: Decimal


class GROut(BaseModel):
    id: int
    display_number: str
    po_id: int | None
    po_number: str | None
    supplier_name: str
    supplier_tax_id: str | None
    supplier_invoice_no: str | None
    supplier_invoice_date: date | None
    created_at: datetime
    created_by_name: str
    items: list[GRItemOut]


class GRAdminOut(GROut):
    items: list[GRItemAdminOut]
    cost_total: Decimal
    vat_total: Decimal
```

| ข้อมูล | admin | employee | mechanic | schema |
|---|:---:|:---:|:---:|---|
| ราคาคาดบน PO | ✅ | ✅ | – | `POPricedOut` / `POOut` |
| ต้นทุนและ VAT บนใบรับของ | ✅ | – | – | `GRAdminOut` / `GROut` |

- **กับดัก:** ตัวลูกต้องประกาศ `items` ใหม่ (`items: list[POItemPricedOut]`) ลืมแล้วจะสืบรายการแบบไม่มีราคามาจากแม่ — สิทธิ์ต้องจัดทุกชั้น
- `items ... Field(min_length=1)` เอกสารไม่มีรายการ → 422 ตั้งแต่ขอบนอก
- รับ `total_paid` (ยอดบนบิลที่ถืออยู่) ไม่ใช่ต้นทุนต่อหน่วย ระบบหารเอง
- `vat_amount = None` = ให้ระบบถอดเอง · มีตัวเลข = ใช้ตามใบกำกับจริง (เอกสารจริงชนะการคำนวณ)
- `GRIn.supplier_name` ว่างได้ถ้าอ้าง PO (ดึงชื่อจาก PO)

### `purchasing/service.py`

```python
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select

from app.db import get_or_404, lock_shop
from app.models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem, Setting, StockLot, StockMovement
from app.money import format_qty, line_total, purchase_vat, unit_cost
from app.stock.service import products_by_id
from app.textutil import digits


def received_by_product(db, po_id) -> dict[int, Decimal]:
    rows = db.execute(select(StockLot.product_id, func.sum(StockLot.qty_received))
                      .join(GoodsReceipt, GoodsReceipt.id == StockLot.receipt_id)
                      .where(GoodsReceipt.po_id == po_id).group_by(StockLot.product_id))
    return dict(rows.all())


def _close(po, status, reason, user):
    po.status, po.close_reason = status, reason
    po.closed_by, po.closed_at = user.id, datetime.now(timezone.utc)


def create_po(db, data, user) -> PurchaseOrder:
    lock_shop(db)
    products_by_id(db, [i.product_id for i in data.items], "ใบสั่งซื้อ")
    po = PurchaseOrder(**data.model_dump(exclude={"items", "supplier_tax_id"}),
                       supplier_tax_id=digits(data.supplier_tax_id), status="open", created_by=user.id)
    po.items = [PurchaseOrderItem(**i.model_dump()) for i in data.items]
    db.add(po)
    db.commit()
    return po


def _open_po(db, po_id) -> PurchaseOrder:
    po = get_or_404(db, PurchaseOrder, po_id, "ใบสั่งซื้อ")
    if po.status != "open":
        raise HTTPException(409, "ใบสั่งซื้อนี้ปิดหรือยกเลิกแล้ว")
    return po


def close_early(db, po_id, reason, user) -> PurchaseOrder:
    lock_shop(db)
    po = _open_po(db, po_id)
    if not received_by_product(db, po.id):
        raise HTTPException(409, "ใบสั่งซื้อนี้ยังไม่เคยรับของ ให้ใช้ยกเลิกแทน")
    _close(po, "closed", reason, user)
    db.commit()
    return po


def cancel_po(db, po_id, reason, user) -> PurchaseOrder:
    lock_shop(db)
    po = _open_po(db, po_id)
    if received_by_product(db, po.id):
        raise HTTPException(409, "ใบสั่งซื้อนี้รับของไปแล้ว ให้ใช้ปิดก่อนครบแทน")
    _close(po, "cancelled", reason, user)
    db.commit()
    return po


def create_goods_receipt(db, data, user) -> GoodsReceipt:
    lock_shop(db)
    products = products_by_id(db, [i.product_id for i in data.items], "ใบรับของ")
    supplier_name = data.supplier_name or None
    tax_id = digits(data.supplier_tax_id)
    po = None
    ordered = {}  # product_id → จำนวนที่สั่ง (เฉพาะตอนอ้าง PO)
    if data.po_id:
        po = get_or_404(db, PurchaseOrder, data.po_id, "ใบสั่งซื้อ")
        if po.status != "open":
            raise HTTPException(409, "ใบสั่งซื้อนี้ปิดหรือยกเลิกแล้ว รับของไม่ได้")
        ordered = {i.product_id: i.qty for i in po.items}
        got = received_by_product(db, po.id)
        for item in data.items:
            name = products[item.product_id].name
            if item.product_id not in ordered:
                raise HTTPException(409, f"{name} ไม่อยู่ในใบสั่งซื้อ")
            remaining = ordered[item.product_id] - got.get(item.product_id, 0)
            if item.qty > remaining:
                raise HTTPException(409, f"รับเกินยอดค้างรับของ {name} (ค้าง {format_qty(remaining)})")
        supplier_name, tax_id = supplier_name or po.supplier_name, tax_id or po.supplier_tax_id
    if not supplier_name:
        raise HTTPException(422, "กรุณากรอกชื่อร้าน")
    invoice_no = (data.supplier_invoice_no or "").upper() or None
    if invoice_no:
        if not data.supplier_invoice_date or not tax_id:
            raise HTTPException(422, "ใบกำกับภาษีต้องมีวันที่และเลขผู้เสียภาษีของร้าน")
        if db.scalar(select(GoodsReceipt.id).where(GoodsReceipt.supplier_tax_id == tax_id,
                                                   GoodsReceipt.supplier_invoice_no == invoice_no)):
            raise HTTPException(409, "ใบกำกับภาษีเลขนี้ของร้านนี้ถูกบันทึกแล้ว")
    rate = db.get(Setting, 1).vat_rate
    gr = GoodsReceipt(po_id=data.po_id, supplier_name=supplier_name, supplier_tax_id=tax_id,
                      supplier_invoice_no=invoice_no, supplier_invoice_date=data.supplier_invoice_date if invoice_no else None,
                      created_by=user.id)
    db.add(gr)
    db.flush()
    for item in data.items:
        vat = Decimal(0)
        if invoice_no:
            vat = item.vat_amount if item.vat_amount is not None else purchase_vat(item.total_paid, rate)
        if vat > item.total_paid:
            raise HTTPException(422, "VAT มากกว่ายอดที่จ่าย")
        cost = item.total_paid - vat
        lot = StockLot(product_id=item.product_id, source_type="receipt", receipt_id=gr.id,
                       unit_cost=unit_cost(cost, item.qty), qty_received=item.qty, qty_remaining=item.qty,
                       cost_total=cost, vat_amount=vat, created_by=user.id)
        db.add(lot)
        db.flush()
        db.add(StockMovement(lot_id=lot.id, qty=item.qty, movement_type="receive", created_by=user.id))
    if po:
        got = received_by_product(db, po.id)
        if all(got.get(pid, 0) >= qty for pid, qty in ordered.items()):
            _close(po, "closed", None, user)
    db.commit()
    return gr


def po_view(db, po) -> dict:
    # ponytail: one received-qty query per PO in lists; batch it if PO lists get long
    got = received_by_product(db, po.id)
    items = [{"product_id": i.product_id, "product_code": i.product.code, "product_name": i.product.name,
              "unit": i.product.unit, "qty": i.qty, "unit_price": i.unit_price,
              "qty_received": got.get(i.product_id, Decimal(0)), "qty_remaining": i.qty - got.get(i.product_id, 0)}
             for i in po.items]
    receive_state = None  # ปิด/ยกเลิกแล้วไม่มีสถานะรับของ
    if po.status == "open":
        receive_state = "partial" if got else "waiting"
    return {
        "id": po.id, "display_number": f"PO-{po.id:05d}", "supplier_name": po.supplier_name,
        "supplier_phone": po.supplier_phone, "supplier_tax_id": po.supplier_tax_id,
        "supplier_address": po.supplier_address, "note": po.note, "status": po.status,
        "receive_state": receive_state,
        "close_reason": po.close_reason, "closed_at": po.closed_at, "created_at": po.created_at,
        "created_by_name": po.creator.full_name, "items": items,
        "estimated_total": sum((line_total(i["qty"], i["unit_price"]) for i in items if i["unit_price"] is not None), Decimal(0)),
    }


def gr_view(gr) -> dict:
    items = [{"product_id": lot.product_id, "product_code": lot.product.code, "product_name": lot.product.name,
              "unit": lot.product.unit, "qty": lot.qty_received, "unit_cost": lot.unit_cost,
              "cost_total": lot.cost_total, "vat_amount": lot.vat_amount} for lot in gr.lots]
    return {
        "id": gr.id, "display_number": f"GR-{gr.id:05d}", "po_id": gr.po_id,
        "po_number": f"PO-{gr.po_id:05d}" if gr.po_id else None, "supplier_name": gr.supplier_name,
        "supplier_tax_id": gr.supplier_tax_id, "supplier_invoice_no": gr.supplier_invoice_no,
        "supplier_invoice_date": gr.supplier_invoice_date, "created_at": gr.created_at,
        "created_by_name": gr.creator.full_name, "items": items,
        "cost_total": sum((i["cost_total"] for i in items), Decimal(0)),
        "vat_total": sum((i["vat_amount"] for i in items), Decimal(0)),
    }
```

**ตัวช่วย**
- `received_by_product` ตอบ "PO นี้รับแล้วสินค้าละเท่าไหร่" — Lot → ใบรับของ → PO แล้ว group by สินค้า · คำนวณสดทุกครั้ง
- `_close` ตั้ง 4 ช่องพร้อมกัน (`status` `close_reason` `closed_by` `closed_at`) ไม่มีทางลืมช่องจนชน CHECK

**สร้าง / ปิดก่อนครบ / ยกเลิก**
- `create_po` ก็ `lock_shop` — กฎเดียวทั้งระบบ "คำสั่งจัดซื้อล็อกเสมอ"
- **ยกเลิก** = ใบนี้ไม่เคยเกิดจริง (ต้องยังไม่เคยรับ) · **ปิดก่อนครบ** = รับมาบางส่วนแล้ว (ต้องเคยรับ) · ข้อความ error บอกทางออก

**`create_goods_receipt` อ่านเป็น 5 ช่วง — ทั้งหมดในทรานแซกชันเดียว**

```
① ตรวจ PO → ② ชื่อร้าน → ③ ใบกำกับ → ④ สร้างใบ + Lot + movement → ⑤ ปิด PO ถ้าครบ
```

- ① ตรวจ**ทุกรายการก่อน**แล้วค่อยสร้าง (ลูปแรกไม่สร้างอะไร) · อ่านยอดรับแล้ว (`got`) **ใต้ `lock_shop` เท่านั้น**:

```
PO สั่ง 10 · สองคนกดรับ 6 พร้อมกัน
ไม่ล็อก: ทั้งคู่เห็น "ค้าง 10" → รับเข้า 12 ❌   ล็อก: คนที่ 2 รอ → เห็น "ค้าง 4" → 409 ✅
```

- ② ไม่กรอกชื่อร้าน → ใช้ของ PO · ซื้อด่วนต้องกรอก
- ③ `.upper()` เลขใบกำกับ · เช็คซ้ำใน service ให้ข้อความดี + index ที่ฐานกันได้ 100%
- ④ VAT กรอกมาใช้ที่กรอก ไม่กรอกถอดตาม `rate` จากค่าตั้ง · ต้นทุน = ยอดจ่าย − VAT · `flush` เพื่อเอา id ไปใช้ต่อ (ยังย้อนได้จนถึง `commit`)
- ⑤ **อ่าน `received_by_product` ใหม่หลังสร้าง Lot** ใช้ตัวเก่า PO จะไม่มีวันปิด · ปิดเมื่อครบ**ทุก**รายการ

**`po_view` / `gr_view`** ประกอบข้อมูลที่หน้าจอต้องใช้จากหลายตาราง (ชื่อสินค้า · ยอดรับ/ค้าง · เลขเอกสาร · ชื่อผู้ออก · สถานะรับของ) ให้เสร็จในคำขอเดียว
คืนทุกช่องรวมราคา/ต้นทุน — **router เป็นที่เดียวที่ตัดตามสิทธิ์** (เลือก schema)

### `purchasing/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import current_user, staff
from app.db import get_db, get_or_404
from app.models import GoodsReceipt, PurchaseOrder
from app.purchasing import service
from app.purchasing.schemas import GRAdminOut, GRIn, GROut, POIn, POOut, POPricedOut
from app.schemas import ReasonIn, serialize_for_role

router = APIRouter(prefix="/api", tags=["purchasing"])


def po_out(db, user, po):
    return (POOut if user.role == "mechanic" else POPricedOut).model_validate(service.po_view(db, po))


@router.get("/purchase-orders", response_model=None)
def list_pos(status: str | None = None, db=Depends(get_db), user=Depends(current_user)):
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(200)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    return [po_out(db, user, po) for po in db.scalars(stmt)]


@router.post("/purchase-orders", response_model=None, status_code=201)
def create_po(data: POIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, service.create_po(db, data, user))


@router.get("/purchase-orders/{po_id}", response_model=None)
def get_po(po_id: int, db=Depends(get_db), user=Depends(current_user)):
    return po_out(db, user, get_or_404(db, PurchaseOrder, po_id, "ใบสั่งซื้อ"))


@router.post("/purchase-orders/{po_id}/close-early", response_model=None)
def close_early(po_id: int, data: ReasonIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, service.close_early(db, po_id, data.reason, user))


@router.post("/purchase-orders/{po_id}/cancel", response_model=None)
def cancel_po(po_id: int, data: ReasonIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, service.cancel_po(db, po_id, data.reason, user))


@router.get("/goods-receipts", response_model=None)
def list_receipts(db=Depends(get_db), user=Depends(current_user)):
    stmt = select(GoodsReceipt).order_by(GoodsReceipt.id.desc()).limit(200)
    if user.role == "mechanic":
        stmt = stmt.where(GoodsReceipt.created_by == user.id)
    return [serialize_for_role(user, GRAdminOut, GROut, service.gr_view(gr)) for gr in db.scalars(stmt)]


@router.post("/goods-receipts", response_model=None, status_code=201)
def create_receipt(data: GRIn, db=Depends(get_db), user=Depends(current_user)):
    return serialize_for_role(user, GRAdminOut, GROut, service.gr_view(service.create_goods_receipt(db, data, user)))


@router.get("/goods-receipts/{gr_id}", response_model=None)
def get_receipt(gr_id: int, db=Depends(get_db), user=Depends(current_user)):
    gr = get_or_404(db, GoodsReceipt, gr_id, "ใบรับของ")
    if user.role == "mechanic" and gr.created_by != user.id:
        raise HTTPException(404, "ไม่พบใบรับของ")
    return serialize_for_role(user, GRAdminOut, GROut, service.gr_view(gr))
```

| คำสั่ง | ใครทำได้ |
|---|---|
| ออก / ปิดก่อนครบ / ยกเลิก PO | `staff` |
| บันทึกใบรับของ | ทุกคน (`current_user`) |

- ช่างเห็นเฉพาะใบรับของที่ตัวเองบันทึก — กัน**สองที่** (รายการ + หน้ารายละเอียด) ลืมที่สอง = เดา id ดูใบคนอื่นได้
- เปิดใบคนอื่นตอบ **404 ไม่ใช่ 403** — 403 ยืนยันว่าใบนั้นมีจริง
- `response_model=None` ทุกเส้น เพราะ schema ขึ้นกับบทบาท · `?status=open` ให้หน้ารับของดึงเฉพาะ PO ที่ยังรับได้

### `app/main.py` — เติม router

```python
from app.purchasing import router as purchasing
```

```python
app.include_router(purchasing.router)
```

## 5. เทสต์ — `tests/test_purchasing.py`

```python
import threading
from decimal import Decimal

from fastapi import HTTPException

from app.db import SessionLocal
from app.purchasing.schemas import GRIn, GRItemIn, POIn, POItemIn
from app.purchasing.service import create_goods_receipt, create_po

INVOICE = dict(
    supplier_name="ร้าน ก",
    supplier_tax_id="0105555555555",
    supplier_invoice_no="iv-001",
    supplier_invoice_date="2026-09-01",
)


def po(client, headers, items, role="employee"):
    return client.post(
        "/api/purchase-orders",
        headers=headers[role],
        json={"supplier_name": "ร้านอะไหล่ดี", "supplier_tax_id": "0-1055-55555-55-5", "items": items},
    )


def receive(client, headers, items, role="employee", **head):
    return client.post("/api/goods-receipts", json={"items": items, **head}, headers=headers[role])


def get_po(client, headers, po_id, role="employee"):
    return client.get(f"/api/purchase-orders/{po_id}", headers=headers[role]).json()


def test_case3_tax_invoice_splits_vat_and_blocks_duplicate(client, headers, make_product):
    pid = make_product()
    r = receive(client, headers, [{"product_id": pid, "qty": "4", "total_paid": "856"}], **INVOICE)
    assert r.status_code == 201, r.text
    assert "cost_total" not in r.json()
    gr = client.get(f"/api/goods-receipts/{r.json()['id']}", headers=headers["admin"]).json()
    assert (Decimal(gr["vat_total"]), Decimal(gr["cost_total"]), Decimal(gr["items"][0]["unit_cost"])) == (56, 800, 200)
    assert gr["supplier_invoice_no"] == "IV-001" and gr["display_number"] == "GR-00001"
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "1", "total_paid": "107"}], **INVOICE).status_code == 409
    )


def test_quick_purchase_without_invoice_cost_is_total_paid(client, headers, make_product):
    pid = make_product()
    r = receive(
        client,
        headers,
        [{"product_id": pid, "qty": "2", "total_paid": "300"}],
        role="mechanic",
        supplier_name="ร้านข้างอู่",
    )
    assert r.status_code == 201, r.text
    gr = client.get(f"/api/goods-receipts/{r.json()['id']}", headers=headers["admin"]).json()
    assert (Decimal(gr["cost_total"]), Decimal(gr["vat_total"])) == (300, 0)


def test_case13_po_rules(client, headers, make_product):
    pid, other = make_product("P1"), make_product("P2")
    assert po(client, headers, [{"product_id": pid, "qty": "1"}], role="mechanic").status_code == 403
    assert po(client, headers, []).status_code == 422
    po_id = po(client, headers, [{"product_id": pid, "qty": "5", "unit_price": "100"}]).json()["id"]
    assert (
        receive(client, headers, [{"product_id": other, "qty": "1", "total_paid": "10"}], po_id=po_id).status_code
        == 409
    )
    cancel = f"/api/purchase-orders/{po_id}/cancel"
    assert client.post(cancel, json={"reason": ""}, headers=headers["employee"]).status_code == 422
    assert (
        client.post(cancel, json={"reason": "ร้านไม่มีของ"}, headers=headers["employee"]).json()["status"] == "cancelled"
    )
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "1", "total_paid": "10"}], po_id=po_id).status_code == 409
    )


def test_mechanic_hides_po_prices_and_sees_only_own_receipts(client, headers, make_product):
    pid = make_product()
    po_id = po(client, headers, [{"product_id": pid, "qty": "5", "unit_price": "100"}]).json()["id"]
    mech = get_po(client, headers, po_id, "mechanic")
    assert "unit_price" not in mech["items"][0] and "estimated_total" not in mech
    assert Decimal(get_po(client, headers, po_id)["estimated_total"]) == 500
    line = [{"product_id": pid, "qty": "1", "total_paid": "100"}]
    emp_gr = receive(client, headers, line, supplier_name="ร้าน ก").json()["id"]
    mech_gr = receive(client, headers, line, role="mechanic", supplier_name="ร้าน ข").json()["id"]
    assert [g["id"] for g in client.get("/api/goods-receipts", headers=headers["mechanic"]).json()] == [mech_gr]
    assert client.get(f"/api/goods-receipts/{emp_gr}", headers=headers["mechanic"]).status_code == 404


def test_case14_partial_receipts_until_auto_close(client, headers, make_product):
    pid = make_product()
    po_id = po(client, headers, [{"product_id": pid, "qty": "10"}]).json()["id"]
    assert get_po(client, headers, po_id)["receive_state"] == "waiting"
    r = receive(client, headers, [{"product_id": pid, "qty": "6", "total_paid": "600"}], po_id=po_id)
    assert r.status_code == 201, r.text
    assert r.json()["supplier_name"] == "ร้านอะไหล่ดี"
    detail = get_po(client, headers, po_id)
    assert (detail["status"], detail["receive_state"], Decimal(detail["items"][0]["qty_remaining"])) == (
        "open",
        "partial",
        4,
    )
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "5", "total_paid": "500"}], po_id=po_id).status_code == 409
    )
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "4", "total_paid": "400"}], po_id=po_id).status_code == 201
    )
    assert get_po(client, headers, po_id)["status"] == "closed"
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "1", "total_paid": "100"}], po_id=po_id).status_code == 409
    )


def test_case15_close_early_vs_cancel(client, headers, make_product):
    pid = make_product()
    po_id = po(client, headers, [{"product_id": pid, "qty": "10"}]).json()["id"]
    close = f"/api/purchase-orders/{po_id}/close-early"
    assert client.post(close, json={"reason": "x"}, headers=headers["employee"]).status_code == 409
    receive(client, headers, [{"product_id": pid, "qty": "3", "total_paid": "300"}], po_id=po_id)
    assert (
        client.post(
            f"/api/purchase-orders/{po_id}/cancel", json={"reason": "x"}, headers=headers["employee"]
        ).status_code
        == 409
    )
    assert client.post(close, json={"reason": ""}, headers=headers["employee"]).status_code == 422
    r = client.post(close, json={"reason": "ร้านเลิกขาย"}, headers=headers["employee"]).json()
    assert (r["status"], r["close_reason"]) == ("closed", "ร้านเลิกขาย")
    assert (
        receive(client, headers, [{"product_id": pid, "qty": "1", "total_paid": "100"}], po_id=po_id).status_code == 409
    )


def test_case15_concurrent_receipts_never_exceed_ordered(users, make_product):
    pid, employee = make_product(), users["employee"]
    with SessionLocal() as s:
        po_id = create_po(s, POIn(supplier_name="ร้าน ก", items=[POItemIn(product_id=pid, qty=10)]), employee).id
    barrier, results = threading.Barrier(2), []

    def worker():
        barrier.wait()
        with SessionLocal() as s:
            try:
                create_goods_receipt(
                    s, GRIn(po_id=po_id, items=[GRItemIn(product_id=pid, qty=6, total_paid=600)]), employee
                )
                results.append("ok")
            except HTTPException as e:
                results.append(e.status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results, key=str) == [409, "ok"]
```

- ชื่อเทสต์ตาม**กรณีตรวจรับ**ที่ตกลงกับเจ้าของอู่ — ถูกถาม "ข้อ 15 ทำได้หรือยัง" เปิดดูชื่อเทสต์ตอบได้เลย
- `test_case14` เดินเรื่องจริงทั้งเส้น: สั่ง 10 → "รอของ" → รับ 6 → "รับบางส่วน" ค้าง 4 → รับ 5 ได้ 409 → รับ 4 → PO ปิดเอง
- `test_case15_concurrent` ยิงสองเธรดจริง (`Barrier` ปล่อยพร้อมกัน · คนละ session) ต้องผ่าน 1 พัง 1 — **ลองลบ `lock_shop` จาก `create_goods_receipt` แล้วเทสต์จะแดง**
- ตัวช่วย `po()` ส่งเลขผู้เสียภาษีแบบมีขีด เพื่อทดสอบ `digits`

```
docker compose run --rm api pytest
```

---

# หน้าจอ

7 หน้า: รายการ PO · สร้าง PO · รายละเอียด PO · รายการใบรับของ · บันทึกรับของ · รายละเอียดใบรับของ · หน้าพิมพ์ PO

## 6. ของกลางที่เติม

**`api.js`** — เติมท้ายไฟล์

```js
// เลขเอกสารจาก id แบบเดียวกับ backend: docNo("PO", 5) → "PO-00005"
export const docNo = (prefix, id) => `${prefix}-${String(id).padStart(5, "0")}`;

// วันนี้ตามเวลาไทยในรูป YYYY-MM-DD (ค่าที่ <input type="date"> ต้องการ)
export const todayBangkok = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bangkok" }).format(new Date());
```

- `docNo` ทำเลขเอกสารแบบเดียวกับ backend — หน้า Lot ได้ `receipt_id` เป็นตัวเลขเปล่า ต้องแสดง `GR-00001`
- `todayBangkok` วันนี้ตามเวลาไทย (`toISOString()` เป็นวัน UTC ตีหนึ่งไทยจะได้เมื่อวาน) · `en-CA` เรียงเป็น `YYYY-MM-DD` พอดีกับ `<input type="date">`

**`index.css`** — ใต้ปีกกาปิดของ `@theme` (กฎตอนพิมพ์ ขนาดกระดาษ + ขอบ)

```css
@page { size: A4; margin: 12mm; }
```

ใต้ `.btn-secondary` (ปุ่มแดงสำหรับคำสั่งที่ย้อนไม่ได้)

```css
  .btn-danger { @apply bg-danger text-white hover:brightness-110; }
```

เหนือ `.tabs` (ปุ่มกลมเลือกของจากรายการสั้น ใส่คู่ `chip chip-on` เหมือน `btn btn-primary`)

```css
  .chip { @apply inline-flex min-h-11 cursor-pointer items-center rounded-full border border-line bg-white px-4 text-sm font-medium whitespace-nowrap transition-colors duration-150 hover:border-accent; }
  .chip-on { @apply border-accent bg-accent-soft text-accent-ink; }
```

**`components/Icon.jsx`** — เติมใน `PATHS`

```jsx
  clipboard: <><rect width="8" height="4" x="8" y="2" rx="1" ry="1" /><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><path d="M12 11h4" /><path d="M12 16h4" /><path d="M8 11h.01" /><path d="M8 16h.01" /></>,
  truck: <><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2" /><path d="M15 18H9" /><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14" /><circle cx="17" cy="18" r="2" /><circle cx="7" cy="18" r="2" /></>,
  printer: <><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6" /><rect x="6" y="14" width="12" height="8" rx="1" /></>,
```

**`components/StatusBadge.jsx`** — ใน `STATUS` เติมบนสุด

```jsx
  waiting: ["รอของ", "info"],
  partial: ["รับบางส่วน", "warn"],
  closed: ["ปิดแล้ว", "neutral"],
  cancelled: ["ยกเลิก", "danger"],
```

ใต้ `disabled`

```jsx
  quick: ["ซื้อด่วน", "neutral"],
```

เหนือ comment ของ `productStatus`

```jsx
// สถานะ PO ที่มีความหมายที่สุดป้ายเดียว: เปิดอยู่ → รอของ/รับบางส่วน, ปิด/ยกเลิก → สถานะจริง
export const poStatus = (po) => (po.status === "open" ? po.receive_state : po.status);
```

`poStatus` เหลือป้ายเดียวที่มีความหมาย: เปิดอยู่ → "รอของ"/"รับบางส่วน" · ปิด/ยกเลิก → สถานะจริง

**`components/DetailLayout.jsx`** — ใน `MoreMenu` แก้ `className` ของปุ่ม (ส่ง `danger: true` = ตัวหนังสือแดง)

```jsx
              className={`flex min-h-11 w-full items-center px-4 text-left hover:bg-surface ${m.danger ? "text-danger" : ""}`}
```

**`components/ReasonDialog.jsx`** — ปุ่มยืนยันสีแดงได้ (ค่าปริยาย `false` ที่ใช้อยู่เดิมไม่ต้องแก้)

```jsx
export default function ReasonDialog({ title, onClose, onSubmit, register, mutation, danger = false, children }) {
```

```jsx
            <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} disabled={mutation.isPending}>
              {mutation.isPending ? "กำลังบันทึก…" : "ยืนยัน"}
            </button>
```

แก้ comment บนสุด

```jsx
// popup ที่มีช่อง "เหตุผล" ท้ายฟอร์ม: ฟอร์ม (register/onSubmit) และ mutation มาจากคนเรียก, danger = ปุ่มยืนยันสีแดง
```

**`pages/ProductDetailPage.jsx`** — ให้รู้จัก Lot จากการรับของ แก้ 5 จุด

```jsx
import { api, docNo, formatMoney, formatQty, formatDate, formatUnitPrice } from "../api";
```

```jsx
const SOURCE_LABEL = { receipt: "รับของ", opening: "สต็อกตั้งต้น" };
const MOVE_LABEL = { receive: "รับของ", adjust: "ของเสีย/สูญหาย", opening: "ตั้งต้น" };
```

หัว Lot (ใน `LotList`)

```jsx
              <span className="font-semibold">
                Lot #{lot.id} · {SOURCE_LABEL[lot.source_type]}
                {lot.receipt_id && ` ${docNo("GR", lot.receipt_id)}`}
              </span>
```

บรรทัดต้นทุน (ใน `LotList`)

```jsx
            {showCost && (
              <div className="num text-sm">
                ต้นทุน/หน่วย {formatUnitPrice(lot.unit_cost)} · ภาษีซื้อ {formatMoney(lot.vat_amount)}
              </div>
            )}
```

สมุดสต็อก (ใน `MovementList`) — `.filter(Boolean)` ตัดค่าว่างก่อน `join` ไม่งั้น movement ที่ไม่มีใบรับของมี `·` ห้อยท้าย

```jsx
              <div className="text-muted">
                {[formatDate(m.created_at), m.created_by_name, m.receipt_id && docNo("GR", m.receipt_id)]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
```

## 7. `components/ProductSearch.jsx` — ค้นแล้วแตะเลือกสินค้า

```jsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { formatQty } from "../api";
import Icon from "./Icon";

// ช่องค้นสินค้า (รหัส/ชื่อ) จาก cache ["products"] ชุดเดียวกับหน้าสต็อก แตะแถวแล้วส่งสินค้าให้ onPick
export default function ProductSearch({ onPick }) {
  const { data: products } = useQuery({ queryKey: ["products"] });
  const [q, setQ] = useState("");
  const text = q.trim().toLowerCase();
  const found = products
    ?.filter(
      (p) => p.is_active && (!text || p.code.toLowerCase().includes(text) || p.name.toLowerCase().includes(text)),
    )
    .slice(0, 20);

  return (
    <div className="space-y-2">
      <label className="relative block">
        <span className="sr-only">ค้นชื่อหรือรหัสสินค้า</span>
        <Icon
          name="search"
          size={20}
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          className="input pl-10"
          placeholder="ค้นชื่อหรือรหัสสินค้า"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>
      {!found ? (
        <p className="text-sm text-muted">กำลังโหลด…</p>
      ) : found.length === 0 ? (
        <p className="text-sm text-muted">ไม่พบสินค้า</p>
      ) : (
        <ul className="max-h-72 divide-y divide-line overflow-y-auto rounded-lg border border-line">
          {found.map((p) => {
            const out = Number(p.qty_on_hand) <= 0;
            return (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => {
                    onPick(p);
                    setQ("");
                  }}
                  className="flex min-h-12 w-full items-center px-3 py-2 text-left hover:bg-surface"
                >
                  <span className="min-w-0">
                    <span className={`block truncate font-medium ${out ? "text-muted" : ""}`}>{p.name}</span>
                    <span className="block text-sm text-muted">
                      {p.code} ·{" "}
                      {out ? <span className="text-danger">หมด</span> : `เหลือ ${formatQty(p.qty_on_hand)} ${p.unit}`}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
```

- ไม่ใช้ `<select>` เพราะสินค้าหลายร้อยตัว บนมือถือเลื่อนหาไม่เจอ พิมพ์แล้วแตะเร็วกว่า
- `useQuery(["products"])` ในตัวเอง กุญแจเดียวกับหน้าสต็อก คนเรียกส่งแค่ `onPick`
- โชว์คงเหลือ / "หมด" สีแดง · ตัดที่ 20 แถว · ซ่อนสินค้าเลิกใช้ · เลือกแล้วล้างช่องค้น (มักเพิ่มหลายตัวติดกัน)
- ช่องค้นใช้ `useState` ไม่ใช่ `useForm` — ไม่ใช่ข้อมูลที่ส่งไป backend

## 8. `pages/PurchaseOrderListPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, formatDate, formatMoney } from "../api";
import { useAuth } from "../auth";
import DataTable from "../components/DataTable";
import ListLayout from "../components/ListLayout";
import SearchBar from "../components/SearchBar";
import StatusBadge, { poStatus } from "../components/StatusBadge";

const FILTERS = [
  ["open", "เปิดอยู่"],
  ["closed", "ปิดแล้ว"],
  ["cancelled", "ยกเลิก"],
  ["all", "ทั้งหมด"],
];

// หน้า /purchase-orders: GET /purchase-orders?status= ตามแท็บ แล้วค้นเลขที่/ร้านฝั่ง client, route ลูก new เปิด popup สร้าง PO
export default function PurchaseOrderListPage() {
  const { user } = useAuth();
  const isStaff = user.role !== "mechanic";
  const [status, setStatus] = useState("open");
  const [q, setQ] = useState("");
  const { data, error } = useQuery({
    queryKey: ["purchase-orders", { status }],
    queryFn: () => api(status === "all" ? "/purchase-orders" : `/purchase-orders?status=${status}`),
  });
  const text = q.trim().toLowerCase();
  const items = data?.filter(
    (po) => !text || po.display_number.toLowerCase().includes(text) || po.supplier_name.toLowerCase().includes(text),
  );

  return (
    <ListLayout
      title="ใบสั่งซื้อ"
      basePath="/purchase-orders"
      action={isStaff && { label: "สร้างใบสั่งซื้อ", to: "/purchase-orders/new" }}
      toolbar={
        <SearchBar
          q={q}
          setQ={setQ}
          placeholder="ค้นเลขที่หรือร้าน"
          filters={FILTERS}
          filter={status}
          setFilter={setStatus}
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
        to={(po) => `/purchase-orders/${po.id}`}
        empty="ไม่มีใบสั่งซื้อ"
        card={(po) => (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold">{po.display_number}</span>
              <StatusBadge status={poStatus(po)} />
            </div>
            <div className="truncate">{po.supplier_name}</div>
            <div className="mt-1 flex justify-between gap-2 text-sm text-muted">
              <span>
                {formatDate(po.created_at)} · {po.items.length} รายการ
              </span>
              {isStaff && <span className="num font-semibold text-ink">{formatMoney(po.estimated_total)}</span>}
            </div>
          </>
        )}
        columns={[
          { label: "เลขที่", render: (po) => po.display_number },
          { label: "ร้าน", render: (po) => po.supplier_name },
          { label: "วันที่", render: (po) => formatDate(po.created_at) },
          { label: "สถานะ", render: (po) => <StatusBadge status={poStatus(po)} /> },
          { label: "รายการ", align: "right", render: (po) => po.items.length },
          ...(isStaff
            ? [{ label: "ยอดประมาณการ", align: "right", render: (po) => formatMoney(po.estimated_total) }]
            : []),
        ]}
      />
    </ListLayout>
  );
}
```

- สถานะกรองที่ **API** (`?status=`) เพราะ PO สะสมไม่มีเพดาน · คำค้นกรองในเบราว์เซอร์
- มี query string → เขียน `queryFn` เอง แต่กุญแจยังขึ้นต้น `"purchase-orders"` → invalidate กลุ่มเดิมจับได้
- `{ status }` อยู่ในกุญแจ = แต่ละแท็บมี cache ของตัวเอง สลับกลับได้ทันที
- `...(isStaff ? [คอลัมน์] : [])` เพิ่มคอลัมน์ยอดประมาณการเฉพาะ staff

## 9. `pages/PurchaseOrderFormPage.jsx` — ป๊อปอัพสร้าง PO

```jsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate, useOutletContext } from "react-router-dom";
import { api, formatMoney } from "../api";
import Field from "../components/Field";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import ProductSearch from "../components/ProductSearch";

const EMPTY_PO = {
  supplier_name: "",
  supplier_phone: "",
  supplier_tax_id: "",
  supplier_address: "",
  note: "",
  items: [],
};

// popup /purchase-orders/new: หัวเอกสาร + รายการสินค้าหลายแถว → POST /purchase-orders แล้วไปหน้า PO ใหม่
export default function PurchaseOrderFormPage() {
  const { close } = useOutletContext();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { register, handleSubmit, control, watch } = useForm({ defaultValues: EMPTY_PO });
  const { fields, append, remove } = useFieldArray({ control, name: "items" }); // แต่ละแถว { product, qty, unit_price }
  const items = watch("items");
  // ไว้โชว์ระหว่างกรอกเท่านั้น ยอดจริง backend คิดด้วย Decimal
  const estimate = items.reduce((sum, it) => sum + Number(it.qty || 0) * Number(it.unit_price || 0), 0);

  // แตะสินค้าที่มีในรายการแล้ว ไม่เพิ่มซ้ำ
  const addProduct = (p) => {
    if (!items.some((it) => it.product.id === p.id)) append({ product: p, qty: "", unit_price: "" });
  };

  const save = useMutation({
    mutationFn: ({ items, ...head }) =>
      api("/purchase-orders", {
        method: "POST",
        body: {
          ...head,
          items: items.map((it) => ({ product_id: it.product.id, qty: it.qty, unit_price: it.unit_price || null })),
        },
      }),
    onSuccess: (po) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      navigate(`/purchase-orders/${po.id}`);
    },
  });

  return (
    <Modal
      title="สร้างใบสั่งซื้อ"
      onClose={close}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {save.error && (
            <p role="alert" className="field-error mb-2">
              {save.error.message}
            </p>
          )}
          <div className="flex items-center gap-3">
            <div className="mr-auto text-sm">
              <div className="text-muted">ยอดประมาณการ</div>
              <div className="num text-lg font-bold">{formatMoney(estimate)}</div>
            </div>
            <button className="btn btn-primary" disabled={save.isPending || fields.length === 0}>
              {save.isPending ? "กำลังบันทึก…" : "บันทึกใบสั่งซื้อ"}
            </button>
          </div>
        </>
      }
    >
      <Field label="ชื่อร้าน" required {...register("supplier_name")} />
      <details className="rounded-lg border border-line px-3">
        <summary className="flex min-h-11 cursor-pointer items-center font-medium">
          ข้อมูลร้านเพิ่มเติม (ไม่บังคับ)
        </summary>
        <div className="space-y-3 pb-3">
          <Field label="เบอร์โทรร้าน" type="tel" inputMode="tel" {...register("supplier_phone")} />
          <Field label="เลขผู้เสียภาษีร้าน" inputMode="numeric" {...register("supplier_tax_id")} />
          <Field label="ที่อยู่ร้าน" {...register("supplier_address")} />
          <Field label="หมายเหตุ" {...register("note")} />
        </div>
      </details>

      <section className="space-y-2">
        <h3 className="font-semibold">รายการ</h3>
        {fields.length > 0 && (
          <ul className="divide-y divide-line rounded-lg border border-line">
            {fields.map((field, i) => (
              <li key={field.id} className="space-y-2 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="min-w-0 font-medium">
                    {field.product.name} <span className="text-sm text-muted">{field.product.code}</span>
                  </span>
                  <button
                    type="button"
                    aria-label={`ลบ ${field.product.name}`}
                    className="btn btn-ghost btn-icon text-muted hover:text-danger"
                    onClick={() => remove(i)}
                  >
                    <Icon name="close" size={18} />
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field
                    label={`จำนวน (${field.product.unit})`}
                    type="number"
                    inputMode="decimal"
                    step="0.001"
                    min="0.001"
                    required
                    {...register(`items.${i}.qty`)}
                  />
                  <Field
                    label="ราคา/หน่วย"
                    hint="ไม่บังคับ"
                    type="number"
                    inputMode="decimal"
                    step="0.01"
                    min="0"
                    {...register(`items.${i}.unit_price`)}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
        <ProductSearch onPick={addProduct} />
      </section>
    </Modal>
  );
}
```

- `useFieldArray` = รายการเพิ่ม/ลบแถวได้ในฟอร์มเดียวกับหัวเอกสาร: `fields` ไว้วาด · `append` เพิ่ม · `remove(i)` ลบ · ช่องในแถว ``register(`items.${i}.qty`)``
- `key={field.id}` ไม่ใช่ `key={i}` — ลบแถวกลางแล้วค่าที่พิมพ์ไว้ไม่สลับช่อง
- แต่ละแถวเก็บ object สินค้าทั้งก้อน (ไว้โชว์ชื่อ/หน่วย) ตอนส่งค่อยแปลงเป็น `product_id`
- `fields` = สำเนาตอนเพิ่มแถว · `watch("items")` = ค่าล่าสุด ใช้คำนวณยอดประมาณการ (Number ได้เพราะแค่โชว์ ยอดจริง backend คิดด้วย Decimal)
- แตะสินค้าซ้ำ → เงียบ ไม่เพิ่ม · `unit_price || null` ช่องว่าง = ไม่ระบุราคา · `<details>` ซ่อนข้อมูลร้านที่ไม่บังคับ
- บันทึกแล้วไปหน้า PO เพราะงานถัดไปคือพิมพ์ส่งร้าน

## 10. `pages/PurchaseOrderDetailPage.jsx`

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { api, formatDate, formatMoney, formatQty } from "../api";
import { useAuth } from "../auth";
import DetailLayout from "../components/DetailLayout";
import Icon from "../components/Icon";
import ReasonDialog from "../components/ReasonDialog";
import StatusBadge, { poStatus } from "../components/StatusBadge";

const ACTION_TITLE = { cancel: "ยกเลิกใบสั่งซื้อ", "close-early": "ปิดใบสั่งซื้อก่อนรับครบ" };

// หน้า /purchase-orders/:id: หัว PO + ความคืบหน้ารับของต่อรายการ, เมนูพิมพ์/ปิดก่อนครบ/ยกเลิก เฉพาะที่ทำได้ตอนนี้
export default function PurchaseOrderDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isStaff = user.role !== "mechanic";
  const { data: po, error } = useQuery({ queryKey: ["purchase-orders", id] });
  const [action, setAction] = useState(null); // null | "cancel" | "close-early"

  if (!po) {
    return <DetailLayout back="/purchase-orders" backLabel="สั่งซื้อ" title={error?.message || "กำลังโหลด…"} />;
  }

  const info = [
    ["เบอร์โทร", po.supplier_phone],
    ["เลขผู้เสียภาษี", po.supplier_tax_id],
    ["ที่อยู่", po.supplier_address],
    ["หมายเหตุ", po.note],
    ["ผู้ออก", `${po.created_by_name} · ${formatDate(po.created_at)}`],
    ["เหตุผลปิด/ยกเลิก", po.close_reason],
  ];
  // เมนู ⋯ มีเฉพาะคำสั่งที่ทำได้ตอนนี้ (ตรงกับกฎ service: ปิดก่อนครบต้องเคยรับ · ยกเลิกต้องยังไม่เคยรับ)
  const menu = [];
  if (isStaff) {
    menu.push({ label: "พิมพ์ใบสั่งซื้อ", onClick: () => window.open(`/print/po/${po.id}`, "_blank", "noreferrer") });
  }
  if (isStaff && po.receive_state === "partial") {
    menu.push({ label: "ปิดก่อนรับครบ", onClick: () => setAction("close-early") });
  }
  if (isStaff && po.receive_state === "waiting") {
    menu.push({ label: "ยกเลิกใบสั่งซื้อ", danger: true, onClick: () => setAction("cancel") });
  }

  return (
    <DetailLayout
      back="/purchase-orders"
      backLabel="สั่งซื้อ"
      title={po.display_number}
      subtitle={po.supplier_name}
      badge={<StatusBadge status={poStatus(po)} />}
      menu={menu}
      footer={
        po.status === "open" && (
          <Link to={`/goods-receipts/new?po=${po.id}`} className="btn btn-primary w-full">
            <Icon name="truck" size={20} />
            รับของตาม PO นี้
          </Link>
        )
      }
    >
      <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        {info
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <div key={label}>
              <dt className="text-muted">{label}</dt>
              <dd className="font-medium">{value}</dd>
            </div>
          ))}
      </dl>

      <ul className="divide-y divide-line rounded-xl border border-line">
        {po.items.map((it) => (
          <PoItem key={it.product_id} item={it} showPrice={isStaff} />
        ))}
      </ul>
      {isStaff && (
        <div className="flex justify-between px-1 font-semibold">
          <span>ยอดประมาณการ</span>
          <span className="num">{formatMoney(po.estimated_total)}</span>
        </div>
      )}

      {action && <PoActionDialog poId={po.id} action={action} onClose={() => setAction(null)} />}
    </DetailLayout>
  );
}

// หนึ่งรายการใน PO: รับแล้ว/สั่ง/ค้าง + แถบความคืบหน้า, ราคาคาดการณ์โชว์เฉพาะ staff
function PoItem({ item, showPrice }) {
  const percent = Math.min(100, (Number(item.qty_received) / Number(item.qty)) * 100);
  return (
    <li className="px-4 py-3">
      <div className="flex justify-between gap-2">
        <span className="font-semibold">{item.product_name}</span>
        <span className="text-sm text-muted">{item.product_code}</span>
      </div>
      <div className="num mt-1 text-sm">
        รับแล้ว {formatQty(item.qty_received)} / {formatQty(item.qty)} {item.unit} · ค้าง{" "}
        <b>{formatQty(item.qty_remaining)}</b>
      </div>
      <div
        role="progressbar"
        aria-label={`รับแล้ว ${item.product_name}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(percent)}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-line"
      >
        <div className="h-full bg-accent" style={{ width: `${percent}%` }} />
      </div>
      {showPrice && item.unit_price != null && (
        <div className="num mt-1 text-sm text-muted">
          ราคาคาดการณ์ {formatMoney(item.unit_price)} · รวม {formatMoney(Number(item.qty) * Number(item.unit_price))}
        </div>
      )}
    </li>
  );
}

// popup ปิดก่อนครบ / ยกเลิก: POST /purchase-orders/{id}/{action} { reason } แล้วให้ข้อมูล PO ทุกหน้าโหลดใหม่
function PoActionDialog({ poId, action, onClose }) {
  const queryClient = useQueryClient();
  const { register, handleSubmit } = useForm({ defaultValues: { reason: "" } });
  const applyAction = useMutation({
    mutationFn: (form) => api(`/purchase-orders/${poId}/${action}`, { method: "POST", body: form }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      onClose();
    },
  });
  return (
    <ReasonDialog
      title={ACTION_TITLE[action]}
      danger={action === "cancel"}
      onClose={onClose}
      register={register}
      mutation={applyAction}
      onSubmit={handleSubmit((form) => applyAction.mutate(form))}
    />
  );
}
```

- แบ่งสามชิ้น: หน้า (ดึง PO · เมนู · รายการ) · `PoItem` (หนึ่งรายการ + แถบความคืบหน้า) · `PoActionDialog` (ปิดก่อนครบ / ยกเลิก)
- **เมนู ⋯ มีเฉพาะคำสั่งที่ทำได้ตอนนี้** ตรงกับกฎ service — ผู้ใช้ไม่มีทางกดแล้วเจอ error
- `action` เก็บชื่อ endpoint (`"cancel"` / `"close-early"`) ต่อ URL ได้เลย ป๊อปอัพเดียวใช้ได้สองคำสั่ง
- "รับของตาม PO นี้" ส่ง PO ผ่าน `?po=5` ให้หน้ารับของเลือกให้เอง · หน้าพิมพ์เปิดแท็บใหม่
- แถบความคืบหน้ามี `role="progressbar"` ให้ screen reader อ่านได้

## 11. `pages/GoodsReceiptListPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { formatDate, formatMoney } from "../api";
import { useAuth } from "../auth";
import DataTable from "../components/DataTable";
import ListLayout from "../components/ListLayout";
import SearchBar from "../components/SearchBar";
import StatusBadge from "../components/StatusBadge";

// ป้ายที่มา: อ้าง PO → เลข PO, ไม่อ้าง → "ซื้อด่วน"
const SourceBadge = ({ gr }) =>
  gr.po_id ? <span className="badge badge-info">{gr.po_number}</span> : <StatusBadge status="quick" />;

// หน้า /goods-receipts: GET /goods-receipts (ช่างได้แค่ใบของตัวเอง) ค้นเลขที่/ร้านฝั่ง client, route ลูก new เปิด popup รับของ
export default function GoodsReceiptListPage() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const { data, error } = useQuery({ queryKey: ["goods-receipts"] });
  const [q, setQ] = useState("");
  const text = q.trim().toLowerCase();
  const items = data?.filter(
    (gr) => !text || gr.display_number.toLowerCase().includes(text) || gr.supplier_name.toLowerCase().includes(text),
  );

  return (
    <ListLayout
      title="รับของ"
      basePath="/goods-receipts"
      action={{ label: "บันทึกรับของ", to: "/goods-receipts/new" }}
      toolbar={<SearchBar q={q} setQ={setQ} placeholder="ค้นเลขที่หรือร้าน" />}
    >
      {user.role === "mechanic" && <p className="text-sm text-muted">แสดงเฉพาะใบรับของที่คุณบันทึก</p>}
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      <DataTable
        items={items}
        to={(gr) => `/goods-receipts/${gr.id}`}
        empty="ยังไม่มีใบรับของ"
        card={(gr) => (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold">{gr.display_number}</span>
              <SourceBadge gr={gr} />
            </div>
            <div className="truncate">{gr.supplier_name}</div>
            <div className="mt-1 flex justify-between gap-2 text-sm text-muted">
              <span>
                {formatDate(gr.created_at)} · {gr.created_by_name}
              </span>
              {isAdmin && <span className="num font-semibold text-ink">{formatMoney(gr.cost_total)}</span>}
            </div>
            {gr.supplier_invoice_no && <div className="text-sm text-muted">ใบกำกับ {gr.supplier_invoice_no}</div>}
          </>
        )}
        columns={[
          { label: "เลขที่", render: (gr) => gr.display_number },
          { label: "วันที่", render: (gr) => formatDate(gr.created_at) },
          { label: "ร้าน", render: (gr) => gr.supplier_name },
          { label: "อ้าง PO", render: (gr) => <SourceBadge gr={gr} /> },
          { label: "ใบกำกับภาษี", render: (gr) => gr.supplier_invoice_no || "-" },
          { label: "ผู้บันทึก", render: (gr) => gr.created_by_name },
          ...(isAdmin
            ? [
                { label: "ต้นทุนรวม", align: "right", render: (gr) => formatMoney(gr.cost_total) },
                { label: "ภาษีซื้อ", align: "right", render: (gr) => formatMoney(gr.vat_total) },
              ]
            : []),
        ]}
      />
    </ListLayout>
  );
}
```

- `SourceBadge` ใช้สองที่ (การ์ด + ตาราง): อ้าง PO → เลข PO · ไม่อ้าง → "ซื้อด่วน"
- บอกช่างตรง ๆ ว่าเห็นแค่ของตัวเอง ไม่งั้นหาใบเพื่อนไม่เจอแล้วคิดว่าระบบพัง (การกรองจริงอยู่ที่ backend)
- ไม่มีแท็บสถานะ เพราะใบรับของไม่มีสถานะ · ปุ่มบันทึกรับของทุกบทบาทเห็น

## 12. `pages/GoodsReceiptFormPage.jsx` — ฟอร์มที่ซับซ้อนที่สุดของเฟส

```
โหมด "ตาม PO"  → เลือก PO → เติมชื่อร้าน + รายการค้างรับให้เอง
โหมด "ซื้อด่วน" → กรอกชื่อร้านเอง ค้นสินค้าเอง
```

```jsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate, useOutletContext, useSearchParams } from "react-router-dom";
import { api, formatMoney, formatQty, formatUnitPrice, plainNumber, todayBangkok } from "../api";
import Field from "../components/Field";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import ProductSearch from "../components/ProductSearch";

const MODES = [
  ["po", "ตาม PO"],
  ["quick", "ซื้อด่วน"],
];
const EMPTY_RECEIPT = {
  supplier_name: "",
  supplier_tax_id: "",
  supplier_invoice_no: "",
  supplier_invoice_date: todayBangkok(),
  has_invoice: false,
  items: [], // แต่ละแถว { product_id, label, remaining?, qty, total_paid, vat_amount }
};
const EMPTY_ITEM = { qty: "", total_paid: "", vat_amount: "" };
const round2 = (x) => Math.round(x * 100) / 100;

// popup /goods-receipts/new: รับของตาม PO (เติมรายการค้างรับให้) หรือซื้อด่วน, โชว์ VAT/ต้นทุนสด ๆ → POST /goods-receipts
export default function GoodsReceiptFormPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { close } = useOutletContext();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState(params.get("po") ? "po" : "quick");
  const [poId, setPoId] = useState(params.get("po") || "");
  const openPos = useQuery({
    queryKey: ["purchase-orders", { status: "open" }],
    queryFn: () => api("/purchase-orders?status=open"),
    enabled: mode === "po",
  });
  const po = useQuery({ queryKey: ["purchase-orders", poId], enabled: mode === "po" && !!poId });
  const settings = useQuery({ queryKey: ["settings"] });
  const rate = Number(settings.data?.vat_rate ?? 7);

  const { register, handleSubmit, control, watch, setValue } = useForm({ defaultValues: EMPTY_RECEIPT });
  const { fields, append, remove, replace } = useFieldArray({ control, name: "items" });
  const items = watch("items");
  const hasInvoice = watch("has_invoice");

  // เลือก PO แล้ว: เติมชื่อร้าน + รายการที่ยังค้างรับ โดยตั้งจำนวนเท่ายอดค้างไว้ให้
  useEffect(() => {
    if (mode !== "po" || !po.data) return;
    setValue("supplier_name", po.data.supplier_name);
    setValue("supplier_tax_id", po.data.supplier_tax_id || "");
    replace(
      po.data.items
        .filter((i) => Number(i.qty_remaining) > 0)
        .map((i) => ({
          ...EMPTY_ITEM,
          product_id: i.product_id,
          label: `${i.product_code} — ${i.product_name} (${i.unit})`,
          remaining: i.qty_remaining,
          qty: plainNumber(i.qty_remaining),
        })),
    );
  }, [mode, po.data, setValue, replace]);

  // สลับโหมด: ล้าง PO ที่เลือกและรายการทิ้ง ไม่ให้ของสองโหมดปนกัน
  const switchMode = (next) => {
    setMode(next);
    setPoId("");
    replace([]);
  };
  // ซื้อด่วน: แตะสินค้าที่มีในรายการแล้ว ไม่เพิ่มซ้ำ
  const addProduct = (p) => {
    if (!items.some((it) => it.product_id === p.id)) {
      append({ ...EMPTY_ITEM, product_id: p.id, label: `${p.code} — ${p.name} (${p.unit})` });
    }
  };

  // ตัวเลขข้างล่างไว้โชว์ระหว่างกรอกเท่านั้น backend คิดใหม่ด้วย Decimal
  const autoVat = (it) =>
    round2(Number(it.total_paid || 0) - round2((Number(it.total_paid || 0) * 100) / (100 + rate)));
  const vatOf = (it) => {
    if (!hasInvoice) return 0;
    return it.vat_amount !== "" ? Number(it.vat_amount) : autoVat(it); // เว้นว่าง = ให้ระบบคิด
  };
  const unitCost = (it) => (Number(it.qty) > 0 ? (Number(it.total_paid || 0) - vatOf(it)) / Number(it.qty) : 0);
  const totalPaid = items.reduce((sum, it) => sum + Number(it.total_paid || 0), 0);
  const totalVat = items.reduce((sum, it) => sum + vatOf(it), 0);

  const save = useMutation({
    mutationFn: (form) =>
      api("/goods-receipts", {
        method: "POST",
        body: {
          po_id: mode === "po" && poId ? Number(poId) : null,
          supplier_name: form.supplier_name,
          supplier_tax_id: form.has_invoice ? form.supplier_tax_id : null,
          supplier_invoice_no: form.has_invoice ? form.supplier_invoice_no : null,
          supplier_invoice_date: form.has_invoice ? form.supplier_invoice_date : null,
          items: form.items.map((it) => ({
            product_id: it.product_id,
            qty: it.qty,
            total_paid: it.total_paid,
            vat_amount: form.has_invoice && it.vat_amount !== "" ? it.vat_amount : null,
          })),
        },
      }),
    onSuccess: (gr) => {
      // รับของแล้วเปลี่ยนสามเรื่อง: ใบรับของ · ยอดรับของ PO · สต็อก
      for (const group of ["goods-receipts", "purchase-orders", "products"]) {
        queryClient.invalidateQueries({ queryKey: [group] });
      }
      navigate(`/goods-receipts/${gr.id}`);
    },
  });

  return (
    <Modal
      title="บันทึกรับของ"
      onClose={close}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {save.error && (
            <p role="alert" className="field-error mb-2">
              {save.error.message}
            </p>
          )}
          <div className="flex items-center gap-3">
            <div className="mr-auto text-sm">
              <div className="text-muted">ยอดจ่ายรวม{hasInvoice && ` · VAT ${formatMoney(totalVat)}`}</div>
              <div className="num text-lg font-bold">{formatMoney(totalPaid)}</div>
            </div>
            <button className="btn btn-primary" disabled={save.isPending || fields.length === 0}>
              {save.isPending ? "กำลังบันทึก…" : "บันทึกรับของ"}
            </button>
          </div>
          <p className="mt-1 text-xs text-muted">บันทึกแล้วแก้ไม่ได้ รับเกินให้แจ้งของเสีย/สูญหาย รับขาดให้รับเพิ่มอีกใบ</p>
        </>
      }
    >
      <section className="space-y-3">
        <div role="group" aria-label="ที่มาของสินค้า" className="grid grid-cols-2 gap-2">
          {MODES.map(([key, label]) => (
            <button
              key={key}
              type="button"
              aria-pressed={mode === key}
              onClick={() => switchMode(key)}
              className={`chip justify-center ${mode === key ? "chip-on" : ""}`}
            >
              {label}
            </button>
          ))}
        </div>
        {mode === "po" && (
          <label className="block">
            <span className="label">ใบสั่งซื้อที่เปิดอยู่</span>
            <select className="input" required value={poId} onChange={(e) => setPoId(e.target.value)}>
              <option value="">— เลือกใบสั่งซื้อ —</option>
              {openPos.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_number} — {p.supplier_name}
                </option>
              ))}
            </select>
          </label>
        )}
        <Field label="ชื่อร้าน" required {...register("supplier_name")} />
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">รายการที่รับ</h3>
        {mode === "po" && !poId && <p className="text-muted">เลือกใบสั่งซื้อก่อน</p>}
        {mode === "po" && po.data && fields.length === 0 && <p className="text-muted">ใบสั่งซื้อนี้ไม่มียอดค้างรับ</p>}
        {fields.map((field, i) => (
          <div key={field.id} className="space-y-3 rounded-lg border border-line p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="font-semibold">{field.label}</div>
                {field.remaining && <div className="text-sm text-muted">ค้างรับ {formatQty(field.remaining)}</div>}
              </div>
              {(mode === "quick" || fields.length > 1) && (
                <button
                  type="button"
                  aria-label={`ลบรายการที่ ${i + 1}`}
                  className="btn btn-ghost btn-icon text-muted hover:text-danger"
                  onClick={() => remove(i)}
                >
                  <Icon name="close" size={18} />
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field
                label="จำนวน"
                type="number"
                inputMode="decimal"
                step="0.001"
                min="0.001"
                max={field.remaining}
                required
                {...register(`items.${i}.qty`)}
              />
              <Field
                label="ยอดที่จ่ายจริง (บาท)"
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                required
                {...register(`items.${i}.total_paid`)}
              />
            </div>
            {hasInvoice && (
              <Field
                label="VAT"
                hint={`เว้นว่าง = คิดอัตโนมัติ ${rate}/${100 + rate}`}
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                placeholder={formatMoney(autoVat(items[i]))}
                {...register(`items.${i}.vat_amount`)}
              />
            )}
            <div className="flex justify-between rounded-lg bg-surface px-3 py-2 text-sm">
              <span className="text-muted">ต้นทุน/หน่วย</span>
              <span className="num font-semibold">{formatUnitPrice(unitCost(items[i]))}</span>
            </div>
          </div>
        ))}
        {mode === "quick" && <ProductSearch onPick={addProduct} />}
      </section>

      <section className="space-y-3">
        <label className="flex min-h-11 cursor-pointer items-center gap-3">
          <input type="checkbox" role="switch" className="size-5 accent-accent" {...register("has_invoice")} />
          ร้านออกใบกำกับภาษีให้ (แยก VAT ออกจากต้นทุน)
        </label>
        {hasInvoice && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label="เลขที่ใบกำกับภาษี"
              required
              autoCapitalize="characters"
              {...register("supplier_invoice_no")}
            />
            <Field label="วันที่ใบกำกับภาษี" type="date" required {...register("supplier_invoice_date")} />
            <Field
              label="เลขผู้เสียภาษีร้าน"
              hint="จำเป็นเมื่อมีใบกำกับภาษี"
              required
              inputMode="numeric"
              className="sm:col-span-2"
              {...register("supplier_tax_id")}
            />
          </div>
        )}
      </section>
    </Modal>
  );
}
```

- โหมดเริ่มจาก URL: มี `?po=` → "ตาม PO" พร้อมเลือกใบนั้น
- `useQuery` สามตัวคุมด้วย `enabled`: รายการ PO (เฉพาะโหมด PO) · PO ที่เลือก (เมื่อเลือกแล้ว) · ค่าตั้ง (อัตรา VAT)
- `useEffect` เลือก PO แล้วเติมให้: `setValue` ตั้งช่องเดียว · `replace` แทนรายการทั้งชุด · จำนวนตั้งเท่ายอดค้าง (กรณีปกติคือของมาครบ กรอกแค่ยอดเงิน)
- แถวเก็บ `product_id` `label` `remaining` ไว้ด้วย (โชว์/ส่ง) ช่องที่กรอกจริงมีแค่ `qty` `total_paid` `vat_amount`
- VAT / ต้นทุนต่อหน่วยคิดด้วย JS **เพื่อโชว์เท่านั้น** (จับพิมพ์ผิดได้ทันที เช่นต้นทุนกลายเป็นชิ้นละ 2,140) — ส่งแค่ยอดจ่าย จำนวน VAT ที่กรอกเอง ให้ backend คิดใหม่
- ปิดสวิตช์ใบกำกับ → ส่ง `null` ทั้งชุด ไม่งั้นส่งครึ่ง ๆ ไปชน CHECK
- บันทึกแล้ว invalidate สามกลุ่ม: ใบรับของใหม่ · ยอดรับของ PO · สต็อก/Lot
- เตือน "บันทึกแล้วแก้ไม่ได้" ไว้ก่อนปุ่ม

## 13. `pages/GoodsReceiptDetailPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { formatDate, formatMoney, formatQty, formatUnitPrice } from "../api";
import { useAuth } from "../auth";
import DetailLayout from "../components/DetailLayout";
import Icon from "../components/Icon";
import StatusBadge from "../components/StatusBadge";

// หน้า /goods-receipts/:id: อ่านอย่างเดียว (บันทึกแล้วแก้ไม่ได้), ต้นทุน/VAT โชว์เฉพาะ admin
export default function GoodsReceiptDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const { data: gr, error } = useQuery({ queryKey: ["goods-receipts", id] });

  if (!gr) {
    return <DetailLayout back="/goods-receipts" backLabel="รับของ" title={error?.message || "กำลังโหลด…"} />;
  }

  const info = [
    ["เลขผู้เสียภาษีร้าน", gr.supplier_tax_id],
    ["ใบกำกับภาษี", gr.supplier_invoice_no && `${gr.supplier_invoice_no} (${formatDate(gr.supplier_invoice_date)})`],
    ["ผู้บันทึก", `${gr.created_by_name} · ${formatDate(gr.created_at)}`],
  ];

  return (
    <DetailLayout
      back="/goods-receipts"
      backLabel="รับของ"
      title={gr.display_number}
      subtitle={gr.supplier_name}
      badge={gr.po_id ? <span className="badge badge-info">{gr.po_number}</span> : <StatusBadge status="quick" />}
      footer={
        gr.po_id && (
          <Link to={`/purchase-orders/${gr.po_id}`} className="btn btn-secondary w-full">
            <Icon name="clipboard" size={20} />
            ดูใบสั่งซื้อ {gr.po_number}
          </Link>
        )
      }
    >
      <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        {info
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <div key={label}>
              <dt className="text-muted">{label}</dt>
              <dd className="font-medium">{value}</dd>
            </div>
          ))}
      </dl>
      <ul className="divide-y divide-line rounded-xl border border-line">
        {gr.items.map((it) => (
          <li key={it.product_id} className="px-4 py-3">
            <div className="flex justify-between gap-2">
              <span className="font-semibold">{it.product_name}</span>
              <span className="num font-semibold">
                {formatQty(it.qty)} {it.unit}
              </span>
            </div>
            <div className="text-sm text-muted">{it.product_code}</div>
            {isAdmin && (
              <div className="num text-sm">
                ต้นทุน/หน่วย {formatUnitPrice(it.unit_cost)} · รวม {formatMoney(it.cost_total)} · VAT{" "}
                {formatMoney(it.vat_amount)}
              </div>
            )}
          </li>
        ))}
      </ul>
      {isAdmin && (
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <Total label="ต้นทุนรวม" value={gr.cost_total} />
          <Total label="ภาษีซื้อ" value={gr.vat_total} />
        </dl>
      )}
    </DetailLayout>
  );
}

// กล่องยอดรวมตัวใหญ่ หัวข้อ + เงิน
function Total({ label, value }) {
  return (
    <div className="rounded-lg bg-surface p-2">
      <dt className="text-muted">{label}</dt>
      <dd className="num text-lg font-bold">{formatMoney(value)}</dd>
    </div>
  );
}
```

- ไม่มีปุ่มแก้ / ลบ / เมนู ⋯ — เอกสารบันทึกแล้วแก้ไม่ได้ ปุ่มเดียวคือกลับไปดู PO
- ช่างเปิดใบคนอื่น → backend 404 → หัวหน้าแสดง "ไม่พบใบรับของ"

## 14. `pages/PurchaseOrderPrintPage.jsx` — หน้าพิมพ์ A4

```jsx
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { formatDate, formatMoney, formatQty } from "../api";
import Icon from "../components/Icon";

// หน้า A4 /print/po/:id สำหรับพิมพ์หรือบันทึก PDF: GET PO + ค่าตั้งอู่ (หัวกระดาษ), แถบปุ่มซ่อนตอนพิมพ์ด้วย print:hidden
export default function PurchaseOrderPrintPage() {
  const { id } = useParams();
  const { data: po, error } = useQuery({ queryKey: ["purchase-orders", id] });
  const { data: shop } = useQuery({ queryKey: ["settings"] });
  // เปิดจากในเว็บ → กลับหน้าเดิม · เปิดแท็บใหม่ → ปิดแท็บ
  const closePage = () => (history.length > 1 ? history.back() : window.close());

  return (
    <div className="min-h-dvh bg-surface print:bg-white">
      <div className="sticky top-0 z-10 flex items-center justify-end gap-2 border-b border-line bg-white p-2 print:hidden">
        <button type="button" className="btn btn-secondary" onClick={closePage}>
          ปิด
        </button>
        <button type="button" className="btn btn-primary" onClick={() => window.print()} disabled={!po}>
          <Icon name="printer" size={20} />
          พิมพ์ / บันทึก PDF
        </button>
      </div>
      <article className="mx-auto my-4 max-w-[210mm] bg-white p-6 text-sm shadow-sm md:p-10 print:m-0 print:max-w-none print:p-0 print:shadow-none">
        {error ? (
          <p role="alert" className="field-error">
            {error.message}
          </p>
        ) : !po ? (
          <p className="text-muted">กำลังโหลด…</p>
        ) : (
          <PoDocument po={po} shop={shop} />
        )}
      </article>
    </div>
  );
}

// เนื้อเอกสาร: หัวอู่ · ผู้ขาย · ตารางรายการ · หมายเหตุ · ช่องเซ็น
function PoDocument({ po, shop }) {
  const hasPrice = (it) => it.unit_price != null;
  const supplierLines = [
    po.supplier_name,
    po.supplier_address,
    po.supplier_phone && `โทร ${po.supplier_phone}`,
    po.supplier_tax_id && `เลขประจำตัวผู้เสียภาษี ${po.supplier_tax_id}`,
  ].filter(Boolean);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap justify-between gap-4 border-b-2 border-ink pb-4">
        <div className="min-w-0">
          <div className="text-lg font-bold">{shop?.shop_name || "ชื่ออู่ (ตั้งค่าได้ในหน้าตั้งค่า)"}</div>
          {shop?.shop_address && <div className="whitespace-pre-line">{shop.shop_address}</div>}
          {shop?.shop_tax_id && <div>เลขประจำตัวผู้เสียภาษี {shop.shop_tax_id}</div>}
        </div>
        <div className="text-right">
          <div className="text-xl font-bold">ใบสั่งซื้อ</div>
          <div>เลขที่ {po.display_number}</div>
          <div>วันที่ {formatDate(po.created_at)}</div>
        </div>
      </header>

      <div>
        <div className="font-semibold">ผู้ขาย</div>
        {supplierLines.map((line, i) => (
          <div key={i} className="whitespace-pre-line">
            {line}
          </div>
        ))}
      </div>

      <table className="w-full border-collapse">
        <thead>
          <tr className="border-y border-ink text-left">
            <th className="px-2 py-1.5">ลำดับ</th>
            <th className="px-2 py-1.5">รหัส</th>
            <th className="px-2 py-1.5">รายการ</th>
            <th className="px-2 py-1.5 text-right">จำนวน</th>
            <th className="px-2 py-1.5">หน่วย</th>
            <th className="px-2 py-1.5 text-right">ราคา/หน่วย</th>
            <th className="px-2 py-1.5 text-right">จำนวนเงิน</th>
          </tr>
        </thead>
        <tbody>
          {po.items.map((it, i) => (
            <tr key={it.product_id} className="border-b border-line">
              <td className="px-2 py-1.5">{i + 1}</td>
              <td className="px-2 py-1.5">{it.product_code}</td>
              <td className="px-2 py-1.5">{it.product_name}</td>
              <td className="num px-2 py-1.5 text-right">{formatQty(it.qty)}</td>
              <td className="px-2 py-1.5">{it.unit}</td>
              <td className="num px-2 py-1.5 text-right">{hasPrice(it) ? formatMoney(it.unit_price) : "-"}</td>
              <td className="num px-2 py-1.5 text-right">
                {hasPrice(it) ? formatMoney(Number(it.qty) * Number(it.unit_price)) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-ink text-base font-bold">
            <td colSpan={6} className="px-2 py-1 text-right">
              ยอดประมาณการ (รวม VAT)
            </td>
            <td className="num px-2 py-1 text-right">{formatMoney(po.estimated_total)}</td>
          </tr>
        </tfoot>
      </table>

      {po.note && (
        <div>
          <div className="font-semibold">หมายเหตุ</div>
          <div className="whitespace-pre-line">{po.note}</div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8 pt-12 break-inside-avoid">
        {["ผู้สั่งซื้อ", "ผู้อนุมัติ"].map((label) => (
          <div key={label} className="text-center">
            <div className="border-b border-ink pb-8" />
            <div className="pt-1">{label}</div>
            <div className="text-muted">วันที่ ........../........../..........</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- ไม่ต้องมีไลบรารี PDF: `window.print()` แล้วเลือกเครื่องพิมพ์ หรือ "Save as PDF"
- `print:hidden` / `print:bg-white` ฯลฯ มีผลเฉพาะตอนพิมพ์ ไฟล์เดียวใช้ทั้งดูบนจอและพิมพ์
- `max-w-[210mm]` บนจอเห็นเท่ากระดาษ A4 จริง · `break-inside-avoid` กันช่องเซ็นขาดข้ามหน้า
- หัวกระดาษอ่านชื่ออู่จาก `/settings` ยังไม่ตั้งก็บอกว่าไปตั้งที่ไหน
- ยังไม่แยก `PrintLayout` เพราะมีหน้าพิมพ์หน้าเดียว (เฟส 5 มีหน้าที่สองค่อยแยก)

## 15. เมนูและ route

`components/AppLayout.jsx` — เติมใน `MENU` (กลุ่ม `"คลังสินค้า"` มีแล้ว)

```jsx
const MENU = [
  { to: "/stock", label: "สต็อก", icon: "box", group: "คลังสินค้า" },
  { to: "/purchase-orders", label: "สั่งซื้อ", icon: "clipboard", group: "คลังสินค้า" },
  { to: "/goods-receipts", label: "รับของ", icon: "truck", group: "คลังสินค้า" },
];
```

`main.jsx` — เติม import

```jsx
import GoodsReceiptDetailPage from "./pages/GoodsReceiptDetailPage";
import GoodsReceiptFormPage from "./pages/GoodsReceiptFormPage";
import GoodsReceiptListPage from "./pages/GoodsReceiptListPage";
import PurchaseOrderDetailPage from "./pages/PurchaseOrderDetailPage";
import PurchaseOrderFormPage from "./pages/PurchaseOrderFormPage";
import PurchaseOrderListPage from "./pages/PurchaseOrderListPage";
import PurchaseOrderPrintPage from "./pages/PurchaseOrderPrintPage";
```

หน้าพิมพ์อยู่**นอก** AppLayout (กระดาษต้องมีแต่เอกสาร) เติมใต้ route `/login`

```jsx
          <Route
            path="/print/po/:id"
            element={
              <Guard roles={STAFF}>
                <PurchaseOrderPrintPage />
              </Guard>
            }
          />
```

ที่เหลือเติม**ใน** layout route ใต้ `stock/:id`

```jsx
            <Route path="purchase-orders" element={<PurchaseOrderListPage />}>
              <Route
                path="new"
                element={
                  <Guard roles={STAFF}>
                    <PurchaseOrderFormPage />
                  </Guard>
                }
              />
            </Route>
            <Route path="purchase-orders/:id" element={<PurchaseOrderDetailPage />} />
            <Route path="goods-receipts" element={<GoodsReceiptListPage />}>
              <Route path="new" element={<GoodsReceiptFormPage />} />
            </Route>
            <Route path="goods-receipts/:id" element={<GoodsReceiptDetailPage />} />
```

- รูปแบบเดียวกับเฟส 3: `xxx` รายการ → ลูก `xxx/new` ป๊อปอัพ · `xxx/:id` หน้ารายละเอียด
- สร้าง PO ครอบ `Guard roles={STAFF}` · รับของไม่ครอบ (ทุกบทบาท) — ตรงกับสิทธิ์ backend

---

## เช็คว่าเสร็จ

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

**เดินเรื่องจริงของ PO หนึ่งใบ**
1. สร้าง PO ผ้าเบรก 10 ชุด ราคาคาด 350 → ป้าย "รอของ"
2. ⋯ → พิมพ์ → A4 มีชื่ออู่ · Ctrl+P ต้องไม่เห็นแถบปุ่ม
3. "รับของตาม PO นี้" → จำนวนเติมเป็น 10 → แก้เป็น 6 จ่าย 2,100 → PO เป็น "รับบางส่วน" ค้าง 4 · หน้าสต็อกมี Lot "รับของ GR-0000x" ต้นทุน 350
4. รับ 5 → เบราว์เซอร์เตือน · ยิง API ตรงได้ 409 พร้อมยอดค้าง · รับ 4 → PO "ปิดแล้ว" เอง
5. ทุกหน้าอัปเดตเองโดยไม่ต้อง F5 · ลบแถวกลางในฟอร์ม PO แล้วค่าที่พิมพ์ไม่สลับ

**VAT** ซื้อด่วน 4 ขวด จ่าย 856 มีใบกำกับ `iv-001` → VAT 56.00 · ต้นทุน/หน่วย 200.0000 · เก็บเป็น `IV-001` · บันทึกซ้ำ → "ใบกำกับภาษีเลขนี้ของร้านนี้ถูกบันทึกแล้ว"

**เมนู ⋯** รอของ → มีแค่ "ยกเลิก" (แดง) · รับบางส่วน → มีแค่ "ปิดก่อนรับครบ" · ปิด/ยกเลิกแล้ว → ไม่มีทั้งคู่

**สิทธิ์** พนักงาน: ออก PO ได้ เห็นราคาคาด ไม่เห็นต้นทุน/VAT ใบรับของ · ช่าง: ไม่มีปุ่มสร้าง PO · ไม่เห็นราคาคาด · บันทึกซื้อด่วนได้ · เห็นแค่ใบตัวเอง · เดา URL ใบคนอื่น → "ไม่พบใบรับของ"

**มือถือ** ☰ เห็น สต็อก · สั่งซื้อ · รับของ · ฟอร์มรับของเลื่อนได้ ปุ่มบันทึกอยู่ล่างเสมอ

## git

```
docker compose run --rm api ruff check --fix .
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A && git commit -m "feat: purchase orders and goods receipts"
```
