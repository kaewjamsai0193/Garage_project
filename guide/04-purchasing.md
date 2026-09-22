# เฟส 4 — ใบสั่งซื้อ และรับของเข้าคลัง

**จบเฟสนี้แล้วจะทำอะไรได้**

- ออกใบสั่งซื้อ (PO) แล้วพิมพ์ส่งร้านได้
- รับของทยอยเข้ามาตาม PO (ไม่ต้องรับครบทีเดียว)
- ซื้อด่วนที่ไม่มี PO ก็บันทึกได้
- แยก VAT ซื้อออกจากต้นทุน เมื่อร้านออกใบกำกับภาษี
- **ของที่รับโผล่ในสต็อกเป็น Lot ใหม่พร้อมต้นทุนจริง**
- PO ปิดตัวเองอัตโนมัติเมื่อรับของครบ

**อ่านก่อนเริ่ม** `new_scenario_summary.md` หัวข้อ 3 · `data_model.md` หัวข้อ 4 ·
กรณีตรวจรับข้อ 3, 13, 14, 15

**เฟสนี้ยังไม่ทำ** รายงานภาษีซื้อ — เฟส 9 จะอ่านจาก `vat_amount` ที่เฟสนี้เก็บไว้

---

## เฟสนี้ข้อมูลเดินยังไง (อ่าน 1 นาที)

```
① สั่งของ: ออกใบสั่งซื้อ (PO) ส่งร้าน — ยังไม่มีของเข้าคลัง สต็อกยังไม่ขยับ
   ↓ พิมพ์ใบส่งร้านได้จากหน้า PO
② ของมาถึง: บันทึกใบรับของ (GR) อ้าง PO ใบนั้น หรือ "ซื้อด่วน" ที่ไม่มี PO
   ↓ backend ทำสามอย่างในคำสั่งเดียว
   - สร้าง Lot ใหม่ในคลัง (ต้นทุนต่อหน่วย = ยอดที่จ่ายจริง − VAT ÷ จำนวน)
   - จดสมุดสต็อกว่า "รับของ +4 จากใบ GR-00003"
   - บวกยอดรับของ PO ถ้ารับครบแล้ว PO ปิดตัวเอง
```

- **เพิ่มอะไรในฐาน** ตารางใบสั่งซื้อ + รายการในใบ + ใบรับของ และเติมคอลัมน์ใน Lot ว่ามาจากใบรับของไหน
- **ยอดในใบสั่งซื้อเป็นแค่ราคาคาดการณ์** ต้นทุนจริงคือยอดที่จ่ายตอนรับของ
- **VAT ซื้อ** ร้านออกใบกำกับให้ → แยก VAT ออกจากต้นทุน (ไม่งั้นต้นทุนจะบวมและภาษีซื้อขอคืนไม่ได้)
- **ใบรับของบันทึกแล้วแก้ไม่ได้** กรอกผิดให้ไปปรับสต็อกพร้อมเหตุผล เพื่อให้เหลือร่องรอย

## กฎที่ต้องเข้าใจก่อนเขียน

**อ่านให้เข้าใจก่อนพิมพ์โค้ด** เฟสนี้มีกฎธุรกิจเยอะที่สุดในบรรดาทุกเฟส

**1. ไม่มีตารางทะเบียนร้านค้า**

ชื่อร้าน เบอร์โทร เลขผู้เสียภาษี — **กรอกสดลงบนใบสั่งซื้อและใบรับของทุกครั้ง**

ฟังดูเหมือนงานซ้ำ แต่อู่เดียวซื้อจากร้านไม่กี่เจ้า ตารางผู้ขายที่ต้องมีหน้า
จัดการ หน้าแก้ไข และกฎว่าลบได้ไหม **ไม่คุ้มกับที่ประหยัดไป**

**2. ราคาบน PO เป็นแค่ราคาคาด — ต้นทุนจริงเกิดตอนรับของ**

ตอนสั่งอาจคาดว่าชิ้นละ 100 แต่พอของมาจริงบิลอาจเป็น 105 (ราคาขึ้น)
**ระบบยึดราคาบนใบรับของเสมอ**

**3. รับของทุกครั้ง = Lot ใหม่เสมอ (สินค้าละ 1 Lot ต่อใบรับของ)**

นี่คือเหตุผลทั้งหมดที่ระบบบอกต้นทุนจริงได้ — ต่อยอดจากแนวคิด Lot ในเฟส 3

**4. ยอดที่รับไปแล้ว นับจาก Lot จริง ไม่เก็บเป็นตัวเลขบน PO**

หลักการเดียวกับ `qty_on_hand` ในเฟส 3 — **ไม่เก็บซ้ำในสองที่**

**5. รับของแล้วแก้ไม่ได้**

กรอกผิดให้ไปปรับสต็อกแทน (ปุ่มปรับลดจากเฟส 3)
**เอกสารที่บันทึกแล้วห้ามแก้ — กฎของทั้งระบบ**

**6. ช่างรับของได้ แต่ออก PO ไม่ได้**

เพราะช่างขับไปซื้อของด่วนจากร้านข้างอู่จริง ๆ แต่ช่างจะเห็น**เฉพาะใบรับของ
ที่ตัวเองบันทึก** และ**ไม่เห็นราคา**

### สถานะ PO

```
เปิดอยู่ ──รับครบทุกรายการ──────────────────────────────> ปิดแล้ว (ระบบปิดเอง)
   │   └─ปิดก่อนครบ (ต้องมีเหตุผล · เฉพาะใบที่เคยรับของแล้ว)──> ปิดแล้ว
   └─ยกเลิก (เฉพาะใบที่ยังไม่เคยรับของเลย · ต้องมีเหตุผล)────> ยกเลิก
```

**สถานะในฐานมีแค่ 3 ตัว: `open` · `closed` · `cancelled`**

แต่บนหน้าจอผู้ใช้จะเห็นคำว่า **"รอของ"** กับ **"รับบางส่วน"** ด้วย —
สองคำนี้**ไม่ใช่สถานะในฐาน** เป็นคำที่คำนวณสด ๆ จากยอดที่รับไปแล้ว (`receive_state`)

```
สถานะ open + ยังไม่เคยรับเลย      → แสดงว่า "รอของ"
สถานะ open + รับไปบ้างแล้ว        → แสดงว่า "รับบางส่วน"
```

**ทำไมไม่เก็บเป็นสถานะจริง** — ต้องคอยอัปเดตทุกครั้งที่รับของ
แล้ววันหนึ่งจะมีเคสที่ลืมอัปเดต จนสถานะไม่ตรงกับความจริง
(หลักการเดียวกับ `productStatus` ในเฟส 3)

### VAT ซื้อ

อู่ซื้อของจากสองแบบร้าน ระบบต้องรองรับทั้งคู่:

| ร้านออกใบกำกับภาษีไหม | ทำยังไง |
|---|---|
| **ออก** | กรอกเลขผู้เสียภาษีร้าน + เลขที่ + วันที่ใบกำกับ<br>**ถอด VAT ออก** (เริ่มต้น 7/107 แก้ได้)<br>**ต้นทุนของ = ยอดจ่าย − VAT**<br>เก็บ VAT ไว้ทำรายงานภาษีซื้อ (เฟส 9) |
| **ไม่ออก** | ต้นทุนของ = ยอดจ่ายทั้งก้อน · VAT = 0 |

**ทำไมต้องถอด VAT ออกจากต้นทุน** — เพราะ VAT ที่จ่ายไปขอคืนได้
มันไม่ใช่ต้นทุนของของจริง ๆ ถ้าไม่ถอดออก ต้นทุนจะสูงเกินจริง 7%
แล้วกำไรที่คำนวณได้ก็ผิดตามไปหมด

**ใบกำกับหนึ่งใบบันทึกซ้ำไม่ได้** (คู่ เลขผู้เสียภาษี + เลขที่ใบกำกับ)
— บังคับที่ฐานด้วย **partial unique index** (ข้อ 1 จะอธิบายว่าคืออะไร)

---

# ส่วน backend

## 1. `app/models.py` — ตารางใหม่ 3 ตัว + แก้ตาราง Lot และสมุดสต็อก

### import

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func, select, text,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship
```

### ตารางใหม่ — วางก่อน `class StockLot`

`StockLot` จะอ้าง `goods_receipts` เลยวางไว้ก่อนให้อ่านง่าย (SQLAlchemy เองไม่สนลำดับ)

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

### อ่านโค้ดนี้ยังไง

**`CHECK (closed_at is null) = (status = 'open')` — รูปแบบที่จะเจอบ่อยมาก**

อ่านเครื่องหมาย `=` ตรงกลางว่า **"สองข้างนี้ต้องจริงหรือเท็จพร้อมกัน"**

| status | closed_at | ผ่านไหม |
|---|---|---|
| `open` | ว่าง | ✅ เปิดอยู่ ยังไม่มีเวลาปิด สมเหตุสมผล |
| `closed` | มีค่า | ✅ ปิดแล้ว มีเวลาปิด สมเหตุสมผล |
| `closed` | ว่าง | ❌ ปิดแล้วแต่ไม่รู้ปิดเมื่อไหร่ |
| `open` | มีค่า | ❌ ยังเปิดอยู่แต่มีเวลาปิด |

**สองสถานะที่ขัดแย้งกันเองเกิดขึ้นไม่ได้เลยในระดับฐานข้อมูล**
เขียน CHECK แบบนี้แล้วไม่ต้องไปเขียน `if` ป้องกันในโค้ดทุกที่

**`CHECK status <> 'cancelled' or close_reason is not null`**

อ่านว่า "ถ้าไม่ใช่สถานะยกเลิก ก็ผ่าน · ถ้าใช่ ต้องมีเหตุผล"

ทำไมบังคับแค่กรณียกเลิก — เพราะ **PO ที่ปิดเพราะรับของครบไม่ต้องมีเหตุผล**
(ระบบปิดให้เอง) ส่วนกรณี "ปิดก่อนรับครบ" ที่ต้องมีเหตุผทเหมือนกัน
แยกไม่ได้ที่ระดับฐาน เลยให้ service ดูแลแทน

**`UniqueConstraint("po_id", "product_id")`** — สินค้าตัวเดียวห้ามอยู่สองแถว
ในใบเดียวกัน ไม่งั้นคำถามว่า "ยอดค้างรับของสินค้านี้เท่าไหร่" ต้องไล่รวมหลายแถว
ซึ่งเปิดช่องให้คำนวณพลาด

**`unit_price` เป็น `None` ได้** — ราคาคาดไม่บังคับกรอก
เพราะหลายครั้งโทรสั่งไปก่อน แล้วค่อยรู้ราคาตอนของมา

**กฎใบกำกับภาษี — สอง CHECK ที่ทำงานคู่กัน**

```python
CheckConstraint("(supplier_invoice_no is null) = (supplier_invoice_date is null)")
# เลขที่กับวันที่ใบกำกับ ต้องมีคู่กันหรือไม่มีทั้งคู่

CheckConstraint("supplier_invoice_no is null or supplier_tax_id is not null")
# มีเลขใบกำกับ = ต้องมีเลขผู้เสียภาษีร้านด้วย
```

**`partial unique index` — index ที่บังคับเฉพาะบางแถว**

```python
Index("goods_receipts_supplier_invoice", "supplier_tax_id", "supplier_invoice_no",
      unique=True, postgresql_where=text("supplier_invoice_no is not null"))
#     ^ ห้ามซ้ำ    ^ แต่บังคับเฉพาะแถวที่มีเลขใบกำกับเท่านั้น
```

**ทำไมต้อง partial** — เราอยากให้คู่ (เลขผู้เสียภาษี + เลขที่ใบกำกับ) ไม่ซ้ำ
แต่ใบรับของที่**ไม่มี**ใบกำกับมีเยอะมาก ซึ่งทุกใบมีค่าเป็น `(null, null)` เหมือนกันหมด

ถ้าใช้ unique ธรรมดา ใบที่ไม่มีใบกำกับจะบันทึกได้แค่ใบเดียวทั้งระบบ
`postgresql_where` บอกว่า "ตรวจเฉพาะแถวที่มีเลขใบกำกับ" — แถวที่ไม่มีปล่อยผ่านหมด

**`relationship(order_by="PurchaseOrderItem.id")`** — รายการบนเอกสาร
เรียงลำดับเหมือนเดิมทุกครั้งที่เปิด ไม่ใส่แล้วลำดับอาจสลับไปมา
ซึ่งดูเหมือนเอกสารเปลี่ยนไปเอง

**`creator: relationship(foreign_keys=[created_by])` — ทำไมต้องระบุ**

`PurchaseOrder` มี FK ชี้ไปตาราง `users` **สองตัว** (`created_by` กับ `closed_by`)
SQLAlchemy เดาไม่ออกว่า `creator` หมายถึงตัวไหน ต้องบอกให้ชัด

(`GoodsReceipt` มี FK ไป users ตัวเดียว เลยไม่ต้องบอก)

### แก้ `StockLot` — Lot จากการรับของ

เพิ่มสองคอลัมน์ (ใต้ `source_type` และใต้ `cost_total`)

```python
    receipt_id: Mapped[int | None] = fk("goods_receipts.id")
```

```python
    vat_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, server_default="0")
```

แทน `__table_args__` ทั้งก้อนด้วย

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

| CHECK | เฟส 3 | เฟส 4 | ทำไม |
|---|---|---|---|
| `source_type` | `adjustment` `opening` | + `receipt` | Lot ชนิดใหม่ |
| `receipt` (ใหม่) | – | `(source_type = 'receipt') = (receipt_id is not null)` | Lot จากรับของ**ต้อง**มีใบรับของ · Lot จากการปรับ**ต้องไม่มี** |
| `adjust_vat` (ใหม่) | – | `source_type = 'receipt' or vat_amount = 0` | ปรับสต็อกไม่มี VAT ซื้อ (ไม่ได้ซื้อจากใคร) |
| `cost` | ไม่มี VAT | + `vat_amount >= 0` | |

**`UniqueConstraint("receipt_id", "product_id")`** — ใบรับของหนึ่งใบ สินค้าละ Lot เดียว
ซึ่งก็คือกฎข้อ 3 ในหัวข้อแนวคิดที่บังคับไว้ที่ฐานเลย

**CHECK ตัวที่เข้าใจยากที่สุด**

```sql
(source_type = 'receipt') = (receipt_id is not null)
```

รูปแบบ `=` ตรงกลางแบบเดียวกับ `closed_at` ข้างบน อ่านว่า:

- Lot ที่มาจากการรับของ → **ต้องมี** `receipt_id` ชี้ไปที่ใบรับของ
- Lot ที่มาจากการปรับสต็อก → **ต้องไม่มี** `receipt_id`

กัน Lot กำพร้าที่บอกว่ามาจากการรับของ แต่ชี้ไปหาใบรับของไม่ได้

### แก้ `StockMovement` — ประเภท `receive`

```python
        CheckConstraint("movement_type in ('receive','adjust','opening')", name="type"),
        CheckConstraint("(movement_type in ('receive','opening') and qty > 0) or (movement_type = 'adjust' and qty <> 0)", name="direction"),
```

## 2. migration — ต้องแก้มือ

```
docker compose run --rm api alembic revision --autogenerate -m "purchase orders and goods receipts"
```

**ขั้นนี้ต่างจาก migration ของเฟสก่อน ๆ — ครั้งนี้ต้องเขียนเพิ่มเองเยอะ**

**สิ่งที่ autogenerate ทำให้ครบแล้ว** เปิดไฟล์เช็คว่ามี:

- สร้างสามตารางใหม่
- partial index `goods_receipts_supplier_invoice` (**เช็คว่ามี `postgresql_where`** ติดมาด้วย)
- `add_column` สองคอลัมน์ใหม่ใน `stock_lots` (`receipt_id`, `vat_amount`)
- FK · unique · index บน `receipt_id`

**สิ่งที่ autogenerate มองไม่เห็นเลย: การแก้ CHECK ของตารางที่มีอยู่แล้ว**

alembic เทียบ**โครงสร้าง**ตารางได้ แต่เทียบ**เนื้อหาของ CHECK** ไม่ได้
มันเลยไม่รู้ว่าเราแก้ `ck_stock_lots_source_type` จาก 2 ค่าเป็น 3 ค่า

**ถ้าไม่เขียนเพิ่มเอง จะเกิดอะไร** — ฐานยังใช้ CHECK ของเฟส 3 อยู่
แล้วพอรับของครั้งแรก (ซึ่งสร้าง Lot ที่ `source_type = 'receipt'`) จะพังด้วย:

```
ข้อมูลขัดกับกฎของระบบ          ← ข้อความจาก IntegrityError handler เฟส 2
(ชน ck_stock_lots_source_type)
```

**นี่คือจุดที่ `naming_convention` จากเฟส 1 ได้ใช้จริง** — เพราะเรารู้ชื่อ
constraint แน่นอนว่าเป็น `ck_stock_lots_source_type` เลยสั่ง drop แล้วสร้างใหม่ได้
ถ้าปล่อยให้ Postgres ตั้งชื่อเอง ตอนนี้ต้องไปเปิดฐานหาชื่อทีละตัว

**① เติมรายการ CHECK ไว้เหนือ `def upgrade()`**

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

**② ท้าย `upgrade()`** ก่อน `# ### end Alembic commands ###` (ต้องอยู่หลัง `add_column` เพราะ CHECK ใหม่อ้าง `vat_amount` `receipt_id`)

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

**③ ต้น `downgrade()`** ใต้ `# ### commands auto generated ...` (ต้องอยู่**ก่อน** `drop_column` เพราะ CHECK ใหม่ยังอ้างคอลัมน์ที่จะถูกลบ)

```python
    # --- เติมมือ: คืน CHECK แบบเฟส 3 ---
    op.drop_constraint(op.f("ck_stock_lots_receipt"), "stock_lots", type_="check")
    op.drop_constraint(op.f("ck_stock_lots_adjust_vat"), "stock_lots", type_="check")
    for table, name, cond in CHECKS_OLD:
        op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, cond)
```

### สี่เรื่องที่ต้องเข้าใจ

**ลำดับสำคัญมาก — วางผิดที่ migration พัง**

```
upgrade():    add_column ก่อน  →  แล้วค่อยแก้ CHECK
              (เพราะ CHECK ใหม่อ้างถึง vat_amount กับ receipt_id ที่เพิ่งเพิ่ม)

downgrade():  คืน CHECK เก่าก่อน  →  แล้วค่อย drop_column
              (เพราะ CHECK ใหม่ยังอ้างคอลัมน์ที่กำลังจะถูกลบ)
```

**`op.f("ck_...")` — ลืมใส่แล้วได้ชื่อประหลาด**

บอก alembic ว่า "ชื่อนี้เป็นชื่อเต็มแล้ว อย่าเอาไปผ่าน `naming_convention` ซ้ำอีก"

```
ใส่ op.f()      → ck_stock_lots_source_type              ✅
ไม่ใส่          → ck_stock_lots_ck_stock_lots_source_type ❌
```

**Postgres แก้ CHECK ตรง ๆ ไม่ได้** ต้อง drop แล้ว create ใหม่ —
ซึ่งปลอดภัยเพราะ alembic ห่อทั้งไฟล์ไว้ในทรานแซกชันเดียวให้แล้ว
พังตรงไหนย้อนหมด ไม่มีสภาพที่ CHECK หายไปครึ่งทาง

**ข้อมูลเก่าจะไม่พัง — ตรวจแล้ว**

Lot ที่สร้างในเฟส 3 เป็น `opening` หรือ `adjustment` ซึ่ง:

- ผ่าน CHECK `source_type` ใหม่ (ค่าเดิมยังอยู่ในลิสต์)
- `vat_amount` ได้ `0` จาก `server_default` → ผ่านทั้ง `adjust_vat` และ `cost`
- `receipt_id` เป็น `null` และไม่ใช่ `receipt` → ผ่าน CHECK `receipt` ใหม่

> **ห้ามย้อนไปแก้ไฟล์ migration ของเฟส 3 เด็ดขาด**
> ฐานที่ upgrade ผ่านไปแล้วจะไม่รันไฟล์นั้นซ้ำอีก แก้ไปก็ไม่มีผล
> และจะทำให้เครื่องที่ยังไม่ upgrade ได้โครงสร้างต่างจากเครื่องที่ upgrade แล้ว
> **ต้องสร้างไฟล์ใหม่เสมอ**

### ทดสอบว่า migration ไป-กลับได้จริง

ขั้นนี้สำคัญเป็นพิเศษเพราะเราเขียนเองเยอะ — รันสามคำสั่งนี้ตามลำดับ

```
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic downgrade -1
docker compose run --rm api alembic upgrade head
docker compose exec db psql -U garage -d garage -c "\d stock_lots"      # เห็น ck_stock_lots_receipt
```

## 3. ตัวช่วยที่เติม

**ขั้นนี้ทำอะไร** เพิ่มสูตรคำนวณที่เฟสนี้ต้องใช้ — ถอด VAT · ต้นทุนต่อหน่วย ·
ยอดรวมต่อแถว และตัวช่วยจัดข้อความ

### `app/money.py` — เติมท้ายไฟล์

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

**`purchase_vat` — สูตรที่ต้องเขียนให้ถูกตั้งแต่แรก**

```python
return total_paid - round_money(total_paid * 100 / (100 + rate))
#      ยอดจ่าย    −  ฐาน(ปัดแล้ว)        =  VAT
```

สังเกตว่า **ปัดแค่ครั้งเดียวที่ "ฐาน" แล้วให้ VAT เป็นส่วนที่เหลือ**

ถ้าปัดทั้งฐานและ VAT แยกกัน จะมีบางยอดที่รวมกลับแล้วขาดหรือเกิน 1 สตางค์:

```
ยอดจ่าย 856
✅ แบบที่ใช้   ฐาน = round_money(856×100/107) = 800.00   VAT = 856 − 800.00 = 56.00   รวม 856 ✅
❌ ปัดแยก      ฐาน = 800.00   VAT = round_money(856×7/107) = 56.00                   บางยอดจะไม่ลงตัว
```

**ฐาน + VAT = ยอดจ่ายเป๊ะทุกกรณี** ซึ่งจำเป็นมากสำหรับเอกสารทางบัญชี

**`unit_cost` ใช้ `q4` เก็บ 4 ตำแหน่ง**

เหตุผลเดียวกับ `PRICE = Numeric(14,4)` ในเฟส 3 — มันมาจากการหาร

```
จ่าย 1,000 ได้ 3 ชิ้น → 333.3333  ✅
ปัดเหลือ 2 ตำแหน่ง    → 333.33 × 3 = 999.99  ❌ หายไปสตางค์นึง
```

**`line_total`** — ราคาคาด × จำนวน ของแต่ละแถวใน PO (ปัด 2 ตำแหน่งเพราะเป็นยอดเงิน)

### `tests/test_money.py` — แก้ import และเติม

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

### `app/textutil.py` — ไฟล์ใหม่

```python
import re


def digits(s):
    """เก็บเฉพาะตัวเลข (เลขผู้เสียภาษี) · ว่าง → None"""
    return re.sub(r"\D", "", s) or None if s else None
```

**ฟังก์ชันสามบรรทัดที่ทำให้กฎ "ใบกำกับห้ามซ้ำ" ใช้ได้จริง**

คนกรอกเลขผู้เสียภาษีได้หลายแบบ แต่ทั้งหมดคือร้านเดียวกัน:

```
0-1055-55555-55-5
0105555555555
0105555555555      ← ทั้งสามอันนี้ร้านเดียวกัน
```

ถ้าไม่ทำให้เป็นรูปแบบเดียวกันก่อนเก็บ (เรียกว่า normalize) **ฐานจะเห็นเป็น
คนละค่ากัน** แล้ว partial unique index ที่อุตส่าห์ทำในข้อ 1 จะจับซ้ำไม่ได้เลย

```python
re.sub(r"\D", "", s)    # \D = อะไรก็ได้ที่ไม่ใช่ตัวเลข → ลบทิ้ง
```

**`or None` ตรงท้าย** — ถ้ากรอกมาแต่ขีด (ไม่มีตัวเลขเลย) จะได้ `""`
ซึ่งเราอยากให้เป็น `None` มากกว่า เพราะ CHECK ในข้อ 1 เช็คด้วย `is null`
ไม่ได้เช็คว่าเป็นข้อความว่าง

**ทำไมอยู่ไฟล์กลางของตัวเอง** — เป็นเรื่องจัดรูปแบบข้อความล้วน ๆ
ไม่ใช่ของโดเมนไหนเป็นเจ้าของ (เฟส 5 เบอร์โทรลูกค้าก็จะใช้ตัวนี้)

### `app/schemas.py` — เติม `ReasonIn`

แก้ import เป็น `from pydantic import BaseModel, ConfigDict, Field` แล้วเติมใต้ `class Out`

```python
class ReasonIn(In):
    reason: str = Field(min_length=1)
```

ปิด PO ก่อนครบกับยกเลิก PO รับแค่เหตุผลเหมือนกัน — schema กลางตัวเดียว (เฟส 5–6 ยกเลิกใบงาน/บิลก็ใช้)

### `app/stock/service.py` — เติม `products_by_id` เหนือ `save_product`

```python
def products_by_id(db, ids, label) -> dict[int, Product]:
    if len(set(ids)) != len(ids):
        raise HTTPException(422, f"สินค้าใน{label}ซ้ำกัน")
    found = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
    if len(found) != len(ids):
        raise HTTPException(422, "ไม่พบสินค้าบางรายการ")
    return found
```

**ตรวจสองอย่างในฟังก์ชันเดียว แล้วคืนของที่จะได้ใช้ต่อ**

```python
if len(set(ids)) != len(ids):     # set ตัดตัวซ้ำทิ้ง ถ้าจำนวนลด = มีซ้ำ
    raise ... "สินค้าใน{label}ซ้ำกัน"
if len(found) != len(ids):        # หาเจอไม่ครบ = มี id ที่ไม่มีจริง
    raise ... "ไม่พบสินค้าบางรายการ"
return found                      # dict {id: Product} ไว้หาชื่อสินค้าต่อ
```

**ยิง query ครั้งเดียวด้วย `in_(ids)`** ไม่ใช่วนลูปถามทีละตัว —
เอกสาร 20 รายการจะกลายเป็น 20 query ถ้าเขียนแบบวน

**ทำไมอยู่ใน `stock/` ไม่ใช่ `purchasing/`** เพราะเป็นเรื่องของ**สินค้า**
โดเมนไหนก็ import ไปใช้ได้ (เฟส 5-6 ใบงานกับบิลจะใช้ตัวนี้เหมือนกัน)

`label` รับเข้ามาเพื่อให้ข้อความ error บอกได้ว่าซ้ำในเอกสารอะไร
("สินค้าในใบสั่งซื้อซ้ำกัน" / "สินค้าในใบรับของซ้ำกัน")

### `app/stock/` — ให้หน้าสต็อกรู้ว่า Lot มาจากใบรับของไหน

`stock/schemas.py` — `LotOut` เติม `receipt_id: int | None` ใต้ `source_type` · `LotAdminOut` เติม `vat_amount: Decimal` · `MovementOut` เติม `receipt_id: int | None` ใต้ `lot_id`

`stock/router.py` — `list_product_movements` ดึง `receipt_id` จาก Lot มาด้วย

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

`tests/test_stock.py` — บรรทัดเช็คต้นทุนหลุด เติม `vat_amount`

```python
    assert not {"unit_cost", "cost_total", "vat_amount"} & emp_lot.keys()
```

## 4. โดเมน `app/purchasing/`

**ขั้นนี้ทำอะไร** API ทั้งหมดของใบสั่งซื้อและใบรับของ — ส่วนที่ยาวที่สุดของเฟส

โครง 3 ไฟล์เหมือนทุกโดเมน (`schemas` → `service` → `router`)

**สร้างโฟลเดอร์ `backend/app/purchasing/` พร้อม `__init__.py` ว่าง**

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

**สิทธิ์เห็นราคามีสองระดับ**

| ข้อมูล | admin | employee | mechanic | schema |
|---|:---:|:---:|:---:|---|
| ราคาคาดบน PO | ✅ | ✅ | ❌ | `POPricedOut` / `POOut` |
| ต้นทุนและ VAT บนใบรับของ | ✅ | ❌ | ❌ | `GRAdminOut` / `GROut` |

**กับดักที่ต้องระวัง: ต้อง override `items` ในตัวลูกด้วย**

```python
class POPricedOut(POOut):
    items: list[POItemPricedOut]    # ← บรรทัดนี้ขาดไม่ได้
    estimated_total: Decimal
```

**ถ้าลืมบรรทัดนี้** — `POPricedOut` จะสืบ `items: list[POItemOut]` มาจากแม่
ซึ่งไม่มีราคา ผลคือ admin จัดการสิทธิ์ระดับบนถูกแล้ว แต่**ราคาในรายการย่อย
ยังหายอยู่ดี**

หลักการ: **สิทธิ์ต้องจัดการทุกชั้นที่มีข้อมูลอ่อนไหว ไม่ใช่แค่ชั้นบนสุด**

**`items: list[...] = Field(min_length=1)`** — เอกสารที่ไม่มีรายการสักแถว
สร้างไม่ได้ pydantic ปฏิเสธตั้งแต่ขอบนอก (422) ไม่ต้องไปเช็คใน service

**`total_paid` ไม่ใช่ `unit_cost` — ออกแบบตามของจริงที่คนถืออยู่ในมือ**

```
พนักงานถือกระดาษบิลที่เขียนว่า "หัวเทียน 5 ชิ้น จ่ายไป 856 บาท"
  → ให้กรอก 856 ตรง ๆ  ✅ ตรงกับที่ตาเห็น
  → ไม่ใช่ให้กดเครื่องคิดเลขหา 171.20 แล้วกรอก  ❌ คิดผิดได้ และเสียเวลา
```

ระบบคำนวณต่อหน่วยเอง (`unit_cost` จากข้อ 3)

**`vat_amount` เป็น `None` ได้ — สองความหมาย**

| ส่งมา | แปลว่า |
|---|---|
| `None` | ให้ระบบถอด VAT เอง (7/107 ตามค่าตั้ง) |
| มีตัวเลข | ใช้ตัวเลขที่อยู่บนใบกำกับจริง |

ต้องมีทางที่สองเพราะบางใบกำกับปัดเศษไม่ตรงกับที่เราคำนวณ
**เอกสารจริงต้องชนะการคำนวณเสมอ**

**`GRIn.supplier_name` เป็น `None` ได้** — เพราะถ้าอ้าง PO มา ระบบดึงชื่อร้าน
จาก PO ให้เอง ไม่ต้องกรอกซ้ำ ส่วนกรณีซื้อด่วนไม่มี PO ต้องกรอก
(service เป็นคนตรวจว่าสุดท้ายแล้วต้องมีชื่อร้าน)

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
    supplier_name, tax_id, po, ordered = data.supplier_name or None, digits(data.supplier_tax_id), None, {}
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
    return {
        "id": po.id, "display_number": f"PO-{po.id:05d}", "supplier_name": po.supplier_name,
        "supplier_phone": po.supplier_phone, "supplier_tax_id": po.supplier_tax_id,
        "supplier_address": po.supplier_address, "note": po.note, "status": po.status,
        "receive_state": ("partial" if got else "waiting") if po.status == "open" else None,
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

#### ตัวช่วย

**`received_by_product` — ตอบว่า "PO ใบนี้รับของไปแล้วสินค้าละเท่าไหร่"**

```
เดินทางของ query:  StockLot ──join──> GoodsReceipt ──where po_id──> PO ใบนี้
                   แล้ว group by product_id เอาผลรวม qty_received
คืน:               {product_id: จำนวนที่รับแล้ว}
```

**คำนวณสดทุกครั้ง ไม่เก็บเป็นคอลัมน์บน PO** — นี่คือกฎข้อ 4 ในหัวข้อแนวคิด
เหตุผลเดียวกับ `qty_on_hand` ในเฟส 3: **ตัวเลขที่คำนวณได้ถูกเสมอ
ตัวเลขที่เก็บไว้จะผิดสักวัน**

**`_close` ใช้ร่วมทั้งสามทางที่ปิด PO ได้** (รับครบเอง / ปิดก่อนครบ / ยกเลิก)

ตั้ง 4 ช่องพร้อมกันทีเดียว — `status` `close_reason` `closed_by` `closed_at`
เขียนรวมไว้ที่เดียวแบบนี้ทำให้**ไม่มีทางลืมตั้งบางช่อง** ซึ่งจะไปชน CHECK
`closed_at` กับ `closed_by` ที่ตั้งไว้ในข้อ 1

#### สร้าง ปิด ยกเลิก

**`create_po` ใช้ `lock_shop`** ทั้งที่ไม่แตะสต็อก — ยึดกฎเดียวทั้งระบบ ("คำสั่งที่แตะจัดซื้อล็อกเสมอ") ง่ายกว่ามานั่งตัดสินทีละคำสั่ง
**`model_dump(exclude=...)`** ช่องใน `POIn` ชื่อตรงกับคอลัมน์ ส่งเข้าทั้งก้อน ยกเว้น `items` (คนละตาราง) และ `supplier_tax_id` (ต้องผ่าน `digits` ก่อน)
**`po.items = [...]`** ใส่ลูกผ่าน relationship — SQLAlchemy เติม `po_id` ให้เองตอนบันทึก

**"ปิดก่อนครบ" กับ "ยกเลิก" แยกกันและห้ามสลับ**
- **ยกเลิก** = ใบนี้ไม่เคยเกิดขึ้นจริง ไม่มีของเข้าคลังเลย
- **ปิดก่อนครบ** = ของมาบางส่วน ร้านส่งที่เหลือไม่ได้ ต้องเก็บเป็นประวัติว่าเคยรับอะไร

ยกเลิกใบที่รับของแล้ว → มี Lot อ้างถึงใบที่ "ไม่มีอยู่จริง" · **ข้อความ error บอกทางออกด้วย** ("ให้ใช้ปิดก่อนครบแทน")

#### `create_goods_receipt` — อ่านเป็น 5 ช่วง

```
① ตรวจ PO (ถ้าอ้าง) → ② ตรวจชื่อร้าน → ③ ตรวจใบกำกับ → ④ สร้างใบ + Lot + movement → ⑤ ปิด PO ถ้าครบ
```

**ทั้งหมดอยู่ในทรานแซกชันเดียว** พังช่วงไหนย้อนหมด ไม่มีสภาพ "ใบรับของมีแล้วแต่ของไม่เข้าคลัง"

#### ① ตรวจ PO

**ตรวจทุกรายการให้ครบก่อน แล้วค่อยสร้างอะไร — สังเกตว่า `for` ลูปแรก
ไม่ได้สร้างอะไรเลย ตรวจอย่างเดียว**

ถ้าสร้าง Lot ไปพลางตรวจไปพลาง แล้วเจอรายการที่สามรับเกิน:
ต้องพึ่ง rollback อย่างเดียว และข้อความ error จะไม่บอกว่ารายการไหนผิด

**`item.qty > remaining` — ต้องอ่าน `got` ใต้ `lock_shop` เท่านั้น**

นี่คือคำตอบของกรณีตรวจรับข้อ 15 ลองดูว่าถ้าไม่มีล็อกจะเกิดอะไร:

```
PO สั่งหัวเทียน 10 ชิ้น · สองคนกดรับ 6 ชิ้นพร้อมกัน

ไม่มีล็อก:  ทั้งคู่อ่านได้ "ค้าง 10"  →  ทั้งคู่ผ่าน  →  รับเข้าคลัง 12 ชิ้น ❌
มีล็อก:     คนที่ 2 รอ  →  อ่านใหม่ได้ "ค้าง 4"  →  ถูกปฏิเสธถูกต้อง ✅
```

**เทสต์ `test_case15_concurrent_receipts_never_exceed_ordered` พิสูจน์ข้อนี้
ด้วยการยิงสองเธรดจริง ๆ** ไม่ใช่แค่เชื่อว่าน่าจะถูก

**ข้อความ error บอกตัวเลขค้างรับด้วย** (`ค้าง {format_qty(remaining)}`)
หลักการเดียวกับปรับลดในเฟส 3

#### ② ตรวจชื่อร้าน

```python
supplier_name = supplier_name or po.supplier_name
```

ไม่กรอกมา → ดึงจาก PO · กรอกมา → ใช้ที่กรอก (กรณีร้านส่งของจากสาขาอื่น)
ส่วนซื้อด่วนที่ไม่มี PO ต้องกรอกเอง ไม่งั้น 422

#### ③ ตรวจใบกำกับภาษี

**`.upper()` บนเลขที่ใบกำกับ** — `iv-001` กับ `IV-001` คือใบเดียวกัน
ต้องทำให้เป็นรูปแบบเดียวกันก่อนเทียบ (หลักการเดียวกับ `digits` ในข้อ 3)

**เช็คซ้ำใน python ทั้งที่มี unique index ที่ฐานแล้ว — ตั้งใจให้ซ้ำ**

| ชั้น | กันได้ | ข้อความที่ผู้ใช้เห็น |
|---|---|---|
| เช็คใน service | เกือบตลอด | "ใบกำกับภาษีเลขนี้ของร้านนี้ถูกบันทึกแล้ว" ✅ |
| partial unique index | **100%** | "ข้อมูลขัดกับกฎของระบบ" (จาก handler เฟส 2) |

**ชั้นนอกให้ข้อความดี ชั้นในให้ความถูกต้อง** — รูปแบบเดียวกับเรื่องรหัสสินค้าซ้ำในเฟส 3

**`supplier_invoice_date if invoice_no else None`** — ไม่มีเลขที่ ห้ามมีวันที่
ตรงกับ CHECK `invoice_date` ที่ตั้งไว้ในข้อ 1 (ถ้าไม่เขียนบรรทัดนี้ จะโดน CHECK ตีกลับ)

#### ④ สร้างใบรับของ + Lot + movement

**VAT: ระบบคิดให้ แต่คนแก้ทับได้**

```python
vat = item.vat_amount if item.vat_amount is not None else purchase_vat(item.total_paid, rate)
#     ^ กรอกมา ใช้ตัวที่กรอก              ^ ไม่กรอก ระบบถอด 7/107 ให้
```

**ทำไมต้องให้แก้ทับได้** — ใบกำกับจริงอาจปัดเศษต่างจากที่เราคำนวณนิดหน่อย
และ**ตัวเลขในระบบต้องตรงกับกระดาษที่ถืออยู่เสมอ** ไม่งั้นเวลาสรรพากรตรวจจะอธิบายไม่ได้

`rate` อ่านจากตาราง `settings` ตอนรับของ — ค่าที่เจ้าของอู่ตั้งไว้ในเฟส 2

**`cost = total_paid - vat` — ต้นทุนที่เก็บคือราคาก่อน VAT**

เพราะ VAT ซื้อ**ขอคืนได้** มันไม่ใช่ต้นทุนของกิจการ
ถ้าเก็บรวม VAT ไปด้วย ต้นทุนจะสูงเกินจริง 7% → กำไรที่คำนวณได้จะต่ำกว่าความจริง

**`db.flush()` สองจุด — เหตุผลเดียวกับเฟส 3**

```python
db.add(gr); db.flush()        # เอา gr.id ไปใส่ Lot
    db.add(lot); db.flush()   # เอา lot.id ไปใส่ movement
```

ยังไม่ `commit` — ทุกอย่างยังย้อนได้จนถึงบรรทัดสุดท้าย

**ไม่ต้อง `with_for_update` แบบปรับลดในเฟส 3** เพราะที่นี่**สร้าง Lot ใหม่**
ไม่ได้แก้แถวเดิม ไม่มีใครมาแย่งแก้แถวเดียวกัน

#### ⑤ ปิด PO ถ้ารับครบ

**ต้องอ่าน `received_by_product` ใหม่ ห้ามใช้ `got` ตัวเก่า**

```python
got = received_by_product(db, po.id)    # ← อ่านใหม่หลังสร้าง Lot แล้ว
```

`flush()` ข้างบนทำให้ Lot ใหม่ถูกเขียนลงฐานแล้ว query ครั้งนี้จึงเห็นด้วย
**ถ้าใช้ `got` ตัวเดิมที่อ่านไว้ตอนต้นฟังก์ชัน PO จะไม่มีวันปิดเลย**

**`all(...)`** — ต้องครบ**ทุก**รายการถึงปิด ขาดรายการเดียวก็ยังเปิดอยู่

ปิดแบบนี้ส่ง `reason=None` ได้ เพราะ CHECK `cancel_reason` ในข้อ 1
บังคับเหตุผลเฉพาะสถานะ `cancelled` ส่วนอันนี้เป็น `closed`

#### `po_view` / `gr_view` — ประกอบข้อมูลให้หน้าจอ

**ปัญหาที่สองฟังก์ชันนี้แก้** — หน้าจอต้องการข้อมูลที่ไม่ได้อยู่ในตารางเดียว:

| หน้าจอต้องการ | มาจากไหน |
|---|---|
| ชื่อ/รหัสสินค้า | ตาราง `products` |
| ยอดรับแล้ว / ยอดค้างรับ | **คำนวณจาก Lot** |
| เลขที่เอกสาร `PO-00007` | **คำนวณจาก id** |
| ชื่อผู้ออกเอกสาร | ตาราง `users` |
| สถานะรับของ (รอของ/รับบางส่วน) | **คำนวณ** |

ประกอบให้เสร็จที่นี่ทีเดียว **หน้าจอเลยไม่ต้องยิง API หลายรอบ**
(ส่วน pydantic มีหน้าที่แค่ตรวจรูปแบบกับตัดช่องตามสิทธิ์)

**คืน dict ที่มีทุกช่อง รวมราคาและต้นทุนด้วยเสมอ**

ไม่ต้องมาเช็คบทบาทในนี้ — ปล่อยให้ schema ที่ router เลือกใช้เป็นตัวตัดทิ้ง
(`serialize_for_role` จากเฟส 3) **ที่เดียวที่ตัดสินใจเรื่องสิทธิ์คือ router**

**`f"PO-{po.id:05d}"` — เลขเอกสารคำนวณจาก id ไม่เก็บคอลัมน์**

`:05d` = เติม 0 ข้างหน้าให้ครบ 5 หลัก (`7` → `00007`)

**ทำแบบนี้ได้เพราะเลข PO/GR ข้ามได้ไม่เป็นไร** — ถ้าสร้างแล้วพังจน rollback
id ก็ข้ามไปหนึ่งเลข ไม่มีใครเดือดร้อน

> ต่างจาก**เลขที่บิลขาย** ในเฟส 6 ที่กฎหมายกำหนดว่าห้ามข้าม
> อันนั้นจะต้องเก็บเป็นคอลัมน์จริงและมีวิธีออกเลขที่ซับซ้อนกว่านี้มาก

**`gr_view` ไม่รับ `db` แต่ `po_view` รับ**

เพราะ `gr.lots` และ `lot.product` เป็น relationship ที่ SQLAlchemy โหลดให้เอง
ส่วน `po_view` ต้องเรียก `received_by_product(db, ...)` ซึ่งต้องใช้ `db`

### `purchasing/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import current_user, require_role
from app.db import get_db, get_or_404
from app.models import GoodsReceipt, PurchaseOrder
from app.purchasing import service as svc
from app.purchasing.schemas import GRAdminOut, GRIn, GROut, POIn, POOut, POPricedOut
from app.schemas import ReasonIn, serialize_for_role

router = APIRouter(prefix="/api", tags=["purchasing"])
staff = require_role("admin", "employee")


def po_out(db, user, po):
    return (POOut if user.role == "mechanic" else POPricedOut).model_validate(svc.po_view(db, po))


@router.get("/purchase-orders", response_model=None)
def list_pos(status: str | None = None, db=Depends(get_db), user=Depends(current_user)):
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(200)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    return [po_out(db, user, po) for po in db.scalars(stmt)]


@router.post("/purchase-orders", response_model=None, status_code=201)
def create_po(data: POIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, svc.create_po(db, data, user))


@router.get("/purchase-orders/{po_id}", response_model=None)
def get_po(po_id: int, db=Depends(get_db), user=Depends(current_user)):
    return po_out(db, user, get_or_404(db, PurchaseOrder, po_id, "ใบสั่งซื้อ"))


@router.post("/purchase-orders/{po_id}/close-early", response_model=None)
def close_early(po_id: int, data: ReasonIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, svc.close_early(db, po_id, data.reason, user))


@router.post("/purchase-orders/{po_id}/cancel", response_model=None)
def cancel_po(po_id: int, data: ReasonIn, db=Depends(get_db), user=Depends(staff)):
    return po_out(db, user, svc.cancel_po(db, po_id, data.reason, user))


@router.get("/goods-receipts", response_model=None)
def list_receipts(db=Depends(get_db), user=Depends(current_user)):
    stmt = select(GoodsReceipt).order_by(GoodsReceipt.id.desc()).limit(200)
    if user.role == "mechanic":
        stmt = stmt.where(GoodsReceipt.created_by == user.id)
    return [serialize_for_role(user, GRAdminOut, GROut, svc.gr_view(gr)) for gr in db.scalars(stmt)]


@router.post("/goods-receipts", response_model=None, status_code=201)
def create_receipt(data: GRIn, db=Depends(get_db), user=Depends(current_user)):
    return serialize_for_role(user, GRAdminOut, GROut, svc.gr_view(svc.create_goods_receipt(db, data, user)))


@router.get("/goods-receipts/{gr_id}", response_model=None)
def get_receipt(gr_id: int, db=Depends(get_db), user=Depends(current_user)):
    gr = get_or_404(db, GoodsReceipt, gr_id, "ใบรับของ")
    if user.role == "mechanic" and gr.created_by != user.id:
        raise HTTPException(404, "ไม่พบใบรับของ")
    return serialize_for_role(user, GRAdminOut, GROut, svc.gr_view(gr))
```

### อ่าน router นี้ยังไง — สิทธิ์ของเฟสนี้ซับซ้อนกว่าเฟสก่อน

**สิทธิ์การเขียน**

| คำสั่ง | ใครทำได้ | ทำไม |
|---|---|---|
| ออก/ปิด/ยกเลิก PO | `staff` | ช่างไม่มีหน้าที่สั่งของ |
| บันทึกใบรับของ | **ทุกคน** (`current_user`) | ช่างขับไปซื้อของด่วนจริง |

**สิทธิ์การเห็นราคา — สองกฎคนละระดับ อย่าสับสน**

```
ราคาคาดบน PO       ตัดที่ "เป็นช่างหรือไม่"    → ช่างไม่เห็น พนักงานเห็น
ต้นทุนบนใบรับของ    ตัดที่ "เป็น admin หรือไม่"  → มีแต่ admin เห็น
```

ต่างกันเพราะราคาคาดเป็นแค่ตัวเลขประมาณการ แต่ต้นทุนจริงคือข้อมูลกำไรของกิจการ

**ช่างเห็นเฉพาะใบรับของที่ตัวเองบันทึก** — กันไว้**สองที่** ต้องครบทั้งคู่

```python
# ในรายการ
if user.role == "mechanic": stmt = stmt.where(GoodsReceipt.created_by == user.id)

# ในหน้ารายละเอียด (ลืมอันนี้ = ช่างเดา id แล้วเปิดดูใบคนอื่นได้)
if user.role == "mechanic" and gr.created_by != user.id: raise HTTPException(404, ...)
```

**ทำไมโยน 404 ไม่ใช่ 403**

| รหัส | บอกอะไรกับคนที่พยายามเดา |
|---|---|
| 403 | "ใบนี้**มีอยู่** แต่คุณดูไม่ได้" ← ยืนยันว่ามีจริง |
| 404 | "ไม่มีใบนี้" ← ไม่บอกอะไรเลย |

เมื่อความลับคือ "เอกสารนี้มีอยู่หรือเปล่า" **404 ปลอดภัยกว่า**
(หลักการเดียวกับข้อความล็อกอินที่ไม่บอกว่าชื่อผู้ใช้มีจริงไหม ในเฟส 1)

**`response_model=None` ทุกเส้น** — เพราะ schema ขึ้นกับบทบาท ปล่อยให้
`serialize_for_role` / `po_out` จัดการ (เหมือน `/lots` ในเฟส 3)

**`limit(200)`** รายการล่าสุดพอสำหรับหน้าจอ · **`?status=open`**
หน้าจอรับของใช้ดึงเฉพาะ PO ที่ยังรับของได้

### `app/main.py` — เติม router

**เปิด** `backend/app/main.py` → เติม import

```python
from app.purchasing import router as purchasing
```

→ แล้วเติมต่อจาก `include_router` ตัวอื่น

```python
app.include_router(purchasing.router)
```

## 5. เทสต์ — `tests/test_purchasing.py`

**ขั้นนี้ทำอะไร** เทสต์ชุดนี้พิเศษกว่าเฟสอื่น เพราะตั้งชื่อตาม**กรณีตรวจรับ**
ที่ตกลงกับเจ้าของอู่ไว้ (ข้อ 3, 13, 14, 15)

ตั้งชื่อแบบนี้แล้ววันที่เจ้าของอู่ถามว่า "กรณีข้อ 15 ทำได้หรือยัง"
เปิดไฟล์นี้ดูชื่อเทสต์ตอบได้ทันที

**สร้างไฟล์ใหม่** `backend/tests/test_purchasing.py`

```python
import threading
from decimal import Decimal as D

from fastapi import HTTPException

from app.db import SessionLocal
from app.purchasing.schemas import GRIn, GRItemIn, POIn, POItemIn
from app.purchasing.service import create_goods_receipt, create_po

INVOICE = dict(supplier_name="ร้าน ก", supplier_tax_id="0105555555555",
               supplier_invoice_no="iv-001", supplier_invoice_date="2026-09-01")


def po(client, h, items, role="employee"):
    return client.post("/api/purchase-orders", headers=h[role], json={
        "supplier_name": "ร้านอะไหล่ดี", "supplier_tax_id": "0-1055-55555-55-5", "items": items})


def receive(client, h, items, role="employee", **head):
    return client.post("/api/goods-receipts", json={"items": items, **head}, headers=h[role])


def get_po(client, h, po_id, role="employee"):
    return client.get(f"/api/purchase-orders/{po_id}", headers=h[role]).json()


def test_case3_tax_invoice_splits_vat_and_blocks_duplicate(client, h, make_product):
    pid = make_product()
    r = receive(client, h, [{"product_id": pid, "qty": "4", "total_paid": "856"}], **INVOICE)
    assert r.status_code == 201, r.text
    assert "cost_total" not in r.json()
    gr = client.get(f"/api/goods-receipts/{r.json()['id']}", headers=h["admin"]).json()
    assert (D(gr["vat_total"]), D(gr["cost_total"]), D(gr["items"][0]["unit_cost"])) == (56, 800, 200)
    assert gr["supplier_invoice_no"] == "IV-001" and gr["display_number"] == "GR-00001"
    assert receive(client, h, [{"product_id": pid, "qty": "1", "total_paid": "107"}], **INVOICE).status_code == 409


def test_quick_purchase_without_invoice_cost_is_total_paid(client, h, make_product):
    pid = make_product()
    r = receive(client, h, [{"product_id": pid, "qty": "2", "total_paid": "300"}], role="mechanic", supplier_name="ร้านข้างอู่")
    assert r.status_code == 201, r.text
    gr = client.get(f"/api/goods-receipts/{r.json()['id']}", headers=h["admin"]).json()
    assert (D(gr["cost_total"]), D(gr["vat_total"])) == (300, 0)


def test_case13_po_rules(client, h, make_product):
    pid, other = make_product("P1"), make_product("P2")
    assert po(client, h, [{"product_id": pid, "qty": "1"}], role="mechanic").status_code == 403
    assert po(client, h, []).status_code == 422
    po_id = po(client, h, [{"product_id": pid, "qty": "5", "unit_price": "100"}]).json()["id"]
    assert receive(client, h, [{"product_id": other, "qty": "1", "total_paid": "10"}], po_id=po_id).status_code == 409
    cancel = f"/api/purchase-orders/{po_id}/cancel"
    assert client.post(cancel, json={"reason": ""}, headers=h["employee"]).status_code == 422
    assert client.post(cancel, json={"reason": "ร้านไม่มีของ"}, headers=h["employee"]).json()["status"] == "cancelled"
    assert receive(client, h, [{"product_id": pid, "qty": "1", "total_paid": "10"}], po_id=po_id).status_code == 409


def test_mechanic_hides_po_prices_and_sees_only_own_receipts(client, h, make_product):
    pid = make_product()
    po_id = po(client, h, [{"product_id": pid, "qty": "5", "unit_price": "100"}]).json()["id"]
    mech = get_po(client, h, po_id, "mechanic")
    assert "unit_price" not in mech["items"][0] and "estimated_total" not in mech
    assert D(get_po(client, h, po_id)["estimated_total"]) == 500
    line = [{"product_id": pid, "qty": "1", "total_paid": "100"}]
    emp_gr = receive(client, h, line, supplier_name="ร้าน ก").json()["id"]
    mech_gr = receive(client, h, line, role="mechanic", supplier_name="ร้าน ข").json()["id"]
    assert [g["id"] for g in client.get("/api/goods-receipts", headers=h["mechanic"]).json()] == [mech_gr]
    assert client.get(f"/api/goods-receipts/{emp_gr}", headers=h["mechanic"]).status_code == 404


def test_case14_partial_receipts_until_auto_close(client, h, make_product):
    pid = make_product()
    po_id = po(client, h, [{"product_id": pid, "qty": "10"}]).json()["id"]
    assert get_po(client, h, po_id)["receive_state"] == "waiting"
    r = receive(client, h, [{"product_id": pid, "qty": "6", "total_paid": "600"}], po_id=po_id)
    assert r.status_code == 201, r.text
    assert r.json()["supplier_name"] == "ร้านอะไหล่ดี"
    detail = get_po(client, h, po_id)
    assert (detail["status"], detail["receive_state"], D(detail["items"][0]["qty_remaining"])) == ("open", "partial", 4)
    assert receive(client, h, [{"product_id": pid, "qty": "5", "total_paid": "500"}], po_id=po_id).status_code == 409
    assert receive(client, h, [{"product_id": pid, "qty": "4", "total_paid": "400"}], po_id=po_id).status_code == 201
    assert get_po(client, h, po_id)["status"] == "closed"
    assert receive(client, h, [{"product_id": pid, "qty": "1", "total_paid": "100"}], po_id=po_id).status_code == 409


def test_case15_close_early_vs_cancel(client, h, make_product):
    pid = make_product()
    po_id = po(client, h, [{"product_id": pid, "qty": "10"}]).json()["id"]
    close = f"/api/purchase-orders/{po_id}/close-early"
    assert client.post(close, json={"reason": "x"}, headers=h["employee"]).status_code == 409
    receive(client, h, [{"product_id": pid, "qty": "3", "total_paid": "300"}], po_id=po_id)
    assert client.post(f"/api/purchase-orders/{po_id}/cancel", json={"reason": "x"}, headers=h["employee"]).status_code == 409
    assert client.post(close, json={"reason": ""}, headers=h["employee"]).status_code == 422
    r = client.post(close, json={"reason": "ร้านเลิกขาย"}, headers=h["employee"]).json()
    assert (r["status"], r["close_reason"]) == ("closed", "ร้านเลิกขาย")
    assert receive(client, h, [{"product_id": pid, "qty": "1", "total_paid": "100"}], po_id=po_id).status_code == 409


def test_case15_concurrent_receipts_never_exceed_ordered(users, make_product):
    pid, employee = make_product(), users["employee"]
    with SessionLocal() as s:
        po_id = create_po(s, POIn(supplier_name="ร้าน ก", items=[POItemIn(product_id=pid, qty=10)]), employee).id
    barrier, results = threading.Barrier(2), []

    def worker():
        barrier.wait()
        with SessionLocal() as s:
            try:
                create_goods_receipt(s, GRIn(po_id=po_id, items=[GRItemIn(product_id=pid, qty=6, total_paid=600)]), employee)
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

### อ่านเทสต์ชุดนี้ยังไง

**`test_case3` — VAT และใบกำกับซ้ำ**

```
พนักงานบันทึกรับของ 4 ชิ้น จ่าย 856 พร้อมใบกำกับ
  พนักงานดู  → ไม่มี cost_total ใน response ของเขาเลย
  admin ดู   → VAT 56 · ต้นทุน 800 · ต่อหน่วย 200
เลขใบกำกับ iv-001 → เก็บเป็น IV-001
บันทึกใบเดิมซ้ำ    → 409
```

**`test_case14` — เดินตามเรื่องจริงทั้งเส้นในเทสต์เดียว**

```
สั่ง 10 → สถานะ "รอของ"
รับ 6 (ไม่กรอกชื่อร้าน ดึงจาก PO)  → สถานะ "รับบางส่วน" ค้าง 4
ลองรับ 5 (เกินค้าง)  → 409
รับ 4                → PO ปิดเอง
ลองรับต่อ             → 409 ปิดแล้ว
```

**ทำไมรวมเป็นเทสต์เดียว ไม่แตกเป็นห้าเทสต์** — เพราะแต่ละขั้นต้องใช้สถานะ
จากขั้นก่อนหน้า แตกแล้วต้อง setup ซ้ำทุกเทสต์ และอ่านแล้วไม่เห็นภาพรวม
ว่าเรื่องดำเนินไปยังไง

**`test_case15_concurrent` — เทสต์ที่ยิงสองเธรดจริง**

```python
barrier = threading.Barrier(2)   # ปล่อยทั้งสองเธรดพร้อมกันเป๊ะ
# แต่ละเธรดมี SessionLocal() ของตัวเอง = คนละ connection จริง ๆ
assert sorted(results, key=str) == [409, "ok"]   # ต้องผ่านแค่ 1 พัง 1
```

**ลองพิสูจน์เองได้: ลบ `lock_shop(db)` ออกจาก `create_goods_receipt`
แล้วรันเทสต์นี้ — จะแดงทันที** (ได้ `["ok", "ok"]` คือรับเกินไปแล้ว)

นี่คือวิธีเดียวที่จะรู้จริงว่าล็อกทำงาน — อ่านโค้ดเฉย ๆ ดูยังไงก็เหมือนถูก

**ตัวช่วย `po()` จงใจส่งเลขผู้เสียภาษีแบบมีขีด** (`0-1055-55555-55-5`)
เพื่อทดสอบว่า `digits` แปลงเป็นตัวเลขล้วนจริง

### รันเทสต์

```
docker compose run --rm api pytest
```

ต้อง **passed ทั้งหมด ไม่มี failed**

---

# ส่วนหน้าจอ

**ส่วนนี้จะได้อะไร** หน้าจอ 7 หน้า: รายการ PO · สร้าง PO · รายละเอียด PO ·
รายการใบรับของ · บันทึกรับของ · รายละเอียดใบรับของ · หน้าพิมพ์ PO

## 6. ของกลางที่เติม

**ขั้นนี้ทำอะไร** เติมของกลางที่หน้าจอทั้ง 7 หน้าจะใช้ร่วมกัน
ทำให้ครบก่อนแล้วค่อยลุยหน้าจริง

### `api.js` — เติมท้ายไฟล์

```js
// เลขเอกสารจาก id แบบเดียวกับ backend: docNo("PO", 5) → "PO-00005"
export const docNo = (prefix, id) => `${prefix}-${String(id).padStart(5, "0")}`;

// วันนี้ตามเวลาไทยในรูป YYYY-MM-DD (ค่าที่ <input type="date"> ต้องการ)
export const todayBangkok = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bangkok" }).format(new Date());
```

**`docNo`** — ทำเลขเอกสารจาก id แบบเดียวกับ backend
(`f"PO-{id:05d}"` ฝั่ง python = `docNo("PO", id)` ฝั่ง js)

จำเป็นเพราะหน้า Lot ในเฟส 3 ต้องแสดง `GR-00001` จาก `receipt_id` ที่ได้มาเป็นตัวเลขเปล่า ๆ

**`todayBangkok` — วันนี้ตามเวลาไทย ในรูป `YYYY-MM-DD`**

```js
new Date().toISOString().slice(0, 10)   // ❌ วันตาม UTC — ตีหนึ่งไทยจะได้ "เมื่อวาน"
todayBangkok()                          // ✅ วันตามเวลาไทยจริง
```

`en-CA` เป็นภาษาที่เรียงวันที่เป็น `YYYY-MM-DD` พอดี ซึ่งเป็นรูปแบบที่
`<input type="date">` ต้องการ — ใช้ประโยชน์จากตรงนี้แทนที่จะต่อ string เอง

### `index.css`

**เปิด** `frontend/src/index.css` → หา `@theme { ... }` → เติม**ใต้ปีกกาปิด** ของมัน

```css
@page { size: A4; margin: 12mm; }
```

`@page` เป็นกฎ CSS สำหรับ**ตอนสั่งพิมพ์เท่านั้น** ตั้งขนาดกระดาษกับขอบ
ไว้ให้หน้าพิมพ์ใบสั่งซื้อในข้อ 14 (อยู่นอก `@layer` เพราะไม่ใช่คลาส)

→ หา `.btn-secondary` เติมใต้มัน

```css
  .btn-danger { @apply bg-danger text-white hover:brightness-110; }
```

ปุ่มสีแดงสำหรับคำสั่งที่ย้อนกลับไม่ได้ (ยกเลิก PO · ปิด PO)

→ หา `.tabs` เติม**เหนือ**มัน

```css
  .chip { @apply inline-flex min-h-11 cursor-pointer items-center rounded-full border border-line bg-white px-4 text-sm font-medium whitespace-nowrap transition-colors duration-150 hover:border-accent; }
  .chip-on { @apply border-accent bg-accent-soft text-accent-ink; }
```

`chip` คือปุ่มกลมมนที่ใช้เลือกของจากรายการสั้น ๆ (ข้อ 12 ใช้เลือก PO)
`chip-on` คือสถานะที่ถูกเลือกอยู่ — ใส่คู่กัน `className="chip chip-on"`
เหมือน `btn btn-primary`

### `components/Icon.jsx` — เติมใน `PATHS`

```jsx
  clipboard: <><rect width="8" height="4" x="8" y="2" rx="1" ry="1" /><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><path d="M12 11h4" /><path d="M12 16h4" /><path d="M8 11h.01" /><path d="M8 16h.01" /></>,
  truck: <><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2" /><path d="M15 18H9" /><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14" /><circle cx="17" cy="18" r="2" /><circle cx="7" cy="18" r="2" /></>,
  printer: <><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6" /><rect x="6" y="14" width="12" height="8" rx="1" /></>,
```

### `components/StatusBadge.jsx` — สถานะ PO และใบรับของ

ใน `STATUS` เติมบนสุด

```jsx
  waiting: ["รอของ", "info"],
  partial: ["รับบางส่วน", "warn"],
  closed: ["ปิดแล้ว", "neutral"],
  cancelled: ["ยกเลิก", "danger"],
```

และใต้ `disabled`

```jsx
  quick: ["ซื้อด่วน", "neutral"],
```

เติมเหนือ comment ของ `productStatus`

```jsx
// สถานะ PO ที่มีความหมายที่สุดป้ายเดียว: เปิดอยู่ → รอของ/รับบางส่วน, ปิด/ยกเลิก → สถานะจริง
export const poStatus = (po) => (po.status === "open" ? po.receive_state : po.status);
```

**`poStatus` — ตัวแปลงสถานะให้เหลือป้ายเดียวที่มีความหมาย** (ตั้งชื่อคู่กับ `productStatus`)

```jsx
po.status === "open" ? po.receive_state : po.status
//  เปิดอยู่ → เอา "รอของ"/"รับบางส่วน" มาแสดง
//  ปิด/ยกเลิก → แสดงสถานะจริง
```

เพราะถ้าโชว์ทั้งสองอย่าง ผู้ใช้จะเห็น "เปิดอยู่ · รับบางส่วน" ซึ่งยาว
และคำว่า "เปิดอยู่" ไม่ได้บอกอะไรเพิ่ม

ท่าเดียวกับ `productStatus` ในเฟส 3 — **คำนวณป้ายจากข้อมูล ไม่เก็บ**

### `components/DetailLayout.jsx` — คำสั่งอันตรายในเมนู ⋯ เป็นสีแดง

**เปิด** `frontend/src/components/DetailLayout.jsx` → ใน `MoreMenu` แก้ `className` ของปุ่ม

```jsx
              className={`flex min-h-11 w-full items-center px-4 text-left hover:bg-surface ${m.danger ? "text-danger" : ""}`}
```

ส่ง `danger: true` มากับรายการในเมนูก็ได้ตัวหนังสือสีแดง (ข้อ 10 ใช้กับ "ยกเลิกใบสั่งซื้อ")

### `components/ReasonDialog.jsx` — ปุ่มยืนยันสีแดง

```jsx
export default function ReasonDialog({ title, onClose, onSubmit, register, mutation, danger = false, children }) {
```

```jsx
            <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} disabled={mutation.isPending}>
              {mutation.isPending ? "กำลังบันทึก…" : "ยืนยัน"}
            </button>
```

แก้ comment บนสุดให้บอกเรื่อง `danger` ด้วย:

```jsx
// popup ที่มีช่อง "เหตุผล" ท้ายฟอร์ม: ฟอร์ม (register/onSubmit) และ mutation มาจากคนเรียก, danger = ปุ่มยืนยันสีแดง
```

**`danger = false` เป็นค่าปริยาย** — ที่เรียกใช้อยู่แล้วในเฟส 3 (ปรับลด)
ไม่ต้องแก้อะไร ยังได้ปุ่มน้ำเงินเหมือนเดิม

ยกเลิก PO ทำย้อนไม่ได้ — **ปุ่มแดงคือการบอกให้คิดอีกรอบก่อนกด**

### `pages/ProductDetailPage.jsx` — Lot จากการรับของ

**ขั้นนี้ทำอะไร** ย้อนกลับไปแก้หน้าเฟส 3 ให้รู้จัก Lot ชนิดใหม่
(ที่มาจากการรับของ) และแสดงเลขใบรับของให้ตามรอยต่อได้

**เปิด** `frontend/src/pages/ProductDetailPage.jsx` → แก้ 5 จุดตามนี้

```jsx
import { api, docNo, formatMoney, formatQty, formatDate, formatUnitPrice } from "../api";
```

```jsx
const SOURCE = { receipt: "รับของ", adjustment: "ปรับเพิ่ม", opening: "สต็อกตั้งต้น" };
const MOVE = { receive: "รับของ", adjust: "ปรับสต็อก", opening: "ตั้งต้น" };
```

หัว Lot แสดงเลขใบรับของ (ใน `LotList`)

```jsx
              <span className="font-semibold">
                Lot #{lot.id} · {SOURCE[lot.source_type]}
                {lot.receipt_id && ` ${docNo("GR", lot.receipt_id)}`}
              </span>
```

บรรทัดต้นทุนเติมภาษีซื้อ (ใน `LotList`)

```jsx
            {showCost && (
              <div className="num text-sm">
                ต้นทุน/หน่วย {formatUnitPrice(lot.unit_cost)} · ภาษีซื้อ {formatMoney(lot.vat_amount)}
              </div>
            )}
```

สมุดสต็อกแสดงเลขใบรับของต่อท้าย (ใน `MovementList`)

```jsx
              <div className="text-muted">
                {[formatDate(m.created_at), m.created_by_name, m.receipt_id && docNo("GR", m.receipt_id)]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
```

**ทำไมต้องโชว์เลขใบรับของในสมุดสต็อก** — เพื่อให้**ตามรอยต่อได้**

```
สมุดสต็อกบอก: "รับของ +4 · 21 ก.ย. · สมชาย · GR-00003"
                                            ^ เปิดใบนี้ดูต่อได้เลยว่าซื้อจากร้านไหน ราคาเท่าไหร่
```

**`.filter(Boolean)` ก่อน `.join(" · ")`** — ตัดค่าว่างทิ้งก่อนต่อข้อความ

จำเป็นเพราะ movement ที่มาจากการปรับสต็อกไม่มี `receipt_id`
ไม่กรองแล้วจะได้ `"21 ก.ย. · สมชาย · "` มีจุดคั่นห้อยท้ายลอย ๆ

(`Boolean` ในฐานะฟังก์ชันจะคืน `false` สำหรับ `null`/`undefined`/`""`)

## 7. `components/ProductSearch.jsx` — ค้นแล้วแตะเลือกสินค้า

**ขั้นนี้ทำอะไร** ช่องค้นหาสินค้าที่แตะแล้วเลือกได้ ใช้สองที่
(ตอนสร้าง PO และตอนรับของซื้อด่วน)

**สร้างไฟล์ใหม่** `frontend/src/components/ProductSearch.jsx`

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

### อ่านโค้ดนี้ยังไง

**ทำไมไม่ใช้ `<select>` ธรรมดา**

สินค้ามีหลายร้อยตัว `<select>` บนมือถือจะเป็นล้อหมุนยาวเหยียดที่เลื่อนหาไม่เจอ
**พิมพ์ "เบรก" แล้วแตะ เร็วกว่ามาก**

**`useQuery({ queryKey: ["products"] })` ในคอมโพเนนต์เอง — ไม่ต้องให้คนเรียกส่งรายการสินค้ามา**

กุญแจเดียวกับหน้าสต็อก (เฟส 3) ถ้าเคยเปิดหน้าสต็อกมาแล้ว ได้จาก cache ทันทีไม่ยิงซ้ำ
คนเรียกส่งแค่ `onPick` — "เลือกแล้วให้ทำอะไร" ใช้ได้ทุกที่โดยไม่ต้องเตรียมอะไร

**สี่รายละเอียดที่ทำให้ใช้งานจริงได้ดี**

- **แสดงคงเหลือ และขึ้น "หมด" สีแดง** — ตอนสั่งของ คำถามแรกในหัวคือ
  "ของเหลือเท่าไหร่ ต้องสั่งไหม" ตอบให้ตรงนั้นเลย
- **`.slice(0, 20)`** — ไม่วาดหลายร้อยแถวพร้อมกัน ค้นให้แคบลงเอาเอง
- **`p.is_active`** — สินค้าที่เลิกใช้แล้วไม่ต้องโผล่มาให้เลือกผิด (API ส่งมาทั้งหมด กรองตรงนี้)
- **`setQ("")` หลังเลือก** — ล้างช่องค้นทันที พร้อมพิมพ์หาตัวถัดไปได้เลย
  (คนมักเพิ่มหลายรายการติดกัน)

**ช่องค้นหาใช้ `useState` ไม่ใช้ `useForm`** — มันไม่ได้เป็นส่วนของข้อมูลที่ส่งไป backend
เป็นแค่ตัวกรองบนจอ (เหมือน `SearchBar` เฟส 3) `useForm` มีไว้สำหรับค่าที่จะถูกบันทึก

**สามสถานะครบเหมือนเดิม** — กำลังโหลด / ไม่พบ / มีผลลัพธ์ (กฎจากเฟส 2)

## 8. `pages/PurchaseOrdersPage.jsx` — รายการใบสั่งซื้อ

**ขั้นนี้ทำอะไร** หน้ารายการ PO — โครงเดียวกับหน้าสต็อกเฟส 3

**สร้างไฟล์ใหม่** `frontend/src/pages/PurchaseOrdersPage.jsx`

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
export default function PurchaseOrdersPage() {
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

### อ่านโค้ดนี้ยังไง

**การกรองแบ่งเป็นสองแบบ ตั้งใจให้ต่างกัน**

| กรองด้วย | ทำที่ไหน | เพราะ |
|---|---|---|
| สถานะ (เปิด/ปิด/ยกเลิก) | **API** (`?status=open`) | PO สะสมไปเรื่อย ๆ ไม่ควรโหลดทุกใบ |
| คำค้น (เลขที่/ร้าน) | **เบราว์เซอร์** | ในชุดที่โหลดมาแล้ว กรองทันทีทุกตัวอักษร |

ต่างจากเฟส 3 ที่กรองในเบราว์เซอร์หมด เพราะสินค้ามีจำนวนจำกัด แต่เอกสารไม่มีเพดาน

**`useQuery` ที่มี query string — เขียน `queryFn` เอง**

```jsx
useQuery({
  queryKey: ["purchase-orders", { status }],
  queryFn: () => api(status === "all" ? "/purchase-orders" : `/purchase-orders?status=${status}`),
});
```

`queryFn` ตัวกลางใน `api.js` (เฟส 1) ต่อกุญแจด้วย `/` ได้แค่ path ล้วน ๆ
เส้นไหนมี `?...` ให้ใส่ `queryFn` ของตัวเองแทน ส่วน**กุญแจยังขึ้นต้นด้วย `"purchase-orders"`** เหมือนเดิม
`invalidateQueries({ queryKey: ["purchase-orders"] })` เลยยังจับได้ครบ

**`{ status }` อยู่ในกุญแจ = แต่ละแท็บมี cache ของตัวเอง**

```
แท็บ "เปิดอยู่"  → ["purchase-orders", { status: "open" }]
แท็บ "ปิดแล้ว"  → ["purchase-orders", { status: "closed" }]
```

กดสลับแท็บ `status` เปลี่ยน → กุญแจเปลี่ยน → TanStack Query ดึงชุดของแท็บนั้นเอง ไม่ต้องสั่งโหลด
สลับกลับมาแท็บเดิม ได้จาก cache ทันที

(หน้ารับของข้อ 12 ขอกุญแจ `["purchase-orders", { status: "open" }]` เหมือนกัน — ได้ข้อมูลชุดเดียวกัน)

**เริ่มต้นที่แท็บ "เปิดอยู่"** เพราะคือใบที่ยังต้องทำอะไรกับมัน
คนเปิดหน้านี้ส่วนใหญ่มาตามงานที่ค้าง ไม่ได้มาดูประวัติ

**`...(isStaff ? [{...}] : [])` — เพิ่มคอลัมน์แบบมีเงื่อนไข**

`...` (spread) แผ่อาเรย์ออกมาต่อในที่เดิม ส่ง `[]` มาก็ไม่มีอะไรเพิ่ม
ช่างเลยไม่มีคอลัมน์ยอดประมาณการ (และ backend ก็ไม่ส่งมาอยู่แล้ว)

## 9. `pages/PurchaseOrderNewPage.jsx` — ป๊อปอัพสร้าง PO

**ขั้นนี้ทำอะไร** ฟอร์มสร้าง PO — เป็นฟอร์มแรกของโปรเจกต์ที่มี
**รายการย่อยหลายแถว** (หัวเอกสาร + รายการสินค้า) ได้ใช้ `useFieldArray` ของ react-hook-form เป็นครั้งแรก

**สร้างไฟล์ใหม่** `frontend/src/pages/PurchaseOrderNewPage.jsx`

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
export default function PurchaseOrderNewPage() {
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

### อ่านโค้ดนี้ยังไง

**`useFieldArray` — รายการที่เพิ่ม/ลบแถวได้ ในฟอร์มเดียวกับหัวเอกสาร**

```jsx
const { register, handleSubmit, control, watch } = useForm({ defaultValues: EMPTY_PO });   // items: []
const { fields, append, remove } = useFieldArray({ control, name: "items" });
```

| ได้อะไรมา | ใช้ทำอะไร |
|---|---|
| `fields` | อาเรย์ของแถวไว้**วาด** — แต่ละแถวมี `field.id` ที่ react-hook-form สร้างให้ ใช้เป็น `key` |
| `append(ค่า)` | เพิ่มแถวท้ายสุด |
| `remove(i)` | ลบแถวที่ `i` |
| `control` | ตัวเชื่อม `useFieldArray` เข้ากับ `useForm` ตัวเดียวกัน |

แต่ละช่องในแถวใช้ `register` ด้วยชื่อที่มี index:

```jsx
{...register(`items.${i}.qty`)}          // → form.items[i].qty
{...register(`items.${i}.unit_price`)}   // → form.items[i].unit_price
```

กดบันทึก `handleSubmit` คืนก้อนเดียว `{ supplier_name, ..., items: [{ product, qty, unit_price }, ...] }`
ไม่ต้องมี `useState` แยกระหว่างหัวกับรายการ ไม่ต้องเขียน `setItems(items.map(...))` เองทุกครั้งที่พิมพ์

**`key={field.id}` ไม่ใช่ `key={i}`** — ลบแถวกลางแล้ว index ของแถวถัดไปเลื่อน
ถ้าใช้ `i` เป็น key React จะคิดว่าแถวที่ 3 เดิมกลายเป็นแถวที่ 2 แล้วค่าที่พิมพ์ไว้สลับช่องกัน

**แต่ละแถวเก็บ object สินค้าทั้งก้อน ไม่ได้เก็บแค่ id**

```js
append({ product: p, qty: "", unit_price: "" })
//       ^ เก็บทั้งก้อนไว้เลย
```

เพราะหน้าจอต้องแสดงชื่อ รหัส และหน่วยของสินค้าในแต่ละแถว (`field.product.name`)
ถ้าเก็บแค่ id ต้องวนหาในรายการทุกครั้งที่วาด ตอนส่งค่อยแปลงเป็น `product_id` ใน `mutationFn`

**`fields` ไว้วาด · `watch("items")` ไว้คำนวณ**

```jsx
const items = watch("items");   // ค่าปัจจุบันที่พิมพ์อยู่ อัปเดตทุกตัวอักษร
const estimate = items.reduce(...);
```

`fields` เป็นสำเนาตอนเพิ่มแถว ไม่ได้อัปเดตตามที่พิมพ์ — อยากได้ค่า**ล่าสุด**ต้อง `watch`
ยอดประมาณการเลยใช้ `items` ส่วนชื่อสินค้า (ไม่เปลี่ยน) ใช้ `field.product` ได้

**`addProduct` ไม่รับสินค้าซ้ำ — และไม่ต้องขึ้น error**

```js
if (!items.some((it) => it.product.id === p.id)) append(...);
//   ^ มีแล้วก็ไม่ทำอะไร เงียบ ๆ
```

ตรงกับ `UniqueConstraint("po_id", "product_id")` ที่ฐาน — แตะซ้ำไม่เกิดอะไร
ซึ่งเป็นพฤติกรรมที่ผู้ใช้คาดหวังอยู่แล้ว ไม่ต้องเด้ง error มากวน

**`mutationFn: ({ items, ...head }) => ...` — แยกรายการออกจากหัวเอกสาร**

`...head` คือทุกช่องที่เหลือ (ชื่อร้าน เบอร์ ฯลฯ) ส่งไปตรง ๆ ส่วน `items` แปลงก่อน:

```js
items.map((it) => ({ product_id: it.product.id, qty: it.qty, unit_price: it.unit_price || null }))
```

`unit_price || null` — ช่องว่างแปลว่า "ไม่ระบุราคา" ไม่ใช่ "ราคา 0" ส่ง `""` ไปจะโดน pydantic ตีกลับ

**ยอดประมาณการคำนวณด้วย `Number` — แต่แสดงอย่างเดียว**

ใช้ float ได้เพราะเป็นแค่ตัวเลขให้ดูระหว่างกรอก **ยอดจริงคำนวณด้วย `Decimal`
ที่เซิร์ฟเวอร์** (`line_total` ในข้อ 3)

**`<details>` ซ่อนข้อมูลร้านที่ไม่บังคับกรอก**

ส่วนใหญ่กรอกแค่ชื่อร้านก็พอ — **ฟอร์มสั้นลงครึ่งหนึ่งบนมือถือ**
ใครต้องการกรอกครบก็กดเปิด ช่องข้างในยังอยู่ในหน้า (แค่ซ่อน) `register` เลยเก็บค่าได้ปกติ

**`disabled={save.isPending || fields.length === 0}`** — กดบันทึกไม่ได้ถ้ายังไม่มีรายการ
(ตรงกับ `Field(min_length=1)` ที่ backend)

**บันทึกแล้ว invalidate `["purchase-orders"]` แล้วพาไปหน้ารายละเอียด PO** —
รายการ PO ทุกแท็บจะมีใบใหม่ และสิ่งถัดไปที่คนทำคือ**พิมพ์ส่งร้าน** ซึ่งปุ่มอยู่หน้านั้น (ท่าเดียวกับเพิ่มสินค้าในเฟส 3)

## 10. `pages/PurchaseOrderPage.jsx` — หน้ารายละเอียด PO

**ขั้นนี้ทำอะไร** หน้ารายละเอียด PO — ใช้ `DetailLayout` จากเฟส 3 เป็นเปลือก
เพิ่มแถบความคืบหน้าว่ารับของมาแล้วกี่เปอร์เซ็นต์

**สร้างไฟล์ใหม่** `frontend/src/pages/PurchaseOrderPage.jsx`

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
export default function PurchaseOrderPage() {
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
  const menu = [
    ...(isStaff
      ? [{ label: "พิมพ์ใบสั่งซื้อ", onClick: () => window.open(`/print/po/${po.id}`, "_blank", "noreferrer") }]
      : []),
    ...(isStaff && po.receive_state === "partial"
      ? [{ label: "ปิดก่อนรับครบ", onClick: () => setAction("close-early") }]
      : []),
    ...(isStaff && po.receive_state === "waiting"
      ? [{ label: "ยกเลิกใบสั่งซื้อ", danger: true, onClick: () => setAction("cancel") }]
      : []),
  ];

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

### อ่านโค้ดนี้ยังไง

**แบ่งเป็นสามชิ้น ท่าเดียวกับ `ProductDetailPage` เฟส 3**

```
PurchaseOrderPage   ดึง PO · หัว · เมนู · รายการ · เลือกว่าป๊อปอัพเปิดไหม
 ├─ PoItem          หนึ่งรายการ + แถบความคืบหน้า
 └─ PoActionDialog  ป๊อปอัพปิดก่อนครบ / ยกเลิก (ฟอร์มเหตุผล + ส่ง)
```

**`useQuery({ queryKey: ["purchase-orders", id] })`** — `GET /purchase-orders/{id}`
ไม่เจอ (หรือช่างเปิดไม่ได้) backend ตอบ 404 → `error.message` ขึ้นเป็นหัวหน้า

**เมนูแสดงเฉพาะคำสั่งที่ทำได้จริง ณ ตอนนี้ — สำคัญมาก**

```jsx
...(isStaff && po.receive_state === "partial" ? [{ label: "ปิดก่อนรับครบ", ... }] : []),
...(isStaff && po.receive_state === "waiting" ? [{ label: "ยกเลิกใบสั่งซื้อ", ... }] : []),
```

ตรงกับกฎใน service เป๊ะ ๆ (`close_early` ต้องเคยรับของ · `cancel_po` ต้องยังไม่เคยรับ)

**ผู้ใช้เลยไม่มีทางกดปุ่มแล้วเจอ error** — ปุ่มที่กดไม่ได้ไม่ต้องโผล่มาให้เห็น
ดีกว่าโผล่แล้วเด้ง "ใบสั่งซื้อนี้รับของไปแล้ว ให้ใช้ปิดก่อนครบแทน"

**`action` เก็บชื่อ endpoint ตรง ๆ**

```jsx
setAction("cancel")       // หรือ "close-early"
api(`/purchase-orders/${poId}/${action}`, ...)   // เอาไปต่อ URL ได้เลย
```

`PoActionDialog` ตัวเดียวใช้ได้ทั้งสองคำสั่ง แค่เปลี่ยนหัวข้อ (`ACTION_TITLE[action]`) กับสีปุ่ม (`danger`)

**`{action && <PoActionDialog ... />}`** — render = เปิด (กฎของ `Modal` เฟส 2)
ปิดแล้วช่องเหตุผลที่พิมพ์ค้างหายไปเอง เปิดใหม่ครั้งหน้าว่างเสมอ

**`PoActionDialog` — ท่าเดียวกับ `AdjustDownDialog` เฟส 3**

```jsx
const { register, handleSubmit } = useForm({ defaultValues: { reason: "" } });
const applyAction = useMutation({ mutationFn: (form) => api(..., { body: form }), onSuccess: ... });
<ReasonDialog register={register} mutation={applyAction} onSubmit={handleSubmit((form) => applyAction.mutate(form))} />
```

ฟอร์มมีช่องเดียวคือ `reason` ซึ่ง `ReasonDialog` วาดให้เอง `form` เลยเป็น `{ reason }` ตรงกับ `ReasonIn` ของ backend ส่งทั้งก้อนได้เลย
สำเร็จ → invalidate `["purchase-orders"]` (หน้านี้ + รายการทุกแท็บ) แล้วปิด

**`/goods-receipts/new?po=5` — ส่งของผ่าน query string**

ปุ่มหลัก "รับของตาม PO นี้" พา PO ไปด้วยทาง URL
หน้าฟอร์มรับของจะอ่านแล้วเลือก PO ให้เองอัตโนมัติ (ข้อ 12)

**`window.open(..., "_blank", "noreferrer")`** — หน้าพิมพ์เปิดแท็บใหม่
พิมพ์เสร็จปิดแท็บ กลับมาอยู่ที่หน้าเดิม ไม่ต้องกด back

**แถบความคืบหน้า — เห็นทันทีว่ารายการไหนมาครบแล้ว**

```jsx
const percent = Math.min(100, (Number(item.qty_received) / Number(item.qty)) * 100);
//              ^ กัน 100+ เผื่อมีข้อมูลเก่าที่ผิด แถบจะได้ไม่ล้นกรอบ
```

`role="progressbar"` + `aria-valuenow` ทำให้ screen reader อ่านเปอร์เซ็นต์ได้
ไม่งั้นคนที่มองไม่เห็นจะได้ข้อมูลไม่ครบ (แถบสีเป็นข้อมูล ไม่ใช่ของประดับ)

**`info.filter(([, value]) => value)`** — ช่องที่ไม่ได้กรอกไม่ต้องแสดงหัวข้อเปล่า
`[, value]` คือการข้ามตัวแรกแล้วเอาตัวที่สอง (ค่า) มาเช็ค

## 11. `pages/GoodsReceiptsPage.jsx` — รายการใบรับของ

**ขั้นนี้ทำอะไร** หน้ารายการใบรับของ โครงเดียวกับรายการ PO

**สร้างไฟล์ใหม่** `frontend/src/pages/GoodsReceiptsPage.jsx`

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
export default function GoodsReceiptsPage() {
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

### อ่านโค้ดนี้ยังไง

**`SourceBadge` — ป้ายบอกที่มาของใบรับของ**

```jsx
gr.po_id ? <span className="badge badge-info">{gr.po_number}</span> : <StatusBadge status="quick" />
//         อ้าง PO → แสดงเลข PO                              ไม่อ้าง → ป้าย "ซื้อด่วน"
```

ใช้สองที่ (การ์ดมือถือ + คอลัมน์ตาราง) เลยตั้งเป็นคอมโพเนนต์เล็กบนสุดของไฟล์ ให้สองที่หน้าตาตรงกันแน่ ๆ
ทำให้กวาดตาดูรายการแล้วแยกออกทันทีว่าใบไหนมีการสั่งล่วงหน้า ใบไหนซื้อด่วน

**บอกช่างตรง ๆ ว่าเห็นแค่ของตัวเอง**

```jsx
{user.role === "mechanic" && <p className="text-sm text-muted">แสดงเฉพาะใบรับของที่คุณบันทึก</p>}
```

**ข้อนี้สำคัญกว่าที่คิด** — ถ้าไม่บอก ช่างที่รู้ว่าเมื่อวานเพื่อนรับของเข้ามา
แต่หาในระบบไม่เจอ จะคิดว่าระบบมีปัญหาแล้วไปรายงานผิด ๆ

**การกรองสิทธิ์ทำที่ backend ตัวข้อความนี้แค่อธิบาย** — ไม่ใช่ตัวกรอง
(และ `logout` ล้าง cache แล้ว — ช่างที่ล็อกอินต่อจาก admin ในแท็บเดิมไม่เห็นรายการของ admin ค้าง)

**ไม่มีตัวกรองสถานะเหมือนหน้า PO** เพราะใบรับของไม่มีสถานะ
บันทึกแล้วจบ แก้ไม่ได้ (กฎข้อ 5 ในหัวข้อแนวคิด) กุญแจเลยเป็น `["goods-receipts"]` เฉย ๆ

**ปุ่มบันทึกรับของทุกบทบาทเห็น** ตรงกับสิทธิ์ backend (`current_user`)

## 12. `pages/GoodsReceiptNewPage.jsx` — ฟอร์มที่ซับซ้อนที่สุดของเฟสนี้

**ขั้นนี้ทำอะไร** ฟอร์มบันทึกรับของ ที่ต้องรองรับสองโหมดในฟอร์มเดียว
และคำนวณ VAT ให้เห็นสด ๆ ระหว่างกรอก

```
โหมด "ตาม PO"   → เลือก PO → ระบบเติมชื่อร้านและรายการค้างรับให้เอง
โหมด "ซื้อด่วน"  → กรอกชื่อร้านเอง ค้นหาสินค้าเอง
```

**ถ้าอ่านรอบเดียวไม่เข้าใจเป็นเรื่องปกติ** — พิมพ์ตามให้ครบก่อน
แล้วค่อยกลับมาอ่านพร้อมกับกดเล่นในจอจริง

**สร้างไฟล์ใหม่** `frontend/src/pages/GoodsReceiptNewPage.jsx`

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
export default function GoodsReceiptNewPage() {
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
  const vatOf = (it) => (!hasInvoice ? 0 : it.vat_amount !== "" ? Number(it.vat_amount) : autoVat(it));
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
          <p className="mt-1 text-xs text-muted">บันทึกแล้วแก้ไม่ได้ ถ้าจำนวนผิดให้ปรับสต็อก</p>
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
```jsx
const [mode, setMode] = useState(params.get("po") ? "po" : "quick");
const [poId, setPoId] = useState(params.get("po") || "");
```

#### `useQuery` สามตัว — `enabled` คุมว่าจะโหลดเมื่อไหร่

```jsx
useQuery({ queryKey: ["purchase-orders", { status: "open" }], queryFn: ..., enabled: mode === "po" });  // รายการ PO ให้เลือก
useQuery({ queryKey: ["purchase-orders", poId], enabled: mode === "po" && !!poId });                   // PO ที่เลือก
useQuery({ queryKey: ["settings"] });                                                                   // อัตรา VAT
```

**`enabled: false` = ยังไม่ต้องโหลด** — โหมดซื้อด่วนไม่ต้องดึงรายการ PO · ยังไม่เลือก PO ก็ยังไม่ต้องดึงรายละเอียด
พอ `mode` / `poId` เปลี่ยนจน `enabled` เป็น `true` มันดึงให้เอง

กุญแจ `["purchase-orders", poId]` ตรงกับหน้ารายละเอียด PO (ข้อ 10) — กดมาจากหน้านั้นได้ข้อมูลจาก cache ทันที

#### `useEffect` ที่เติมรายการให้อัตโนมัติ

```jsx
setValue("supplier_name", po.data.supplier_name);   // เติมช่องเดียว
replace(po.data.items
  .filter((i) => Number(i.qty_remaining) > 0)        // เอาเฉพาะที่ยังค้างรับ
  .map((i) => ({ ...EMPTY_ITEM, qty: plainNumber(i.qty_remaining), ... })));
//                              ^ เติมจำนวนเท่ายอดค้างไว้ให้เลย
```

| ฟังก์ชัน | ของใคร | ทำอะไร |
|---|---|---|
| `setValue(ชื่อ, ค่า)` | `useForm` | ตั้งค่าช่องเดียวจากโค้ด (แทนที่คนพิมพ์) |
| `replace(อาเรย์)` | `useFieldArray` | แทนที่รายการ**ทั้งชุด**ทีเดียว |
| `append(แถว)` | `useFieldArray` | เพิ่มแถวเดียวท้ายสุด (ใช้ตอนซื้อด่วน) |

**ทำไมเติมให้เท่ายอดค้าง** — เพราะกรณีปกติคือของมาครบตามที่ค้างอยู่
พนักงานกรอกแค่ยอดเงินก็จบ ถ้ามาไม่ครบค่อยแก้จำนวนลง **ทำให้กรณีที่เจอบ่อยที่สุดเร็วที่สุด**

**แถวเก็บ `product_id` `label` `remaining` ไว้ด้วยทั้งที่ไม่มีช่องกรอก** — `useFieldArray` เก็บทั้ง object ที่ใส่เข้าไป
`label` / `remaining` ไว้โชว์ (`field.label`) · `product_id` ไว้ส่ง (`form.items[i].product_id`)
ช่องที่คนกรอกจริงมีแค่ `qty` `total_paid` `vat_amount` ที่ `register` ไว้

**`max={field.remaining}`** เบราว์เซอร์เตือนเองถ้ากรอกเกินยอดค้าง —
เป็นแค่ความสะดวก backend ตรวจซ้ำอยู่ดี (ข้อ 4 ①)

**`plainNumber(i.qty_remaining)` ตอนเติมจำนวน** (เฟส 2 ข้อ 16) — ยอดค้างรับจากฐานมาเป็น `"4.000"`
ตัดศูนย์ท้ายให้เหลือ `"4"` ก่อนใส่ช่อง และได้ string ซึ่งเป็นชนิดที่ช่องกรอก HTML ต้องการ

#### การคำนวณ VAT ที่เห็นสด ๆ ระหว่างกรอก

```jsx
const items = watch("items");          // ค่าล่าสุดทุกแถว
const hasInvoice = watch("has_invoice");  // สวิตช์ใบกำกับ (checkbox ที่ register ไว้)

const autoVat  = (it) => ...   // ถอด VAT แบบเดียวกับ purchase_vat ที่ backend
const vatOf    = (it) => (!hasInvoice ? 0 : it.vat_amount !== "" ? Number(it.vat_amount) : autoVat(it));
const unitCost = (it) => ...   // (ยอดจ่าย − VAT) ÷ จำนวน
```

`watch` ทำให้ตัวเลขข้างล่างอัปเดตทุกตัวอักษรที่พิมพ์ — ส่ง `items[i]` (ค่าล่าสุด) เข้าไปคำนวณ ไม่ใช่ `fields[i]` (สำเนาตอนเพิ่มแถว)

**ตัวเลขทุกตัวในฟอร์มนี้คิดด้วย JS เพื่อ _แสดง_ เท่านั้น**

ส่งไป backend แค่ **ยอดจ่าย · จำนวน · VAT ที่กรอกเอง (ถ้ามี)**
แล้วเซิร์ฟเวอร์คำนวณใหม่ทั้งหมดด้วย `Decimal`

`round2` ของ JS ปัดใกล้เคียงแต่ไม่ใช่ตัวจริง — **ห้ามส่งผลลัพธ์ที่คิดจาก JS
ไปเก็บในฐานเด็ดขาด**

**ทำไมต้องโชว์ต้นทุนต่อหน่วยสด ๆ ทั้งที่เดี๋ยวเซิร์ฟเวอร์ก็คิดให้**

เพราะมันจับพิมพ์ผิดได้ทันที — กรอกยอดจ่ายผิดหลักเป็น 8,560 แทน 856
จะเห็นว่าต้นทุนหัวเทียนกลายเป็นชิ้นละ 2,140 ซึ่งผิดปกติชัดเจน
**ดีกว่าไปรู้ตอนปิดบัญชีสิ้นเดือน**

**`rate` อ่านจาก `useQuery(["settings"])`** ไม่ฝัง `7` ในโค้ด — ใช้ค่าที่ตั้งไว้ในเฟส 2

**ช่อง VAT เว้นว่างได้** placeholder บอกว่าระบบจะคิดให้เท่าไหร่
ส่ง `null` เมื่อว่าง = ให้เซิร์ฟเวอร์ถอด 7/107 เอง

#### บันทึก — invalidate สามกลุ่ม

```jsx
for (const group of ["goods-receipts", "purchase-orders", "products"]) {
  queryClient.invalidateQueries({ queryKey: [group] });
}
```

รับของหนึ่งใบเปลี่ยนสามเรื่องพร้อมกัน: **มีใบรับของใหม่ · ยอดรับของ PO ขยับ (อาจปิดเอง) · สต็อกและ Lot เพิ่ม**
สั่งทีเดียวที่นี่ ทุกหน้าที่เกี่ยวข้องอัปเดตเอง — นี่คือเหตุผลหลักที่เลือกใช้ TanStack Query (เฟส 0)

#### รายละเอียดที่ป้องกันข้อมูลเสีย

**ปิดสวิตช์ใบกำกับ → ส่ง `null` ทั้งชุด**

```jsx
supplier_tax_id: form.has_invoice ? form.supplier_tax_id : null,
supplier_invoice_no: form.has_invoice ? form.supplier_invoice_no : null,
supplier_invoice_date: form.has_invoice ? form.supplier_invoice_date : null,
```

ต่อให้ผู้ใช้เคยพิมพ์ไว้แล้วเปลี่ยนใจปิดสวิตช์ ก็ไม่หลุดไป (react-hook-form ยังจำค่าที่พิมพ์ไว้ แต่เราไม่ส่ง)
**ถ้าส่งไปครึ่ง ๆ จะไปชน CHECK `invoice_date` ที่ฐาน** แล้วได้ error ที่อ่านไม่รู้เรื่อง

**`supplier_invoice_date: todayBangkok()` ใน `EMPTY_RECEIPT`** — ตั้งค่าเริ่มเป็นวันนี้ตามเวลาไทย (ข้อ 6)
ส่วนใหญ่ใบกำกับออกวันเดียวกับที่ไปรับของ

**เขียนเตือน "บันทึกแล้วแก้ไม่ได้" ไว้ก่อนปุ่มกด** — ไม่ใช่ไปบอกทีหลัง
(กฎข้อ 5 ในหัวข้อแนวคิด)

## 13. `pages/GoodsReceiptPage.jsx` — รายละเอียดใบรับของ

```jsx
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { formatDate, formatMoney, formatQty, formatUnitPrice } from "../api";
import { useAuth } from "../auth";
import DetailLayout from "../components/DetailLayout";
import Icon from "../components/Icon";
import StatusBadge from "../components/StatusBadge";

// หน้า /goods-receipts/:id: อ่านอย่างเดียว (บันทึกแล้วแก้ไม่ได้), ต้นทุน/VAT โชว์เฉพาะ admin
export default function GoodsReceiptPage() {
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

### อ่านโค้ดนี้ยังไง

**สังเกตว่าหน้านี้ไม่มีปุ่มแก้ ไม่มีปุ่มลบ ไม่มีเมนู ⋯ เลย**

เพราะ**เอกสารที่บันทึกแล้วแก้ไม่ได้** (กฎข้อ 5) ปุ่มเดียวที่มีคือ
"ดูใบสั่งซื้อ" ที่พากลับไปต้นทาง — ใช้ `btn-secondary` เพราะไม่ใช่งานหลัก
แค่ทางเดินต่อ

**กรอกผิดแล้วทำยังไง** — ไปปรับสต็อกที่หน้าสินค้าแทน (ปุ่มปรับลดจากเฟส 3)
ซึ่งจะทิ้งร่องรอยไว้ในสมุดสต็อกว่าปรับเพราะอะไร **ดีกว่าแก้เอกสารเงียบ ๆ**

**ช่างเปิดใบรับของของคนอื่น** → backend ตอบ 404 (ข้อ 4 router)
→ `useQuery` ได้ `error` → หัวหน้าแสดง "ไม่พบใบรับของ"

ช่างไม่มีทางรู้ว่าใบนั้นมีอยู่จริงหรือเปล่า — ซึ่งเป็นสิ่งที่ตั้งใจ

**`Total`** — กล่องยอดรวมสองกล่องหน้าตาเหมือนกัน แยกเป็นคอมโพเนนต์เล็กท้ายไฟล์ (ท่าเดียวกับ `Fact` ในเฟส 3)

## 14. `pages/PrintPOPage.jsx` — หน้าพิมพ์ใบสั่งซื้อ

**ขั้นนี้ทำอะไร** หน้า A4 สำหรับพิมพ์ใบสั่งซื้อส่งร้าน — หน้าแรกของโปรเจกต์
ที่ออกแบบมาเพื่อกระดาษ ไม่ใช่จอ

**สร้างไฟล์ใหม่** `frontend/src/pages/PrintPOPage.jsx`

```jsx
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { formatDate, formatMoney, formatQty } from "../api";
import Icon from "../components/Icon";

// หน้า A4 /print/po/:id สำหรับพิมพ์หรือบันทึก PDF: GET PO + ค่าตั้งอู่ (หัวกระดาษ), แถบปุ่มซ่อนตอนพิมพ์ด้วย print:hidden
export default function PrintPOPage() {
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

### อ่านโค้ดนี้ยังไง

**ไม่ต้องลงไลบรารีสร้าง PDF เลยสักตัว**

หน้านี้เป็น route ธรรมดา + CSS สำหรับการพิมพ์เท่านั้น

```
พิมพ์ลงกระดาษ  → window.print() → เลือกเครื่องพิมพ์
บันทึกเป็น PDF → window.print() → เลือก "Save as PDF" ในหน้าต่างของเบราว์เซอร์
```

**ทั้งสองอย่างคือคำสั่งเดียวกัน** — เบราว์เซอร์ทุกตัวทำ PDF ได้อยู่แล้ว

**แยกสองชิ้น: `PrintPOPage` (เปลือก + ปุ่ม + โหลด) กับ `PoDocument` (ตัวกระดาษ)**
เปลือกจัดการสามสถานะ (พัง / กำลังโหลด / มีข้อมูล) ส่วน `PoDocument` ได้ `po` ที่มีแน่ ๆ แล้ว ไม่ต้องเช็คซ้ำ

**ข้อมูลสองชุดจาก cache** — `["purchase-orders", id]` (ถ้าเพิ่งเปิดหน้ารายละเอียดมา ได้ทันที) และ `["settings"]`
แต่หน้านี้มักเปิดในแท็บใหม่ ซึ่ง cache เริ่มว่าง — ก็แค่ดึงใหม่ตามปกติ

**`print:` ของ Tailwind = `@media print` — มีผลเฉพาะตอนพิมพ์**

```jsx
className="... print:hidden"      // แถบปุ่ม: เห็นบนจอ หายตอนพิมพ์
className="... print:bg-white"    // พื้นหลังเทาบนจอ ขาวล้วนตอนพิมพ์
className="... print:p-0 print:shadow-none"   // ตัดขอบกับเงาออกตอนพิมพ์
```

ทำให้**ไฟล์เดียวใช้ได้ทั้งดูบนจอและพิมพ์** ไม่ต้องทำสองหน้า

**`max-w-[210mm]`** — 210mm คือความกว้างกระดาษ A4
บนจอเลยเห็นหน้าตาเท่ากระดาษจริง **ดูแล้วรู้เลยว่าพิมพ์ออกมาจะเป็นยังไง**

ส่วนขนาดกระดาษกับขอบ ตั้งไว้แล้วที่ `@page { size: A4; margin: 12mm }` ในข้อ 6

**หัวกระดาษอ่านชื่ออู่จาก `/settings`**

```jsx
{shop?.shop_name || "ชื่ออู่ (ตั้งค่าได้ในหน้าตั้งค่า)"}
```

ยังไม่ได้ตั้ง **ก็บอกไปเลยว่าไปตั้งที่ไหน** ดีกว่าโชว์ที่ว่างเปล่าให้งง
— นี่คือจุดที่หน้าตั้งค่าจากเฟส 2 ได้ใช้จริง (`shop?.` เพราะ settings อาจยังโหลดไม่เสร็จ)

**`break-inside-avoid` บนช่องลายเซ็น** — ห้ามเบราว์เซอร์ตัดกล่องนี้ครึ่งหนึ่ง
ข้ามหน้ากระดาษ ไม่งั้นเส้นลายเซ็นจะอยู่หน้า 1 แต่คำว่า "ผู้สั่งซื้อ" ไปอยู่หน้า 2

**`closePage()` รองรับสองทางที่เปิดมา**

```jsx
const closePage = () => (history.length > 1 ? history.back() : window.close());
//                       เปิดจากในเว็บ → กลับหน้าเดิม    เปิดแท็บใหม่ → ปิดแท็บ
```

> **เขียนหัวกระดาษ ตาราง ลายเซ็นไว้ในไฟล์นี้เลย ยังไม่แยกไฟล์**
> เพราะตอนนี้มีหน้าพิมพ์หน้าเดียว — กฎ "ใช้ 2 ที่ขึ้นไปค่อยแยก"
> เฟส 5 (ใบเสนอราคา) จะมีหน้าที่สอง ค่อยดึงส่วนที่ซ้ำไปทำ `components/PrintLayout.jsx` ตอนนั้น

## 15. เมนูและ route

**ขั้นนี้ทำอะไร** ขั้นสุดท้าย — เพิ่มเมนูสองตัวและผูก URL ของหน้าทั้ง 7 หน้า

**เปิด** `frontend/src/components/AppLayout.jsx` — เติมใน `MENU` ต่อจากสต็อก
(อย่าลืม `group` ไม่งั้นเมนูไม่โผล่)

```jsx
export const MENU = [
  { to: "/stock", label: "สต็อก", icon: "box", group: "คลังสินค้า" },
  { to: "/purchase-orders", label: "สั่งซื้อ", icon: "clipboard", group: "คลังสินค้า" },
  { to: "/goods-receipts", label: "รับของ", icon: "truck", group: "คลังสินค้า" },
];
```

กลุ่ม `"คลังสินค้า"` มีอยู่แล้วตั้งแต่เฟส 3 ไม่ต้องเติม `GROUPS` ซ้ำ

**เปิด** `frontend/src/main.jsx` → เติม import เจ็ดบรรทัด

```jsx
import GoodsReceiptPage from "./pages/GoodsReceiptPage";
import GoodsReceiptNewPage from "./pages/GoodsReceiptNewPage";
import GoodsReceiptsPage from "./pages/GoodsReceiptsPage";
import PrintPOPage from "./pages/PrintPOPage";
import PurchaseOrderPage from "./pages/PurchaseOrderPage";
import PurchaseOrderNewPage from "./pages/PurchaseOrderNewPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
```

→ **หน้าพิมพ์ต้องอยู่นอก AppLayout** เติมใต้บรรทัด `/login`

```jsx
          <Route
            path="/print/po/:id"
            element={
              <Guard roles={STAFF}>
                <PrintPOPage />
              </Guard>
            }
          />
```

→ ส่วนที่เหลือเติม**ใน** layout route ใต้บรรทัด `stock/:id`

```jsx
            <Route path="purchase-orders" element={<PurchaseOrdersPage />}>
              <Route
                path="new"
                element={
                  <Guard roles={STAFF}>
                    <PurchaseOrderNewPage />
                  </Guard>
                }
              />
            </Route>
            <Route path="purchase-orders/:id" element={<PurchaseOrderPage />} />
            <Route path="goods-receipts" element={<GoodsReceiptsPage />}>
              <Route path="new" element={<GoodsReceiptNewPage />} />
            </Route>
            <Route path="goods-receipts/:id" element={<GoodsReceiptPage />} />
```

**อ่านโครง route นี้ยังไง**

**ทำไมหน้าพิมพ์ต้องอยู่นอก layout route**

```jsx
<Route path="/print/po/:id" ... />              ← นอก: ไม่มีเมนูครอบ
<Route element={<Guard><AppLayout /></Guard>}>     ← ใน: ทุกหน้ามีเมนูครอบ
```

เพราะ**กระดาษต้องมีแต่เอกสาร** ถ้าอยู่ใน layout จะมีแถบเมนูติดไปด้วย
(ต่อให้ `print:hidden` ซ่อนได้ ก็ยังเกะกะตอนดูบนจอ)

แต่**ยังต้องล็อกอิน** — สังเกตว่ายังมี `<Guard roles={STAFF}>` ครอบอยู่
แค่ครอบทีละหน้าแทนที่จะครอบทั้งกลุ่ม (ช่างเปิดไม่ได้เพราะจะเห็นราคา)

**รูปแบบ route ของทั้งสองโดเมนเหมือนเฟส 3 เป๊ะ**

```
xxx            → รายการ
  xxx/new      → ลูก: ป๊อปอัพฟอร์ม
xxx/:id        → พี่น้อง: หน้ารายละเอียดเต็มหน้า
```

**สังเกตความต่างของ `Guard` สองที่**

```jsx
<Route path="new" element={<Guard roles={STAFF}><PurchaseOrderNewPage /></Guard>} />  ← สร้าง PO เฉพาะ staff
<Route path="new" element={<GoodsReceiptNewPage />} />                                ← รับของ ทุกบทบาท
```

ตรงกับสิทธิ์ที่ backend ตั้งไว้ในข้อ 4 เป๊ะ ๆ — **หน้าจอกับ backend ต้องตรงกัน
เสมอ** ไม่งั้นผู้ใช้จะกดปุ่มแล้วเจอ 403

---

## เช็คว่าเฟสนี้เสร็จ

### 1. คำสั่งต้องผ่านทั้งสองอัน

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

### 2. เดินตามเรื่องจริงของ PO หนึ่งใบ (ใช้สินค้าจากเฟส 3)

**สั่งของ**

1. สร้าง PO — ผ้าเบรก **10 ชุด** ราคาคาด **350**
   → ไปหน้า PO เห็นป้าย **"รอของ"** แถบความคืบหน้ายังว่าง
2. ⋯ → พิมพ์ใบสั่งซื้อ → เปิดแท็บใหม่ หน้าตาเป็น A4 **มีชื่ออู่ที่ตั้งไว้ในเฟส 2**
   → กด Ctrl+P ดูตัวอย่าง → **ต้องไม่เห็นแถบปุ่มด้านบนในหน้ากระดาษ**

**รับของรอบแรก (ไม่ครบ)**

3. กด "รับของตาม PO นี้" → **รายการเติมมาให้เป็น 10 อัตโนมัติ**
4. แก้เป็น **6** กรอกยอดจ่าย **2,100** → บันทึก
5. กลับหน้า PO → ป้ายเปลี่ยนเป็น **"รับบางส่วน"** ค้าง **4** แถบขึ้นมา 60%
6. ไปหน้าสต็อกผ้าเบรก → **มี Lot ใหม่ "รับของ GR-0000x" ต้นทุน 350**

**ทดสอบกฎรับเกิน**

7. รับอีกรอบ กรอก **5** (เกินค้าง 4) → เบราว์เซอร์เตือนตั้งแต่ในช่อง
8. ลองข้ามหน้าจอ ยิงผ่าน DevTools ตรง ๆ → **ต้องได้ 409 พร้อมบอกยอดค้าง**

**รับครบ**

9. รับ **4** ที่เหลือ → **PO เปลี่ยนเป็น "ปิดแล้ว" เอง** และปุ่มรับของหายไป

**ข้อมูลอัปเดตเอง (TanStack Query) — ไม่ต้องกด F5 สักครั้ง**

10. บันทึกรับของเสร็จ → เด้งไปหน้าใบรับของ → กดกลับไปหน้า PO → **ยอดรับ/ป้ายสถานะเป็นของใหม่แล้ว**
11. ไปหน้าสต็อก → คงเหลือของสินค้าที่เพิ่งรับ **เพิ่มแล้ว** (ถ้ายังเป็นเลขเก่า = `onSuccess` ของหน้ารับของลืม invalidate `["products"]`)
12. ยกเลิก PO จากเมนู ⋯ → กลับไปรายการ PO แท็บ "ยกเลิก" → **ใบนั้นอยู่ในแท็บนี้แล้ว**
13. สร้าง PO → กดเพิ่มสินค้าสามตัว → ลบตัวกลาง → **จำนวนที่พิมพ์ไว้ในแถวที่เหลือไม่สลับกัน** (ทดสอบ `key={field.id}`)

### 3. ทดสอบ VAT และใบกำกับ

**ซื้อด่วน (ไม่อ้าง PO)** — น้ำมันเครื่อง **4 ขวด** จ่าย **856**

- เปิดสวิตช์ใบกำกับ ใส่เลขที่ `iv-001` + เลขผู้เสียภาษีร้าน
- → ช่อง VAT ต้องแสดง **56.00** · ต้นทุน/หน่วย **200.0000**
- บันทึกแล้วเปิดดู → **เลขที่กลายเป็น `IV-001` ตัวใหญ่**

**บันทึกใบกำกับเลขเดิมของร้านเดิมอีกครั้ง**
→ "ใบกำกับภาษีเลขนี้ของร้านนี้ถูกบันทึกแล้ว"

### 4. ทดสอบว่าเมนูแสดงเฉพาะคำสั่งที่ทำได้

| สถานะ PO | เมนู ⋯ ต้องมี |
|---|---|
| ยังไม่เคยรับของ ("รอของ") | **แค่ "ยกเลิก"** (สีแดง) |
| รับไปบางส่วนแล้ว | **แค่ "ปิดก่อนรับครบ"** |
| ปิดแล้ว / ยกเลิกแล้ว | ไม่มีทั้งคู่ |

### 5. ทดสอบสิทธิ์

**ล็อกอินเป็น `emp1` (พนักงาน)**

- ออก PO ได้ · **เห็นราคาคาดบน PO**
- แต่เปิดใบรับของ → **ไม่เห็นต้นทุนและ VAT**

**ล็อกอินเป็น `mech1` (ช่าง)**

- ไม่มีปุ่มสร้าง PO
- เปิดดู PO ได้ แต่ **ไม่เห็นราคาคาดเลย**
- **บันทึกซื้อด่วนได้** (ช่างขับไปซื้อของจริง)
- รายการรับของ → **เห็นแค่ใบที่ตัวเองบันทึก** พร้อมข้อความบอกว่าทำไม
- ลองเดา URL เปิดใบของคนอื่น → **"ไม่พบใบรับของ"**

### 6. มือถือ

- กด ☰ → เห็นเมนูครบสามตัวใต้หัวข้อ "คลังสินค้า": สต็อก · สั่งซื้อ · รับของ
- ฟอร์มรับของ → เลื่อนดูในแผ่นป๊อปอัพได้ **ปุ่มบันทึกอยู่ล่างเสมอ**

## git

```
docker compose run --rm api ruff check --fix .
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A && git commit -m "feat: purchase orders and goods receipts"
```
