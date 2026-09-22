# เฟส 3 — สินค้า + Lot สต็อก

**จบเฟสนี้แล้วจะทำอะไรได้**

- เพิ่ม / แก้สินค้าได้
- ใส่สต็อกตั้งต้นตอนเริ่มใช้ระบบได้
- เห็นของแต่ละรอบที่ซื้อเข้ามาเป็น **Lot** แยกต้นทุนกัน
- ปรับเพิ่ม / ปรับลดสต็อกได้ โดย**บังคับกรอกเหตุผล**
- เปิดดูสมุดสต็อกว่าใครทำอะไรเมื่อไหร่
- **พนักงานกับช่างไม่เห็นต้นทุน** (เห็นแต่ราคาขาย)

## เฟสนี้ข้อมูลเดินยังไง (อ่าน 1 นาที)

```
พนักงานเพิ่มสินค้า / ใส่สต็อกตั้งต้น / ปรับเพิ่ม-ลด (ต้องกรอกเหตุผล)
   ↓ หน้าจอส่งไป POST /api/products · POST /api/stock/adjust-up · adjust-down
backend ล็อกไม่ให้สองคนแก้สต็อกพร้อมกัน แล้วเช็คว่าของพอไหม
   ↓ ผ่าน → เขียนสองที่พร้อมกันเสมอ
   stock_lots      "ของก้อนนี้ รับมา 5 ต้นทุนชิ้นละ 100 ตอนนี้เหลือ 3"
   stock_movements "22 ก.ย. สมชาย ปรับลด 2 เพราะของเสีย"   ← เพิ่มอย่างเดียว ห้ามแก้ ห้ามลบ
   ↓
คงเหลือของสินค้า = บวกยอดเหลือของทุก Lot สด ๆ ตอนอ่าน (ไม่ได้เก็บเป็นตัวเลขไว้)
```

- **ทำไมต้องแยกเป็น Lot** ของรอบนี้กับรอบที่แล้วต้นทุนไม่เท่ากัน ถ้ารวมเป็นก้อนเดียวจะตอบไม่ได้ว่ากำไรเท่าไหร่
- **ใครเห็นต้นทุน** เฉพาะ admin — backend ไม่ส่งต้นทุนออกมาเลยสำหรับคนอื่น ไม่ใช่แค่ซ่อนบนจอ
- **แก้ประวัติไม่ได้** ของหาย/นับผิด ให้ปรับสต็อกพร้อมเหตุผล แล้วมันจะโผล่ในสมุดสต็อก
- **หน้าจอไม่ต้องจำว่าต้องโหลดอะไรใหม่** บันทึกเสร็จสั่งครั้งเดียวว่า "ข้อมูลสินค้าเก่าแล้ว" ทุกส่วนอัปเดตเอง

**อ่านก่อนเริ่ม** `new_scenario_summary.md` หัวข้อ 4 · `data_model.md` หัวข้อ 3

**เฟสนี้ยังไม่ทำ**
- **การเบิกของออกแบบ FIFO (`issue_fifo`) และคืนของ (`return_issued`)** — ยังไม่มีอะไรให้เบิกเข้า (ใบงานเฟส 5 / ขายหน้าร้านเฟส 6) ค่อยเขียนตอนนั้น แต่ Lot ในเฟสนี้**เรียงตามลำดับ FIFO แล้ว**ตั้งแต่วันแรก
- รับของจากผู้ขาย (`receive`) — เฟส 4 จะกลับมาแก้ตาราง Lot เพิ่มคอลัมน์ใบรับของและ VAT ซื้อ
- รอบเปลี่ยนบำรุงรักษาของสินค้า (เฟส 8)

---

## แนวคิดที่ต้องเข้าใจก่อนเขียนโค้ด

**อ่านหัวข้อนี้ให้เข้าใจก่อน อย่าเพิ่งพิมพ์โค้ด** — ถ้าไม่เข้าใจว่าทำไมต้องมี Lot
โค้ดทั้งเฟสจะดูซับซ้อนเกินจำเป็นไปหมด

### ปัญหา: "คงเหลือ 10 ชิ้น" ไม่พอ

ระบบสต็อกทั่วไปเก็บคงเหลือเป็นตัวเลขตัวเดียว **ระบบนี้ไม่ทำแบบนั้น** เพราะ:

```
เดือนที่แล้ว  ซื้อหัวเทียน 5 ชิ้น  ต้นทุนชิ้นละ 80
เดือนนี้      ซื้อหัวเทียน 5 ชิ้น  ต้นทุนชิ้นละ 120
```

ถ้าเก็บรวมเป็น "มี 10 ชิ้น ต้นทุนเฉลี่ย 100" แล้ววันนี้ขายไป 1 ชิ้นในราคา 150
กำไรคือเท่าไหร่ — 50 หรือ 70 ตอบไม่ได้ เพราะ**ไม่รู้ว่าหยิบชิ้นจากก้อนไหนไป**
ตัวเลขกำไรที่ได้จะเป็นตัวเลขสมมติ

ทางแก้คือ**เก็บของแต่ละรอบที่ซื้อเข้ามาแยกก้อนกัน** ก้อนหนึ่งเรียกว่า **Lot**

| ตาราง | เปรียบเหมือน | เก็บอะไร |
|---|---|---|
| `products` | ป้ายชื่อของบนชั้น | รหัส ชื่อ หน่วย ราคาขาย จุดเตือนขั้นต่ำ |
| `stock_lots` | **ก้อนของแต่ละรอบ** | รับมากี่ชิ้น · **เหลือกี่ชิ้น** · ต้นทุนต่อชิ้นของรอบนั้น |
| `stock_movements` | **สมุดเดินบัญชี** | ทุกการเข้า/ออก (+/−) · **เพิ่มได้อย่างเดียว ห้ามแก้ ห้ามลบ** |

```
stock_lots                                stock_movements
┌─────┬──────┬──────┬────────┐           ┌───┬─────┬──────┬──────────┐
│ Lot │ รับ   │ เหลือ │ ต้นทุน  │           │ # │ Lot │ qty  │ ประเภท    │
├─────┼──────┼──────┼────────┤           ├───┼─────┼──────┼──────────┤
│  1  │  2   │  1   │   80   │  ◄────────│ 1 │  1  │  +2  │ opening  │
│  2  │  3   │  3   │  120   │  ◄────────│ 2 │  2  │  +3  │ adjust   │
└─────┴──────┴──────┴────────┘      ┌────│ 3 │  1  │  −1  │ adjust   │ ← ปรับลด (แตกหัก)
  คงเหลือรวม = 1 + 3 = 4 ชิ้น        └────└───┴─────┴──────┴──────────┘
```

### กฎสามข้อที่โค้ดทั้งเฟสยึด

**1. ยอดคงเหลือของสินค้า = ผลรวมช่อง "เหลือ" ของทุก Lot**

ไม่มีคอลัมน์ `stock_qty` ในตาราง `products` — ตั้งใจ
เพราะถ้ามีสองที่เก็บตัวเลขเดียวกัน วันหนึ่งมันจะไม่ตรงกันแน่นอน
(โค้ดอัปเดตที่หนึ่งแต่ลืมอีกที่) แล้วไม่มีใครรู้ว่าอันไหนถูก

**คำนวณเอาจากของจริงทุกครั้ง ช้ากว่านิดเดียวแต่ไม่มีวันผิด**

**2. ผลรวม movement ของ Lot หนึ่ง = ช่อง "เหลือ" ของ Lot นั้นเสมอ**

สมุด `stock_movements` คือ**หลักฐาน**ว่าตัวเลขคงเหลือมาจากไหน
ถ้าวันหนึ่งตัวเลขดูแปลก เปิดสมุดไล่ดูได้ว่าใครทำอะไรเมื่อไหร่

นี่คือเหตุผลที่สมุด **เพิ่มได้อย่างเดียว ห้ามแก้ ห้ามลบ** — แก้ได้เมื่อไหร่
มันก็ไม่ใช่หลักฐานอีกต่อไป (หลักการเดียวกับที่ไม่ลบผู้ใช้ในเฟส 2)

**3. Lot เรียงเก่าสุดก่อนเสมอ (`created_at`, `id`)**

เฟส 5 ที่เริ่มตัดของออก จะไล่หยิบจาก Lot แรกก่อน — เรียกว่า **FIFO**
(First In First Out ของเข้าก่อนออกก่อน) ซึ่งตรงกับที่คนในอู่หยิบของจริง
คือหยิบของเก่าก่อน

เฟสนี้ยังไม่มีการตัดออก แต่**เรียงถูกไว้ตั้งแต่วันแรก** เฟส 5 จะได้ไม่ต้องรื้อ

| `movement_type` | ความหมาย | เครื่องหมาย | มีตั้งแต่ |
|---|---|:---:|---|
| `opening` | สต็อกตั้งต้น (ตอนเริ่มใช้ระบบ) | + | เฟส 3 |
| `adjust` | ปรับจากการนับของ **ต้องมีเหตุผล** | + หรือ − | เฟส 3 |
| `receive` | รับของจากผู้ขาย | + | เฟส 4 |

---

# ส่วน backend

## 1. `app/db.py` — เติม `lock_shop`

**ขั้นนี้ทำอะไร** กันไม่ให้สองคนแก้สต็อกพร้อมกันจนตัวเลขเพี้ยน

**เปิด** `backend/app/db.py` → แก้บรรทัด import ให้มี `text`

```python
from sqlalchemy import MetaData, create_engine, text
```

→ แล้วเติมโค้ดนี้ **ก่อน** ฟังก์ชัน `get_or_404` ที่เขียนไว้ในเฟส 2

```python
SHOP_LOCK = 71001


def lock_shop(db):
    """อู่สาขาเดียว ล็อกตัวเดียวพอ: คำสั่งที่แตะสต็อก จัดซื้อ บิล ทำทีละคำสั่ง"""
    db.execute(text("select pg_advisory_xact_lock(:k)"), {"k": SHOP_LOCK})
```

### ปัญหาที่ฟังก์ชันนี้แก้

พนักงานสองคนกดปรับลดสต็อกตัวเดียวกันพร้อมกันเป๊ะ ๆ (ของเหลือ 3 ชิ้น):

```
เวลา   คนที่ 1                      คนที่ 2
0.00   อ่านค่า → เหลือ 3
0.01                                อ่านค่า → เหลือ 3      ← อ่านก่อนคนแรกเขียน
0.02   3 − 2 = 1  เขียนลงฐาน
0.03                                3 − 2 = 1  เขียนทับ
ผล     ตัดของออกไป 4 ชิ้น แต่ฐานบอกว่าเหลือ 1 (ควรเป็น −1 คือไม่พอ ต้องปฏิเสธ)
```

ของหาย 2 ชิ้นโดยไม่มีใครรู้ เรียกปัญหาแบบนี้ว่า **race condition**

`pg_advisory_xact_lock` ทำให้คำสั่งที่สอง**รอ**จนคำสั่งแรกจบสมบูรณ์ก่อน
แล้วค่อยอ่านค่าใหม่ (ตอนนั้นเหลือ 1 → คำนวณได้ว่าไม่พอ → ปฏิเสธถูกต้อง)

### สามเรื่องที่ควรรู้

**ทำไมล็อก "ทั้งอู่" ไม่ล็อกเฉพาะแถวที่แก้**

ล็อกแถวดูประหยัดกว่า แต่ใช้ไม่ได้กับกฎบางข้อที่**ไม่มีแถวให้ล็อก**:

- "เลขบิลถัดไปคือเลขอะไร" (เฟส 6) — ยังไม่มีแถวนั้นในฐาน
- "รับของเกินยอดที่สั่งไว้ไหม" (เฟส 4) — ต้องรวมหลาย Lot ถึงจะรู้

ล็อกตัวเดียวทั้งอู่ง่ายกว่ามากและ**ไม่มีวันลืมล็อก** ส่วนเรื่องช้า —
อู่เดียวไม่มีคนกดพร้อมกันเยอะพอที่จะรู้สึก

**`_xact_` ตรงกลางชื่อสำคัญมาก**

| ฟังก์ชัน | ปลดล็อกเมื่อ |
|---|---|
| `pg_advisory_xact_lock` ✅ | จบทรานแซกชันเอง (ทั้ง commit และ rollback) |
| `pg_advisory_lock` ❌ | ต้องสั่งปลดเอง |

ใช้ตัวล่างแล้วโค้ดพังกลางทางก่อนถึงบรรทัดปลดล็อก → **ล็อกค้างถาวร
ทั้งระบบหยุดทำงาน** ต้องเข้าไปปลดที่ฐานเอง

**`SHOP_LOCK = 71001` เป็นเลขอะไรก็ได้** ขอแค่ไม่ชนกับล็อกอื่นในฐานเดียวกัน

## 2. `app/models.py` — เพิ่มสามตาราง

**ขั้นนี้ทำอะไร** สร้างตารางตามแนวคิดข้างบน: `products` (ป้ายชื่อของ) ·
`stock_lots` (ก้อนของแต่ละรอบ) · `stock_movements` (สมุดเดินบัญชี)

**เปิด** `backend/app/models.py` → แก้บรรทัด import และเพิ่มชนิดข้อมูลกลางไว้บนสุด

```python
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


def fk(target, **kw):
    """คอลัมน์ foreign key ไปยัง target พร้อม index"""
    return mapped_column(ForeignKey(target, **kw), index=True)
```

**`def fk(target, **kw)` — ตัวช่วยที่ใส่ `index=True` ให้ทุก foreign key**

FK (foreign key) คือคอลัมน์ที่ชี้ไปหาแถวในอีกตาราง เช่น `stock_lots.product_id`
ชี้ไปหา `products.id`

**Postgres ไม่สร้าง index ให้ FK เอง** ต้องสั่งเอง และเราถามย้อนกลับตลอดเวลา
("Lot ทั้งหมดของสินค้าตัวนี้" · "เอกสารที่คนนี้ทำ") ถ้าไม่มี index
ฐานต้องไล่อ่านทั้งตารางทุกครั้ง

ห่อไว้เป็นฟังก์ชันแบบนี้แล้ว**ลืมใส่ไม่ได้** ตารางเฟสนี้เป็นตารางแรกที่มี FK จริง

**สามชนิดตัวเลข — ทำไมทศนิยมไม่เท่ากัน**

| ชนิด | ใช้กับ | ทำไมตำแหน่งเท่านี้ |
|---|---|---|
| `MONEY` = Numeric(12,2) | ยอดรวม · ต้นทุนรวม | เงินไทยมีสตางค์ 2 ตำแหน่ง |
| `PRICE` = Numeric(14,4) | ราคา/ต้นทุน **ต่อหน่วย** | มาจากการหาร ต้องละเอียดกว่าผลลัพธ์ |
| `QTY` = Numeric(12,3) | จำนวน | ของในอู่นับเป็นชิ้น/ขวด (จำนวนเต็ม) แต่เปิดทางไว้เผื่อวันที่มีของตวง/ชั่ง เช่นน้ำมันถัง หรือสายไฟเป็นเมตร |

**ทำไม `PRICE` ต้องละเอียดกว่า `MONEY`** — เพราะมันมาจากการหาร:

```
จ่ายไป 1,000 บาท ได้ของ 3 ชิ้น
ต้นทุนต่อชิ้น = 333.3333     ← เก็บ 4 ตำแหน่ง
ต้นทุนรวม 3 ชิ้น = 1,000.00  ← คูณกลับแล้วได้เท่าเดิม ✅
```

ถ้าเก็บต้นทุนต่อชิ้นแค่ 2 ตำแหน่ง (333.33) คูณกลับจะได้ 999.99 —
หายไปสตางค์นึงทุกครั้ง สะสมเป็นพันรายการแล้วยอดไม่ตรง

**หลักการทั่วไป: ค่าที่มาจากการหาร ต้องเก็บละเอียดกว่าค่าที่เป็นผลลัพธ์สุดท้าย**

> **ฐานเติมศูนย์ให้ครบตามที่ประกาศเสมอ** — `numeric(14,4)` เก็บ `150` เป็น `150.0000`
> และ pydantic ส่งออกเป็น**ข้อความ** `"150.0000"` (ไม่ใช่ตัวเลข JSON เพราะจะกลายเป็น float แล้วความแม่นหาย)
> เป็นเรื่องปกติของการเก็บ ไม่ใช่บั๊ก — ฝั่งหน้าจอมีตัวแปลงให้คนอ่าน/พิมพ์ต่อ (`plainNumber` เฟส 2 · `formatUnitPrice` ข้อ 7)

เติมท้ายไฟล์

```python
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
        CheckConstraint("(movement_type = 'opening' and qty > 0) or (movement_type = 'adjust' and qty <> 0)", name="direction"),
        CheckConstraint("movement_type <> 'adjust' or reason is not null", name="adjust_reason"),
    )
```

### อ่านโค้ดนี้ยังไง

**`qty_received` กับ `qty_remaining` แยกกันทำไม ในเมื่อตอนสร้างค่าเท่ากัน**

```
qty_received   รับเข้ามาเท่าไหร่  → ตั้งครั้งเดียว ไม่เปลี่ยนอีกตลอดกาล
qty_remaining  ตอนนี้เหลือเท่าไหร่ → ลดลงทุกครั้งที่ตัดของออก
```

มีทั้งคู่แล้วตอบได้ว่า "Lot นี้ใช้ไปแล้วเท่าไหร่" (`received − remaining`)
ถ้าเก็บแค่ตัวเดียวจะตอบไม่ได้

**CHECK ของ `stock_lots` แต่ละตัวกันอะไร**

| CHECK | กันอะไร |
|---|---|
| `qty_remaining >= 0` | ตัดของออกเกินที่มี |
| `qty_remaining <= qty_received` | เหลือมากกว่าที่เคยรับเข้ามา (เป็นไปไม่ได้) |
| `unit_cost >= 0 and cost_total >= 0` | ต้นทุนติดลบ |

ย้ำหลักการจากเฟส 1: **โค้ดคำนวณพลาดเมื่อไหร่ ฐานปฏิเสธก่อนที่ข้อมูลเสียจะลงไป**

> **Lot ไม่มีช่องเหตุผลของตัวเอง** — Lot ทุกตัวเกิดพร้อม movement แถวแรก
> และเหตุผลอยู่ที่ movement แถวนั้นแล้ว เก็บซ้ำบน Lot ก็เป็นข้อมูลชุดเดียวกันสองที่
> **เฟส 4 จะกลับมาแก้ CHECK `source_type`** เพิ่มค่า `receipt`
> (นี่คือที่ที่ `naming_convention` จากเฟส 1 จะได้ใช้จริง)

**CHECK ทิศทางของ `stock_movements` — ตัวที่จับบั๊กที่หายากที่สุด**

```sql
(movement_type = 'opening' and qty > 0) or (movement_type = 'adjust' and qty <> 0)
```

`opening` (ตั้งต้น) ต้องเป็นบวกเสมอ · `adjust` เป็นบวกหรือลบก็ได้ แต่ห้ามเป็น 0

**กันบั๊กสลับเครื่องหมาย** ซึ่งเป็นบั๊กที่หายากมากเพราะยอดรวมยังดู
"สมเหตุสมผล" อยู่ ไม่มีอะไรดูผิดปกติจนกว่าจะมานั่งไล่ทีละรายการ

**`Index("ix_stock_lots_fifo", "product_id", "created_at", "id")`**

ลำดับคอลัมน์ใน index ต้องตรงกับ query ที่ใช้จริง:

```sql
WHERE product_id = ?  ORDER BY created_at, id
--    ^ตัวแรก          ^ตัวที่สอง  ^ตัวที่สาม
```

ใช้ทั้งหน้าแสดง Lot ในเฟสนี้ และการตัด FIFO ในเฟส 5

**`column_property` — ช่องที่คำนวณสด ๆ ทุกครั้งที่อ่าน**

```python
Product.qty_on_hand
# → (select coalesce(sum(qty_remaining), 0) from stock_lots where product_id = products.id)
```

เขียนแบบนี้แล้ว `p.qty_on_hand` ใช้ได้เหมือนคอลัมน์ธรรมดาทุกอย่าง
แต่จริง ๆ มันคือ subquery ที่วิ่งไปพร้อม query หลัก

**นี่คือการทำตามกฎข้อ 1 ในหัวข้อแนวคิด** — ไม่เก็บยอดคงเหลือเป็นคอลัมน์จริง
คำนวณเอาทุกครั้ง **ยอดเลยถูกเสมอโดยไม่ต้องคอยดูแลให้ตรง**

- `coalesce(..., 0)` — สินค้าที่ยังไม่มี Lot เลยได้ `0` ไม่ใช่ `None`
  (ไม่ใส่แล้วหน้าจอจะโชว์ค่าว่างแทนเลข 0)
- `correlate_except(StockLot)` — บอก SQLAlchemy ว่า `products` ที่อ้างถึง
  ข้างใน คือแถวจาก query ข้างนอก ไม่ใช่ตารางใหม่
- **ต้องเขียนหลังคลาส `StockLot`** เพราะอ้างถึงมัน เขียนก่อนจะ error

> บรรทัด `# ponytail:` ในโค้ดเป็นการจดไว้ว่ารู้ตัวว่าวิธีนี้มีเพดาน
> (subquery ต่อหนึ่งแถวสินค้า) แต่พอสำหรับแคตตาล็อกขนาดอู่เดียว
> ถ้าวันหนึ่งสินค้าเป็นหมื่นรายการค่อยกลับมาดู

**ไม่มีปุ่มลบสินค้า** — เลิกขายแล้วใช้ `is_active = false`
เพราะ Lot และเอกสารเก่ายังอ้างถึงสินค้าตัวนั้นอยู่ (กฎเดียวกับผู้ใช้ในเฟส 2)

### migration

```
docker compose run --rm api alembic revision --autogenerate -m "products lots and movements"
```

**เปิดไฟล์ที่ได้อ่านก่อน upgrade** เช็คว่ามีครบ:

- CHECK ทุกตัว — `ck_products_*` · `ck_stock_lots_*` · `ck_stock_movements_*`
- `op.create_index('ix_stock_lots_fifo', ...)`

ขาดตัวไหนแปลว่า `models.py` ยังไม่ถูก กลับไปแก้แล้วลบไฟล์ migration นี้สร้างใหม่

ครบแล้วค่อย:

```
docker compose run --rm api alembic upgrade head
```

## 3. `app/money.py` — สูตรเงิน (ไฟล์ใหม่)

**ขั้นนี้ทำอะไร** รวมสูตรที่เกี่ยวกับตัวเลขเงินไว้ที่เดียว

**สร้างไฟล์ใหม่** `backend/app/money.py`

```python
from decimal import ROUND_HALF_UP, Decimal


def round_money(x) -> Decimal:
    """ปัดเงินเป็นทศนิยม 2 ตำแหน่งแบบปัดครึ่งขึ้น"""
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def format_qty(d) -> str:
    """แปลงจำนวนเป็นข้อความไม่มีศูนย์ท้าย (เช่น 2.500 → "2.5") ใช้ในข้อความ error"""
    return f"{Decimal(d).normalize():f}"
```

**ชื่อบอกว่าทำอะไร** — `round_money(x)` อ่านแล้วรู้ทันทีว่าปัดเงิน ไม่ต้องจำว่าชื่อย่อ ๆ อย่าง `q2` ("quantize 2 ตำแหน่ง") หมายถึงอะไร

**ทำไมต้องแยกเป็นไฟล์ของตัวเอง ทั้งที่มีแค่สองฟังก์ชัน**

- ทุกสูตรเงินอยู่ที่เดียว วันที่สูตรเปลี่ยนรู้ทันทีว่าต้องแก้ตรงไหน
- **ทดสอบได้โดยไม่ต้องมีฐานข้อมูลเลย** — ไม่มี import อะไรนอกจาก `decimal`
- เฟส 4 จะมาเติมอีกหลายตัว (ถอด VAT, คิดยอดรวม)

**`round_money` ใช้ `ROUND_HALF_UP` — ไม่ใช่ค่าเริ่มต้นของ python**

| วิธีปัด | `2.345` ได้ | ใครใช้ |
|---|---|---|
| `ROUND_HALF_UP` (ที่เราใช้) | `2.35` | คนไทย นักบัญชี |
| `ROUND_HALF_EVEN` (ค่าเริ่มต้น) | `2.34` | ธนาคาร (ปัดไปหาเลขคู่) |

ค่าเริ่มต้นของ python ปัด .5 ไปหาเลขคู่ ซึ่ง**ไม่ตรงกับที่นักบัญชีคิดมือ**
พอยอดในระบบไม่ตรงกับที่เจ้าของอู่กดเครื่องคิดเลข จะกลายเป็นเรื่องใหญ่

**`format_qty` — ทำเลขให้อ่านง่ายในข้อความ error**

```python
Decimal("2.000")  → "2"      normalize() ตัดศูนย์ท้ายทิ้ง
Decimal("0.500")  → "0.5"
Decimal("100")    → "100"    :f กันไม่ให้กลายเป็น "1E+2"
```

`:f` สำคัญ — ไม่ใส่แล้ว `normalize()` จะเปลี่ยน `100` เป็น `1E+2`
ซึ่งผู้ใช้อ่านไม่รู้เรื่องแน่นอน

### `tests/test_money.py` — เขียนเทสต์ก่อนเลย

ฟังก์ชันสองตัวนี้ไม่ต้องพึ่งฐานข้อมูล เลยเป็นที่แรกในโปรเจกต์ที่เขียนเทสต์
ได้ทันทีโดยไม่ต้องรอส่วนอื่นเสร็จ

**สร้างไฟล์ใหม่** `backend/tests/test_money.py`

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

> `Decimal("100")` ส่งเป็น string ตั้งใจ — เทสต์ว่าค่าที่มาจากฐาน (ซึ่งเป็น Decimal จาก string) ไม่กลายเป็น `1E+2`
> ruff จะเสนอให้เขียน `Decimal(100)` (กฎ FURB157) เราปิดกฎนั้นไว้ใน `ruff.toml` แล้ว (เฟส 0)

## 4. `app/schemas.py` — เติม `serialize_for_role`

**ขั้นนี้ทำอะไร** ฟังก์ชันสามบรรทัดที่เป็นหัวใจของ "พนักงานกับช่างไม่เห็นต้นทุน"

**เปิด** `backend/app/schemas.py` → เติมท้ายไฟล์

```python
def serialize_for_role(user, admin_schema, schema, obj):
    """ต้นทุนออกจากเซิร์ฟเวอร์เฉพาะตอนที่คนขอเป็น admin"""
    return (admin_schema if user.role == "admin" else schema).model_validate(obj)
```

**อ่านโค้ดนี้ยังไง**

ชื่อบอกตรง ๆ: **แปลงข้อมูลออก (serialize) ตามบทบาทของคนที่ขอ** — เลือก schema แล้วแปลงด้วยตัวที่เลือก

```python
serialize_for_role(user, LotAdminOut, LotOut, lot)
#                        ^admin ได้อันนี้  ^คนอื่นได้อันนี้
```

**ทำไมวิธีนี้ถึงกันได้จริง** — จำกฎจากเฟส 1 ได้ไหมว่า pydantic ส่งออกเฉพาะ
ช่องที่ประกาศไว้ `LotOut` ไม่มีช่อง `unit_cost` เลย

แปลว่าสำหรับพนักงาน **ต้นทุนไม่ได้ถูก "ซ่อน" — มันไม่เคยออกจากเซิร์ฟเวอร์เลย**

```
ช่างเปิด DevTools → แท็บ Network → ดู response ดิบ ๆ → ไม่มีคำว่า unit_cost อยู่เลย
```

ต่างจากการซ่อนที่หน้าจอ (`{isAdmin && <td>{cost}</td>}`) ซึ่งข้อมูลส่งไปถึง
เบราว์เซอร์แล้ว แค่ไม่วาดออกมา — เปิด DevTools ก็เห็น

**ทำไมอยู่ใน `schemas.py` กลาง ไม่อยู่ใน `stock/`** เพราะเฟส 4 (ใบรับของ)
ใช้ด้วย — ตามกฎเดิม ใช้ 2 ที่ขึ้นไปก็ย้ายมาที่กลาง

## 5. โดเมน `app/stock/`

**ขั้นนี้ทำอะไร** API ของสินค้าและสต็อกทั้งหมด โครง 3 ไฟล์เหมือนเฟส 1-2
(`schemas` → `service` → `router`)

**สร้างโฟลเดอร์ `backend/app/stock/` พร้อม `__init__.py` ว่าง** เหมือนเดิม

### `stock/schemas.py`

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal

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


class AdjustUpIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, decimal_places=4)
    reason: str = Field(min_length=1)
    source_type: Literal["adjustment", "opening"]
```

**อ่านโค้ดนี้ยังไง**

**คู่ `LotOut` / `LotAdminOut` — รูปแบบที่ใช้ทั้งโปรเจกต์**

```python
class LotOut(Out):           # ทุกคนเห็น: จำนวน วันที่
    ...
class LotAdminOut(LotOut):   # สืบทุกช่องข้างบน แล้วเติมต้นทุนเข้าไป
    unit_cost: Decimal
    cost_total: Decimal
```

เขียนแบบสืบทอดแบบนี้ ช่องทั่วไปไม่ต้องพิมพ์ซ้ำ และ**เพิ่มช่องใหม่ทีหลัง
ไม่มีทางลืมใส่ในตัวใดตัวหนึ่ง** (เพิ่มที่ `LotOut` แล้ว Admin ได้ตามอัตโนมัติ)

ทุกที่ในระบบที่มีต้นทุนจะมี schema คู่แบบนี้เสมอ แล้วใช้คู่กับ `serialize_for_role` ข้อ 4

**`ProductOut` ไม่มีช่องต้นทุนเลยสักช่อง — ไม่ใช่เพราะกันช่าง**

เพราะ**ต้นทุนไม่ได้อยู่ที่สินค้า มันอยู่ที่ Lot** สินค้าตัวหนึ่งมีหลายต้นทุน
พร้อมกัน (หัวเทียน 80 กับ 120 จากตัวอย่างตอนต้น) จะใส่ช่องเดียวก็ไม่รู้จะใส่ค่าไหน

**`ProductOut(ProductIn, Out)` สืบสองตัว** ตามตารางในเฟส 1 — ได้ช่องทั้งหมด
จากขาเข้ามาเลย แล้วเติม `id` กับ `qty_on_hand` (ที่มาจาก `column_property`)

**`AdjustDownIn` กับ `AdjustUpIn` รับคนละอย่าง**

| | รับอะไร | เพราะ |
|---|---|---|
| ปรับ**ลด** | `lot_id` | ต้องบอกว่าตัดจากก้อนไหน |
| ปรับ**เพิ่ม** | `product_id` + `unit_cost` | สร้าง Lot **ก้อนใหม่** ต้องรู้ต้นทุน |

ปรับเพิ่มไม่ใช่การเติมของเข้าก้อนเดิม เพราะของที่เพิ่งเจอ/เพิ่งซื้อมีต้นทุน
ของตัวเอง ต้องแยกก้อน ไม่งั้นต้นทุนก้อนเดิมจะเพี้ยน

`qty: Decimal = Field(gt=0)` ทั้งคู่ — **รับเป็นบวกเสมอ** ส่วนจะบวกหรือลบ
เป็นเรื่องของ service ตัดสินจากชื่อฟังก์ชัน ไม่ใช่ให้หน้าจอส่งเลขติดลบมา
(กันบั๊กเครื่องหมายสลับตั้งแต่ขอบนอก)

**`reason: str = Field(min_length=1)` — บังคับกรอกเหตุผล**

ใช้คู่กับ `In` ที่ตัดช่องว่างหัวท้ายให้ (เฟส 1) ผลคือ **เคาะ space อย่างเดียว
ก็ไม่ผ่าน** เพราะตัดแล้วเหลือความยาว 0

**`decimal_places` ต้องตรงกับที่ฐานเก็บ** — `3` บนจำนวน · `4` บนต้นทุน
ไม่ใส่แล้วค่าที่ละเอียดเกินจะโดนฐานปัดเงียบ ๆ ตอนบันทึก (ปัญหาเดียวกับ
`vat_rate` ในเฟส 2)

### `stock/service.py`

```python
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
```

### อ่าน `save_product`

**ฟังก์ชันเดียวใช้ทั้งสร้างและแก้** ตัดสินจาก `product_id`:

```python
product = get_or_404(...) if product_id else Product()
#         ^มี id = แก้ของเดิม      ^ไม่มี = สร้างใหม่
```

**บรรทัดเช็ครหัสซ้ำมีลูกเล่นอยู่**

```python
.where(Product.code == data.code, Product.id != product_id)
#                                 ^ "ไม่นับตัวเอง"
```

ตอน**แก้** — ไม่งั้นแก้ชื่อสินค้าโดยไม่แตะรหัส จะเจอรหัสตัวเองแล้วฟ้องว่าซ้ำ

ตอน**สร้าง** `product_id` เป็น `None` → กลายเป็น `Product.id != NULL`
ซึ่งใน SQL ให้ผลเป็น NULL (ไม่จริง) สำหรับทุกแถว → **ไม่ตัดแถวไหนทิ้งเลย**
พอดีกับที่ต้องการคือเทียบกับทุกแถว

**`db.refresh(product)` ทำไมต้องมี** — เพื่อดึง `qty_on_hand` มาใหม่
เพราะมันเป็น `column_property` (subquery) ไม่ใช่ค่าที่อยู่ในหน่วยความจำ
ไม่ refresh แล้วค่าที่ส่งกลับไปหน้าจอจะเป็นค่าเก่า

### ห้ามเปลี่ยนหน่วยหลังมีของเข้าคลังแล้ว

```python
has_lots = product_id and db.scalar(select(StockLot.id).where(...).limit(1))   # แก้ของเดิม และมี Lot แล้ว?
if has_lots and data.unit != product.unit:                                      # แล้วหน่วยเปลี่ยน?
    raise HTTPException(409, "เปลี่ยนหน่วยไม่ได้ เพราะสินค้านี้มีของเข้าคลังแล้ว")
```

**ตั้งชื่อ `has_lots` ก่อนค่อย `if`** — เงื่อนไขสามท่อนต่อกันในบรรทัดเดียวต้องอ่านสองรอบ
แยกคำถาม "มีของเข้าคลังแล้วไหม" ออกมาเป็นตัวแปรที่มีชื่อ บรรทัด `if` เลยอ่านเป็นประโยคได้
(`product_id and ...` — ตอนสร้างใหม่ `product_id` เป็น `None` ตัวแรกเป็นเท็จ ไม่ยิง query เลย)

**ทำไม** — Lot เก่าเก็บเลข `10` ไว้เฉย ๆ มันไม่ได้เก็บหน่วยไว้ด้วย
ถ้าเปลี่ยนหน่วยจาก "ขวด" เป็น "ลิตร" ทีหลัง เลข 10 ในทุก Lot เก่า
จะเปลี่ยนความหมายทันทีจาก 10 ขวดเป็น 10 ลิตร — ข้อมูลเก่าผิดหมดย้อนหลัง

**กฎ: สินค้าหนึ่งตัวใช้หน่วยเดียวตลอดทั้งซื้อ เบิก ขาย**

**หน่วยคือสิ่งที่นับได้ ไม่ใช่ปริมาตร** — น้ำมันเครื่องขวดละ 1 ลิตร ให้ตั้งหน่วยเป็น "ขวด"
แล้วเขียนปริมาตรไว้ในชื่อสินค้า ("น้ำมันเครื่อง 5W-30 1 ลิตร") เพราะสิ่งที่หยิบออกจากชั้นคือขวด
ไม่ใช่ลิตร ตั้งเป็นลิตรแล้วจะต้องมานั่งคิดทุกครั้งว่าเบิก 1 ขวดคือกี่ลิตร

### อ่าน `adjust_down` — ปรับลด

**ล็อกสองชั้น**

```python
lock_shop(db)                                        # ชั้น 1: ทั้งอู่ (ข้อ 1)
select(StockLot)...with_for_update()                 # ชั้น 2: แถว Lot นี้
```

`with_for_update()` คือ `SELECT ... FOR UPDATE` ในภาษา SQL —
ล็อกแถวที่อ่านมาจนจบทรานแซกชัน

**อ่าน `qty_remaining` ใต้ล็อกเท่านั้นถึงเชื่อค่าได้** ถ้าอ่านนอกล็อก
ค่าอาจเปลี่ยนไปแล้วตอนที่เราจะเขียน (ปัญหา race จากข้อ 1)

**ข้อความ error บอกตัวเลขด้วย**

```
"ปรับลดเกินคงเหลือของ Lot (เหลือ 2)"     ✅ รู้ว่าต้องแก้เป็นเท่าไหร่
"ทำรายการไม่ได้"                          ❌ ต้องไปเปิดดูเอง
```

นี่คือที่ที่ `format_qty` จากข้อ 3 ถูกใช้ — ให้ได้ `2` ไม่ใช่ `2.000`

### อ่าน `adjust_up` — ปรับเพิ่ม

**ทำไมต้อง `db.flush()` ตรงกลาง**

`StockMovement` ต้องใส่ `lot_id` แต่ Lot ที่เพิ่งสร้าง **ยังไม่มี id**
จนกว่าจะถูกเขียนลงฐาน

```python
db.add(lot)
db.flush()        # ส่ง INSERT ไปฐาน → ได้ id กลับมา  (ยังไม่ commit!)
db.add(StockMovement(lot_id=lot.id, ...))
db.commit()       # ตรงนี้ถึงจะบันทึกจริงทั้งคู่พร้อมกัน
```

**`flush` ไม่ใช่ `commit`** — ต่างกันตรงที่ flush ยังย้อนกลับได้
ถ้าบรรทัดถัดไปพัง ทุกอย่างย้อนหมดทั้ง Lot และ movement

**`cost_total = round_money(data.qty * data.unit_cost)`** — คูณแล้วปัด 2 ตำแหน่ง
เพราะเป็นยอดเงิน (`MONEY`) ไม่ใช่ราคาต่อหน่วย

### กฎที่ทั้งสองฟังก์ชันยึด: หนึ่งคำสั่ง = หนึ่งทรานแซกชัน

Lot กับ movement **เกิดพร้อมกันหรือไม่เกิดเลย** ไม่มีสภาพกลาง ๆ แบบ
"ของเพิ่มแล้วแต่ไม่มีบันทึกในสมุด" ซึ่งจะทำให้กฎข้อ 2 ในหัวข้อแนวคิดพัง

### `stock/router.py`

```python
from fastapi import APIRouter, Depends, Response
from sqlalchemy import or_, select

from app.auth import current_user, require_role
from app.db import get_db, get_or_404
from app.models import Product, StockLot, StockMovement, User
from app.schemas import serialize_for_role
from app.stock import service as svc
from app.stock.schemas import AdjustDownIn, AdjustUpIn, LotAdminOut, LotOut, MovementOut, ProductIn, ProductOut

router = APIRouter(prefix="/api", tags=["stock"])
staff = require_role("admin", "employee")


@router.get("/products", response_model=list[ProductOut])
def list_products(q: str = "", active: bool | None = None, db=Depends(get_db), _=Depends(current_user)):
    """GET /api/products?q=&active=: ค้นรหัส/ชื่อ กรองสถานะ → รายการสินค้าพร้อม qty_on_hand"""
    stmt = select(Product).order_by(Product.code)
    if q:
        stmt = stmt.where(or_(Product.code.ilike(f"%{q}%"), Product.name.ilike(f"%{q}%")))
    if active is not None:
        stmt = stmt.where(Product.is_active == active)
    return db.scalars(stmt).all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db=Depends(get_db), _=Depends(current_user)):
    """GET /api/products/{id}: สินค้าตัวเดียวพร้อม qty_on_hand, ไม่เจอ 404"""
    return get_or_404(db, Product, product_id, "สินค้า")


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductIn, db=Depends(get_db), _=Depends(staff)):
    """POST /api/products: admin/พนักงาน สร้างสินค้าใหม่ผ่าน svc.save_product"""
    return svc.save_product(db, None, data)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductIn, db=Depends(get_db), _=Depends(staff)):
    """PUT /api/products/{id}: admin/พนักงาน แก้สินค้าผ่าน svc.save_product"""
    return svc.save_product(db, product_id, data)


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
    """POST /api/stock/adjust-down: admin/พนักงาน ลดของใน Lot พร้อมเหตุผล → 204"""
    svc.adjust_down(db, data, user)
    return Response(status_code=204)


@router.post("/stock/adjust-up", response_model=LotAdminOut, status_code=201)
def adjust_up(data: AdjustUpIn, db=Depends(get_db), user=Depends(require_role("admin"))):
    """POST /api/stock/adjust-up: admin เพิ่ม Lot ใหม่ (ปรับเพิ่ม/ตั้งต้น) → คืน Lot"""
    return svc.adjust_up(db, data, user)
```

**สิทธิ์ของเฟสนี้**

| คำสั่ง | admin | employee | mechanic | ทำไม |
|---|:---:|:---:|:---:|---|
| ดูสินค้า Lot สมุดสต็อก | ✅ | ✅ | ✅ | ช่างต้องดูของก่อนเปิดใบงาน (แต่ไม่เห็นต้นทุน) |
| เพิ่ม/แก้สินค้า | ✅ | ✅ | ❌ | `staff` |
| ปรับลด | ✅ | ✅ | ❌ | ของหาย/เสียเจอหน้างานจริง แต่ต้องกรอกเหตุผล |
| ปรับเพิ่ม / ตั้งต้น | ✅ | ❌ | ❌ | สร้างของจากอากาศพร้อมต้นทุนที่กรอกเอง ถ้าใครก็ทำได้ ตัวเลขกำไรเชื่อไม่ได้ |

**`GET /products/{product_id}` — สินค้าตัวเดียว**

หน้ารายละเอียดสินค้า (ข้อ 15) ต้องการแค่ตัวเดียว ถ้าไม่มีเส้นนี้ต้องดึงรายการทั้งหมดแล้ว `find` เอาตัวที่ต้องการ
ซึ่งช้าลงเรื่อย ๆ ตามจำนวนสินค้า และไม่มี 404 ให้ — ได้แค่ "หาในรายการไม่เจอ"
เส้นนี้ใช้ `get_or_404` จากเฟส 2 บรรทัดเดียวจบ ไม่เจอก็ได้ "ไม่พบสินค้า" มาตรฐานเดียวกับที่อื่น

**ชื่อ endpoint ขึ้นต้นด้วยกริยาเสมอ** — `list_products` · `get_product` · `list_product_lots` · `list_product_movements`
อ่านรายชื่อฟังก์ชันในไฟล์แล้วรู้เลยว่าอันไหนคืนรายการ อันไหนคืนตัวเดียว

**บรรทัด `staff = require_role("admin", "employee")`** — สร้างตัวตรวจไว้ครั้งเดียว
(ท่าเดียวกับ `admin` ในเฟส 2) แล้วแปะได้หลายเส้น

**`response_model=None` บน `/lots` — ทำไมต้องปิด**

ปกติ FastAPI ใช้ `response_model` แปลงข้อมูลขาออกให้ แต่เส้นนี้
**schema ขึ้นกับว่าใครถาม** (`LotOut` หรือ `LotAdminOut`) FastAPI เดาไม่ได้
ใส่ `None` คือบอกว่า "อย่ายุ่ง" แล้วปล่อยให้ `serialize_for_role` จัดการเอง

**`ilike` ไม่ใช่ `like`** — ตัว `i` แปลว่า case-insensitive ค้นคำว่า `oil`
แล้วเจอ `OIL-1` ด้วย ถ้าใช้ `like` ธรรมดาต้องพิมพ์ตัวใหญ่ให้ตรงเป๊ะ

**`limit(500)` บนสมุดสต็อก** — สินค้าขายดีมี movement เป็นหมื่นแถว
ส่งทั้งหมดคือหน้าจอค้าง และไม่มีใครเลื่อนดูเกินหน้าแรกอยู่แล้ว

**`join(User)` เพื่อเอาชื่อคนทำมาด้วย**

```
ไม่ join → ส่ง {"created_by": 3}  → หน้าจอต้องยิงถามชื่อคน id 3 อีกรอบ (ทีละแถว!)
join    → ส่ง {"created_by_name": "employee"}  → จบในคำขอเดียว
```

**`adjust-down` คืน 204 ไม่คืนข้อมูล** — 204 แปลว่า "สำเร็จ ไม่มีอะไรส่งกลับ"
เพราะหน้าจอสั่ง `invalidateQueries({ queryKey: ["products"] })` ให้ดึงสินค้า Lot สมุดสต็อกใหม่ทั้งชุดอยู่แล้ว
(ต่างจาก `adjust-up` ที่คืน Lot ใหม่ เพราะหน้าจออาจอยากเอาไปใช้ต่อ)

### `app/main.py` — เติม router

**เปิด** `backend/app/main.py` → เติม import ไว้กลุ่มเดียวกับ router อื่น

```python
from app.stock import router as stock
```

→ แล้วเติมบรรทัดนี้ต่อจาก `include_router` ตัวอื่น

```python
app.include_router(stock.router)
```

**ลืมบรรทัดนี้ = เขียน API มาทั้งหมดแต่เรียกไม่ได้ ได้ 404 ทุกเส้น**

## 6. เทสต์

### `tests/conftest.py` — เติม fixture ท้ายไฟล์

```python
@pytest.fixture
def make_product():
    def make(code="P1", unit="ชิ้น", sale_price="100"):
        with SessionLocal() as s:
            p = models.Product(code=code, name=f"สินค้า {code}", unit=unit, sale_price=sale_price)
            s.add(p)
            s.commit()
            return p.id
    return make
```

**fixture ตัวนี้คืน _ฟังก์ชัน_ ไม่ได้คืนข้อมูล — ต่างจาก fixture อื่นที่เคยเขียน**

```python
def test_x(make_product):
    pid1 = make_product()          # เรียกได้
    pid2 = make_product("P2")      # และเรียกซ้ำได้ในเทสต์เดียวกัน
```

ถ้าคืนสินค้าเลยแบบ `users` fixture จะสร้างได้ตัวเดียวต่อเทสต์
แต่เทสต์เรื่อง Lot ต้องการสินค้าหลายตัว เลยคืนฟังก์ชันให้เรียกเองกี่ครั้งก็ได้

**ใส่ฐานตรง ๆ ไม่ยิงผ่าน API** — การเตรียมข้อมูลไม่ใช่สิ่งที่กำลังทดสอบ
ยิ่งสั้นยิ่งดี และไม่พังตามไปด้วยถ้า API สร้างสินค้าเปลี่ยนรูปแบบ

### `tests/test_stock.py`

```python
from decimal import Decimal as D

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import SessionLocal

PRODUCT = {"code": "OIL-1", "name": "น้ำมันเครื่อง", "unit": "ลิตร", "sale_price": "250", "min_stock": "2"}


def opening(client, h, pid, qty, cost):
    r = client.post(
        "/api/stock/adjust-up",
        headers=h["admin"],
        json={"product_id": pid, "qty": qty, "unit_cost": cost, "reason": "ตั้งต้น", "source_type": "opening"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_product_create_search_and_unit_lock(client, h):
    r = client.post("/api/products", json=PRODUCT, headers=h["employee"])
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert client.post("/api/products", json=PRODUCT, headers=h["employee"]).status_code == 409
    assert client.post("/api/products", json={**PRODUCT, "code": "X"}, headers=h["mechanic"]).status_code == 403
    opening(client, h, pid, "1.500", "180")
    [p] = client.get("/api/products?q=น้ำมัน", headers=h["mechanic"]).json()
    assert D(p["qty_on_hand"]) == D("1.5")
    one = client.get(f"/api/products/{pid}", headers=h["mechanic"]).json()
    assert one["code"] == "OIL-1" and D(one["qty_on_hand"]) == D("1.5")
    assert client.get("/api/products/999", headers=h["mechanic"]).status_code == 404
    assert client.put(f"/api/products/{pid}", json={**PRODUCT, "unit": "ขวด"}, headers=h["admin"]).status_code == 409
    assert (
        client.put(f"/api/products/{pid}", json={**PRODUCT, "sale_price": "260"}, headers=h["employee"]).status_code
        == 200
    )


def test_lots_are_separate_and_oldest_first(client, h, make_product):
    pid = make_product()
    opening(client, h, pid, "2", "80")
    opening(client, h, pid, "3", "120")
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert [D(lot["unit_cost"]) for lot in lots] == [80, 120]
    [p] = client.get("/api/products", headers=h["admin"]).json()
    assert D(p["qty_on_hand"]) == 5


def test_adjustments_and_cost_visibility(client, h, make_product):
    pid = make_product()
    lot_id = opening(client, h, pid, "2", "100")
    up = {"product_id": pid, "qty": "1", "unit_cost": "1", "reason": "นับเจอ", "source_type": "adjustment"}
    assert client.post("/api/stock/adjust-up", json=up, headers=h["employee"]).status_code == 403
    down = {"lot_id": lot_id, "qty": "1", "reason": "เสีย"}
    assert client.post("/api/stock/adjust-down", json={**down, "qty": "3"}, headers=h["employee"]).status_code == 409
    assert client.post("/api/stock/adjust-down", json={**down, "reason": " "}, headers=h["employee"]).status_code == 422
    assert client.post("/api/stock/adjust-down", json=down, headers=h["mechanic"]).status_code == 403
    assert client.post("/api/stock/adjust-down", json=down, headers=h["employee"]).status_code == 204
    [admin_lot] = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    [emp_lot] = client.get(f"/api/products/{pid}/lots", headers=h["employee"]).json()
    assert D(admin_lot["unit_cost"]) == 100 and D(admin_lot["qty_remaining"]) == 1
    assert not {"unit_cost", "cost_total"} & emp_lot.keys()
    moves = client.get(f"/api/products/{pid}/movements", headers=h["mechanic"]).json()
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

### อ่านเทสต์ชุดนี้ยังไง

**เทียบเป็น `Decimal` ไม่ใช่ string**

```python
D(p["qty_on_hand"]) == D("1.5")     # ✅ ไม่ต้องสนว่าฐานส่ง "1.500" หรือ "1.5"
p["qty_on_hand"] == "1.500"         # ❌ พังทันทีถ้าเปลี่ยนจำนวนทศนิยมในฐาน
```

**บรรทัดที่สำคัญที่สุดของทั้งเฟส**

```python
assert not {"unit_cost", "cost_total"} & emp_lot.keys()
```

อ่านว่า "เซ็ตของสองคีย์นี้ **ตัดกับ** คีย์ที่พนักงานได้รับ ต้องได้เซ็ตว่าง"

สังเกตว่าเช็คว่า **key ไม่มีอยู่เลย** ไม่ได้เช็คว่าค่าเป็น `None` —
ต่างกันมาก ถ้าค่าเป็น `None` แปลว่าข้อมูลยังส่งออกไปแล้วแค่ว่างเปล่า
ซึ่งไม่ใช่สิ่งที่เราต้องการ

**`test_lot_qty_cannot_go_negative` ข้าม service ใส่ฐานตรง ๆ**

จงใจเลี่ยงโค้ดทั้งหมดที่เราเขียน เพื่อพิสูจน์ว่า **CHECK ในฐานกันได้เองจริง**
แม้วันหนึ่งโค้ดจะมีบั๊กจนปล่อยค่าติดลบผ่านมาได้

`pytest.raises(IntegrityError)` = "บรรทัดข้างในนี้ต้องพัง ถ้าไม่พังคือเทสต์ตก"

**ตารางสรุปว่าเทสต์ไหนกันอะไร**

| เทสต์ | ยืนยันว่า |
|---|---|
| `product_create_search_and_unit_lock` | รหัสซ้ำ 409 · ช่างสร้างไม่ได้ 403 · ดึงตัวเดียวได้ / ไม่มี 404 · เปลี่ยนหน่วยหลังมีของไม่ได้ |
| `lots_are_separate_and_oldest_first` | **Lot แยกต้นทุนจริง และเรียงเก่าก่อน** |
| `adjustments_and_cost_visibility` | สิทธิ์ครบทุกบทบาท + **ต้นทุนไม่หลุดถึงพนักงาน** |
| `lot_qty_cannot_go_negative` | ฐานกันของติดลบเองได้ |

### รันเทสต์

```
docker compose run --rm api pytest
```

ต้อง **passed ทั้งหมด ไม่มี failed**

---

# ส่วนหน้าจอ

**ส่วนนี้จะได้อะไร** หน้ารายการสินค้า + หน้ารายละเอียดที่มี Lot กับสมุดสต็อก
พร้อมคอมโพเนนต์กลางอีกชุด (ช่องค้นหา · เปลือกหน้ารายละเอียด · ป๊อปอัพบังคับเหตุผล)

## 7. `api.js` — เติมตัวจัดรูปแบบท้ายไฟล์

**ขั้นนี้ทำอะไร** ตัวแปลงตัวเลขกับวันที่ให้เป็นรูปแบบไทย

**เปิด** `frontend/src/api.js` → เติมท้ายไฟล์

```js
// จัดรูปตัวเลขไว้โชว์: เงิน (2 ตำแหน่งเสมอ), ต้นทุน/ราคาต่อหน่วย (ทศนิยมเท่าที่มีจริง ≤4), จำนวน (≤3), วันที่ไทยเวลากรุงเทพ
export const formatMoney = (v) =>
  Number(v).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const formatUnitPrice = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 4 });

export const formatQty = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 3 });

export const formatDate = (v) =>
  v ? new Date(v).toLocaleDateString("th-TH-u-ca-gregory", { timeZone: "Asia/Bangkok", dateStyle: "medium" }) : "-";
```

(วางต่อจาก `plainNumber` ที่เติมไว้ในเฟส 2 ข้อ 16 — ไฟล์นี้รวมตัวจัดรูปแบบไว้ที่เดียวกันหมด)

**ชื่อขึ้นต้นด้วย `format` ทั้งสามตัว** — อ่าน `formatMoney(p.sale_price)` แล้วรู้ทันทีว่า "แปลงเป็นข้อความไว้โชว์"
ไม่ใช่ตัวเลขเงินที่เอาไปคำนวณต่อได้

**สามตัว สามหน้าที่ — ต่างกันที่ทศนิยม**

```
formatMoney("1500")        → "1,500.00"   เงิน: 2 ตำแหน่งเสมอ ทุกบรรทัดเรียงตรงแนว
formatUnitPrice("100.0000") → "100"        ต้นทุน/หน่วย: มีทศนิยมเท่าไหร่โชว์เท่านั้น
formatUnitPrice("333.3333") → "333.3333"   แต่ของที่มีเศษจริงก็ไม่ตัดทิ้ง
formatQty("2.000")          → "2"          จำนวน: 2 ชิ้น ไม่ใช่ 2.000 ชิ้น
formatQty("0.500")          → "0.5"        ของที่ตวง/ชั่งก็ยังโชว์ถูก
```

**ทำไมเงินกับต้นทุนต่อหน่วยไม่เหมือนกัน** — เงินเป็นยอดที่ต้องเอาไปรวมกันเป็นคอลัมน์
ทศนิยมเท่ากันทุกบรรทัดถึงจะกวาดตาดูรู้เรื่อง ส่วนต้นทุนต่อหน่วยเป็นตัวเลขเดี่ยว ๆ
เก็บไว้ 4 ตำแหน่งเพราะ**บางตัวมีเศษจริง** (มาจากการหาร) แต่ `100.0000` ก็ไม่มีประโยชน์ที่จะโชว์ศูนย์สี่ตัว

> **`Number(v)` ตรงนี้ใช้เพื่อ _แสดงผล_ เท่านั้น**
> ห้ามเอาค่าที่แปลงเป็น `Number` แล้วส่งกลับ backend เด็ดขาด
> เพราะ `Number` คือ float ซึ่งมีปัญหาความแม่นตามที่เตือนไว้ในเฟส 2
> **ส่ง string ที่ได้จากเซิร์ฟเวอร์กลับไปตรง ๆ เสมอ**

**`formatDate` — สองอย่างที่ต้องใส่**

- `-u-ca-gregory` → บังคับ **ปี ค.ศ.** ถ้าใช้ `th-TH` เฉย ๆ จะได้ พ.ศ.
  ซึ่งเอกสารทางบัญชีบางอย่างต้องการ ค.ศ.
- `timeZone: "Asia/Bangkok"` → **จำเป็น** เพราะเซิร์ฟเวอร์เก็บเป็น UTC
  (จำ `TS = DateTime(timezone=True)` จากเฟส 1 ได้ไหม) ไม่ใส่แล้วของที่ทำตอน
  ตี 1 จะแสดงเป็นวันก่อนหน้า

`v ? ... : "-"` — ค่าว่างแสดงขีด ไม่ใช่ `Invalid Date`

## 8. `components/Icon.jsx` — เติมใน `PATHS`

**เปิด** `frontend/src/components/Icon.jsx` → เติมใน `PATHS` (ก็อปวางได้เลย)

```jsx
  more: <><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /><circle cx="5" cy="12" r="1" /></>,
  box: <><path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z" /><path d="M12 22V12" /><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7" /><path d="m7.5 4.27 9 5.15" /></>,
  search: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></>,
  back: <><path d="m12 19-7-7 7-7" /><path d="M19 12H5" /></>,
  edit: <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />,
  minus: <path d="M5 12h14" />,
```

## 9. `components/StatusBadge.jsx` — เติมสถานะสินค้า

**ขั้นนี้ทำอะไร** เพิ่มป้ายสองแบบของสินค้า: "ต่ำกว่าขั้นต่ำ" กับ "เลิกใช้"

**เปิด** `frontend/src/components/StatusBadge.jsx` → เติมสองบรรทัดนี้ใน `STATUS`

```jsx
  low: ["ต่ำกว่าขั้นต่ำ", "warn"],
  inactive: ["เลิกใช้", "neutral"],
```

→ แล้วเติมฟังก์ชันนี้ **ก่อน** comment ของ `export default`

```jsx
// สถานะสินค้า: เลิกใช้ → inactive, คงเหลือ ≤ ขั้นต่ำ → low, ปกติ → null
export function productStatus(p) {
  if (!p.is_active) return "inactive";
  const hasMinimum = Number(p.min_stock) > 0;
  if (hasMinimum && Number(p.qty_on_hand) <= Number(p.min_stock)) return "low";
  return null;
}
```

**อ่านโค้ดนี้ยังไง** — อ่านเป็นบันไดจากบนลงล่าง เจอข้อไหนจริงก็ตอบเลย:

```
เลิกใช้แล้วเหรอ              → "inactive"
ไม่ใช่ แล้วของต่ำกว่าขั้นต่ำ? → "low"
ไม่ใช่ทั้งคู่                 → null (ไม่มีป้าย)
```

**ทำไมเขียน `if` สามบรรทัด ไม่เขียน ternary ซ้อนบรรทัดเดียว** — `a ? x : b ? y : z` สั้นกว่า
แต่ต้องนับ `?` กับ `:` ว่าคู่ไหนไปกับคู่ไหน `if ... return` อ่านทีละบรรทัดจบ ไม่ต้องนับ

**ชื่อ `productStatus` ไม่ใช่ `productKey`** — คืน "สถานะของสินค้า" ที่เอาไปใส่ `<StatusBadge status={...}>`
ตั้งชื่อตามสิ่งที่คืน คนอ่านไม่ต้องเดาว่า "key" คือ key ของอะไร

**สถานะนี้ _คำนวณ_ จากข้อมูล ไม่ได้ _เก็บ_ ไว้ในฐาน**

"ต่ำกว่าขั้นต่ำ" ไม่ใช่สถานะที่ต้องมีคนไปกดตั้ง มันเป็นผลของตัวเลขสองตัว
(`qty_on_hand` กับ `min_stock`) คำนวณตอนแสดงทุกครั้ง → **ถูกเสมอ**

ถ้าไปเก็บเป็นคอลัมน์ `is_low` ในฐาน ต้องมีโค้ดคอยอัปเดตทุกครั้งที่สต็อกขยับ
และจะมีวันที่ลืมอัปเดต (หลักการเดียวกับ `qty_on_hand` ที่ไม่เก็บเป็นคอลัมน์)

**`Number(p.min_stock) > 0` ต้องเช็คก่อน — ไม่งั้นเตือนทั้งร้าน**

สินค้าที่ตั้งขั้นต่ำเป็น `0` แปลว่า **ไม่อยากให้เตือน** ไม่ได้แปลว่า
"เตือนตลอดเพราะ `0 <= 0` เป็นจริง"

## 10. `components/SearchBar.jsx` — ช่องค้นหา + แถบกรอง

**ขั้นนี้ทำอะไร** แถบเครื่องมือเหนือรายการ: ช่องค้นหา + ปุ่มกรอง

**สร้างไฟล์ใหม่** `frontend/src/components/SearchBar.jsx`

```jsx
import Icon from "./Icon";

// ช่องค้นหา (q/setQ) + แท็บกรอง (filter/setFilter) ถ้าส่ง filters มา
export default function SearchBar({ q, setQ, placeholder, filters, filter, setFilter }) {
  return (
    <div className="space-y-2">
      <label className="relative block">
        <span className="sr-only">{placeholder}</span>
        <Icon name="search" size={20} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
        <input type="search" className="input pl-10" placeholder={placeholder} value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      {filters && (
        <div role="tablist" aria-label="กรอง" className="tabs -mx-4 px-4 md:mx-0 md:px-0">
          {filters.map(([key, label]) => (
            <button key={key} type="button" role="tab" aria-selected={filter === key} onClick={() => setFilter(key)} className="tab">{label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
```

**อ่านโค้ดนี้ยังไง**

รับ state มาจากหน้าที่เรียกใช้ทั้งหมด (`q`/`setQ`, `filter`/`setFilter`) —
ตัวมันเองไม่เก็บอะไรเลย เรียกว่า controlled component

**สี่รายละเอียดที่ทำให้ใช้งานจริงได้ดี**

- **`type="search"`** — เบราว์เซอร์ใส่ปุ่มกากบาทล้างข้อความให้ฟรี
- **`sr-only` บน `<span>`** — คลาสนี้ทำให้ข้อความมองไม่เห็นแต่ screen reader
  ยังอ่าน จำเป็นเพราะ `placeholder` **หายไปตอนเริ่มพิมพ์** ช่องกรอกต้องมี
  ชื่อถาวรที่ไม่หาย
- **`pointer-events-none` บนไอคอนแว่นขยาย** — ไอคอนวางทับช่องอยู่
  ไม่ใส่บรรทัดนี้ คลิกโดนไอคอนจะไม่โฟกัสเข้าช่อง ผู้ใช้จะงงว่าทำไมกดไม่ติด
- **`-mx-4 px-4 md:mx-0 md:px-0`** — ดึงแถบกรองให้ชนขอบจอบนมือถือ
  เลื่อนซ้ายขวาได้เต็มพื้นที่ พอขึ้นจอใหญ่ก็กลับมาปกติ

**`filters` ไม่ส่งมาก็ได้** — `{filters && ...}` ข้ามทั้งก้อน
(เฟส 4 หน้ารับของใช้แค่ช่องค้นหา ไม่มีแถบกรอง)

ทำเป็นคอมโพเนนต์ตั้งแต่ตอนนี้เพราะเฟส 4 จะใช้อีกสามหน้า

## 11. `components/DetailLayout.jsx` — เปลือกหน้ารายละเอียด

**ขั้นนี้ทำอะไร** เปลือกของ**หน้ารายละเอียด** (คู่กับ `ListLayout` ของเฟส 2
ที่เป็นเปลือกของหน้ารายการ)

```
ListLayout    (เฟส 2)   หน้ารายการ    → ป๊อปอัพฟอร์มเปิดทับ
DetailLayout  (เฟส 3)   หน้ารายละเอียด → ลิงก์ย้อนกลับ + ปุ่มหลักติดล่าง + เมนู ⋯
```

**สร้างไฟล์ใหม่** `frontend/src/components/DetailLayout.jsx`

```jsx
import { Link } from "react-router-dom";
import Icon from "./Icon";

// ปุ่ม ⋯ เปิดเมนูคำสั่งเพิ่มเติม คลิกแล้วปิดเมนูและเรียก onClick
function MoreMenu({ items }) {
  return (
    <details className="relative">
      <summary aria-label="คำสั่งเพิ่มเติม" className="btn btn-ghost btn-icon list-none [&::-webkit-details-marker]:hidden">
        <Icon name="more" />
      </summary>
      <ul className="absolute right-0 z-20 mt-1 w-60 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lg">
        {items.map((m) => (
          <li key={m.label}>
            <button type="button"
              onClick={(e) => { e.currentTarget.closest("details").open = false; m.onClick(); }}
              className="flex min-h-11 w-full items-center px-4 text-left hover:bg-surface">
              {m.label}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}

// Full-page detail screen: back link, title row, content, one sticky action bar (above the phone nav).
export default function DetailLayout({ back, backLabel, title, subtitle, badge, menu = [], footer, children }) {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <header>
        <Link to={back} className="-ml-2 inline-flex min-h-11 items-center gap-1 px-2 text-sm text-muted hover:text-ink">
          <Icon name="back" size={18} />{backLabel}
        </Link>
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <h1 className="page-title break-words">{title}</h1>
            {subtitle && <div className="text-sm text-muted">{subtitle}</div>}
          </div>
          {badge && <div className="pt-1">{badge}</div>}
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

### อ่านโค้ดนี้ยังไง

**ทำไมหน้ารายละเอียดเป็นหน้าเต็ม ไม่ทำเป็นป๊อปอัพเหมือนฟอร์ม**

1. มีข้อมูลเยอะ — รายการ Lot + สมุดสต็อกทั้งหมด ยัดในป๊อปอัพไม่ไหว
2. **มันต้องเปิดป๊อปอัพซ้อนอีกชั้น** (แก้สินค้า · ปรับลด) และป๊อปอัพซ้อน
   ป๊อปอัพบนมือถือใช้งานไม่ได้จริง

**กฎการวางปุ่ม: ปุ่มหลักปุ่มเดียว คำสั่งรองยัดในเมนู ⋯**

```
footer  → ปุ่มหลัก 1 ปุ่ม ลอยติดขอบล่าง กดง่ายที่สุด
menu    → คำสั่งรองทั้งหมด ซ่อนอยู่หลังปุ่ม ⋯
```

**หน้าจอที่มีปุ่มเด่นห้าปุ่ม คือหน้าจอที่ไม่มีปุ่มเด่นเลย** ผู้ใช้ต้องอ่าน
ทั้งห้าปุ่มทุกครั้งเพื่อหาอันที่ต้องการ

**`MoreMenu` ใช้ `<details>` ของ HTML ไม่ใช่ state ของ React**

หลักการเดียวกับ `<dialog>` ในเฟส 2 — เบราว์เซอร์จัดการเปิด/ปิดให้เอง
และใช้คีย์บอร์ดได้เองโดยไม่ต้องเขียนอะไรเพิ่ม

```jsx
onClick={(e) => { e.currentTarget.closest("details").open = false; m.onClick(); }}
//                ^ ต้องสั่งปิดเอง
```

บรรทัดนี้จำเป็นเพราะ **`<details>` ไม่ปิดตัวเองเมื่อคลิกข้างใน**
(มันปิดเฉพาะตอนคลิกที่หัว `<summary>`) `closest("details")` คือการไต่ขึ้นไป
หา `<details>` ที่ครอบปุ่มนี้อยู่

`list-none [&::-webkit-details-marker]:hidden` — ซ่อนลูกศรสามเหลี่ยมที่
เบราว์เซอร์ใส่ให้ `<summary>` โดยอัตโนมัติ

**`sticky bottom-0` บน footer**

ปุ่มหลักลอยติดขอบล่างจอตลอด ไม่ว่าผู้ใช้จะเลื่อนหน้าไปไกลแค่ไหน —
สำคัญบนมือถือที่หน้ายาว ๆ ต้องเลื่อนหาปุ่ม

- `pb-[max(0.75rem,env(safe-area-inset-bottom))]` — เว้นที่ให้ขีดดำล่างจอ
  ของ iPhone ไม่ให้ทับปุ่ม (`max` = เอาค่าที่มากกว่าระหว่างสองอัน)
- `md:static` — จอใหญ่ไม่ต้องลอย เพราะเห็นทั้งหน้าอยู่แล้ว

## 12. `components/ReasonDialog.jsx` — ป๊อปอัพที่บังคับกรอกเหตุผล

**ขั้นนี้ทำอะไร** ป๊อปอัพยืนยันที่มีช่องเหตุผลบังคับกรอก ใช้ซ้ำหลายที่

**สร้างไฟล์ใหม่** `frontend/src/components/ReasonDialog.jsx`

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

### อ่านโค้ดนี้ยังไง

**ทำไมต้องมีคอมโพเนนต์นี้** — ระบบนี้บังคับกรอกเหตุผลหลายที่มาก:
ปรับลด · ปรับเพิ่ม (เฟสนี้) · ยกเลิก PO · ปิด PO (เฟส 4)
ทั้งหมดหน้าตาเหมือนกัน (หัว · ช่องของตัวเอง · ช่องเหตุผล · ปุ่มยกเลิก/ยืนยัน) ทำตัวเดียวใช้ทุกที่

**`ReasonDialog` เป็นแค่ "หน้าตา" — ฟอร์มกับการส่งเป็นของคนเรียก**

| คนเรียกส่งอะไรมา | ใช้ทำอะไร |
|---|---|
| `register` | จาก `useForm` ของคนเรียก → ผูกช่อง `reason` เข้าฟอร์มเดียวกับช่องอื่น |
| `onSubmit` | `handleSubmit(...)` ของคนเรียก |
| `mutation` | `useMutation` ของคนเรียก → อ่าน `isPending` ปิดปุ่ม · `error` โชว์ข้อความ |
| `children` | ช่องเฉพาะของแต่ละคำสั่ง (จำนวน · ต้นทุน) |

ทำไมไม่ให้ `ReasonDialog` ถือฟอร์มเอง — เพราะช่องใน `children` (จำนวนที่ลด) กับช่องเหตุผล
**ต้องส่งไปด้วยกันในคำขอเดียว** อยู่ในฟอร์มเดียว (`useForm` ตัวเดียวของคนเรียก) ง่ายสุด
`handleSubmit` รวบทั้ง `qty` และ `reason` มาให้ครบในก้อนเดียว

```jsx
<ReasonDialog register={register} onSubmit={handleSubmit(...)} mutation={adjustDown} ...>
  <Field label="จำนวนที่ลด" {...register("qty")} />   {/* ← children ใช้ register ตัวเดียวกัน */}
</ReasonDialog>                                          {/* ช่องเหตุผล register("reason") ต่อท้ายให้เอง */}
```

**ไม่มี prop `open` — render = เปิด** (กฎของ `Modal` จากเฟส 2)

```jsx
{dialog?.downLot && <AdjustDownDialog ... />}   // ข้อ 15
```

ปิดแล้วถอดออกจากหน้า ค่าที่พิมพ์ค้าง (จำนวน เหตุผล error) หายไปพร้อมกัน
เปิดครั้งหน้าฟอร์มสะอาดเอง ไม่ต้องเขียน `useEffect` คอยล้างค่า

**ปิดป๊อปอัพเฉพาะตอนสำเร็จ** — คนเรียกใส่ `onClose` ไว้ใน `onSuccess` ของ `useMutation` (ข้อ 15)
ถ้าพัง `onSuccess` ไม่ทำงาน ป๊อปอัพค้างอยู่พร้อม `mutation.error` ให้อ่าน ไม่ต้องกรอกใหม่หมด

**`open` ไม่มี แต่ต่างจากป๊อปอัพฟอร์มในเฟส 2 ตรงที่คุมด้วย state ไม่ใช่ URL**

| | เปิด/ปิดด้วย | เพราะ |
|---|---|---|
| ฟอร์มเพิ่ม/แก้ (เฟส 2) | **URL** (route ลูก) | เป็นหน้าจอหนึ่ง ควรส่งลิงก์ได้ |
| `ReasonDialog` (อันนี้) | **state** ของหน้า (`dialog`) | เป็นคำสั่งย่อยในหน้า ไม่ต้องมี URL ของตัวเอง |

**`required` บน `<textarea>`** กันส่งฟอร์มว่างตั้งแต่ฝั่งเบราว์เซอร์
(backend ก็ยังตรวจซ้ำด้วย `min_length=1` อยู่ดี)

## 13. `pages/ProductFormPage.jsx` — ป๊อปอัพเพิ่ม/แก้สินค้า

**ขั้นนี้ทำอะไร** ฟอร์มสินค้า ที่ถูกเรียกใช้จาก **สองที่** ด้วยพฤติกรรมต่างกัน

```
/stock/new          เพิ่มสินค้า  → บันทึกแล้วพาไปหน้ารายละเอียดของตัวใหม่
หน้ารายละเอียด → แก้สินค้า   → บันทึกแล้วอยู่หน้าเดิม แค่ปิดป๊อปอัพ
```

ไฟล์นี้เลย export **สองตัว**: `ProductFormPage` (ตัวที่ผูกกับ route)
กับ `ProductModal` (ตัวฟอร์มจริงที่หน้ารายละเอียดหยิบไปใช้)

**สร้างไฟล์ใหม่** `frontend/src/pages/ProductFormPage.jsx`

```jsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate, useOutletContext } from "react-router-dom";
import { api, plainNumber } from "../api";
import Field from "../components/Field";
import Modal from "../components/Modal";

export const EMPTY_PRODUCT = { code: "", name: "", unit: "", sale_price: "", min_stock: "0", is_active: true };

// /stock/new: popup เพิ่มสินค้าบนหน้ารายการ บันทึกแล้วไปหน้าสินค้าตัวใหม่
export default function ProductFormPage() {
  const { close } = useOutletContext();
  const navigate = useNavigate();
  return <ProductModal initial={EMPTY_PRODUCT} onClose={close} onSaved={(p) => navigate(`/stock/${p.id}`)} />;
}

// ฟอร์มสินค้า: มี id → PUT /products/{id}, ไม่มี → POST /products, สำเร็จแล้วให้ข้อมูลสินค้าทุกหน้าโหลดใหม่
export function ProductModal({ initial, onClose, onSaved }) {
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

### อ่านโค้ดนี้ยังไง

**`ProductFormPage` สั้นมาก เพราะมันแค่ห่อ `ProductModal` อีกที**

```jsx
<ProductModal initial={EMPTY_PRODUCT} onClose={close} onSaved={(p) => navigate(`/stock/${p.id}`)} />
//                                                    ^ พฤติกรรมหลังบันทึก ส่งเข้ามาจากข้างนอก
```

ตัว `ProductModal` ไม่รู้เลยว่าบันทึกเสร็จแล้วต้องไปไหนต่อ — ใครเรียกใช้เป็นคนบอก
หน้ารายละเอียดส่ง `onSaved` อีกแบบ (แค่ปิดป๊อปอัพ)

**สิ่งที่ `ProductModal` ทำเองเสมอ ไม่ว่าใครเรียก: `invalidateQueries({ queryKey: ["products"] })`**

บันทึกสินค้าแล้วข้อมูลใต้กุญแจ `"products"` เก่าหมด — รายการสินค้า · สินค้าตัวนั้น
สั่งทีเดียวที่นี่ ทั้งหน้ารายการ (ข้อ 14) และหน้ารายละเอียด (ข้อ 15) อัปเดตเอง
คนเรียกไม่ต้องจำว่าต้อง reload อะไร (เดิมหน้ารายการต้องส่ง `reload` ลงมาทาง context)

**หลังเพิ่มสินค้าใหม่ กระโดดไปหน้ารายละเอียดเลย — จงใจ**

เพราะสิ่งที่คนทำต่อเกือบทุกครั้งหลังเพิ่มสินค้า คือ**ใส่สต็อกตั้งต้น**
ซึ่งปุ่มอยู่ในหน้ารายละเอียด พาไปให้เลยประหยัดหนึ่งคลิกทุกครั้ง

**`isEdit = !!initial.id`** — ตั้งชื่อคำถาม "กำลังแก้ของเดิมอยู่ไหม" ไว้ครั้งเดียว ใช้สามที่ (URL · method · หัวป๊อปอัพ)
`!!` แปลงค่าอะไรก็ได้เป็น `true`/`false` (มี id = `true`)

**`sale_price` / `min_stock` ผ่าน `plainNumber` ก่อนใส่ฟอร์ม** (เฟส 2 ข้อ 16)

ฐานส่งมาเป็น `"150.0000"` กับ `"4.000"` ตามจำนวนทศนิยมของคอลัมน์ ถ้าใส่ตรง ๆ คนกดแก้สินค้าจะเห็นเลขรกแบบนั้น
ตัดศูนย์ท้ายก่อนให้เห็น `150` กับ `4` — ค่าที่ส่งกลับไปบันทึกเหมือนเดิมทุกอย่าง

**ส่ง `form` ทั้งก้อนเป็น body ได้เลย ไม่ต้องคัดช่อง**

ตอนแก้ `initial` คือสินค้าทั้งตัวจาก API (`defaultValues`) มี `id` กับ `qty_on_hand` ติดมาด้วย
ซึ่ง `ProductIn` ไม่มีช่องพวกนี้ — **pydantic ทิ้งช่องที่ไม่รู้จักให้เอง** ไม่ error

**checkbox ก็ใช้ `register` ได้** — `<input type="checkbox" {...register("is_active")} />`
react-hook-form รู้เองว่าเป็น checkbox แล้วเก็บเป็น `true`/`false` ไม่ต้องเขียน `checked` / `e.target.checked` เอง

**ป้าย "ราคาขาย (รวม VAT)"** — ทั้งระบบตกลงกันว่าราคาที่คุยกับลูกค้า
**รวม VAT แล้ว** เขียนไว้ตรงจุดที่กรอกเลย ดีกว่าให้ไปเดาหรือถามกันทีหลัง

**`type="number"` กับ `inputMode="decimal"` ใส่คู่กัน**

| | ทำอะไร |
|---|---|
| `type="number"` | เบราว์เซอร์ตรวจว่าเป็นตัวเลข + `min` `step` ทำงาน |
| `inputMode="decimal"` | มือถือเด้งแป้นตัวเลขที่มีจุดทศนิยม |

**ค่าที่ได้จาก `register` เป็น string เสมอ** แม้ `type="number"` — ส่ง `"250"` ไป backend ตรง ๆ
pydantic แปลงเป็น `Decimal` ให้ ไม่ผ่าน float เลย (ตรงกับคำเตือนเรื่อง `Number()` ในข้อ 7)

**`role="switch"` บน checkbox** — บอก screen reader ว่านี่คือสวิตช์เปิด/ปิด
ไม่ใช่ช่องติ๊กเลือกในรายการ

## 14. `pages/ProductListPage.jsx` — รายการสินค้า

**ขั้นนี้ทำอะไร** หน้ารายการสินค้า — โครงเดียวกับหน้าผู้ใช้ในเฟส 2 เป๊ะ
(`useQuery` + `ListLayout` + `DataTable`) แค่เพิ่มแถบค้นหา/กรอง

**สร้างไฟล์ใหม่** `frontend/src/pages/ProductListPage.jsx`

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
  ["low", "ต่ำกว่าขั้นต่ำ"],
  ["inactive", "เลิกใช้"],
];

// หน้า /stock: GET /products แล้วค้น/กรองฝั่ง client, route ลูก new เปิด popup เพิ่มสินค้า
export default function ProductListPage() {
  const { user } = useAuth();
  const { data, error } = useQuery({ queryKey: ["products"] });
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("active");
  const text = q.trim().toLowerCase();
  const items = data?.filter(
    (p) =>
      (filter === "active" ? p.is_active : productStatus(p) === filter) &&
      (!text || p.code.toLowerCase().includes(text) || p.name.toLowerCase().includes(text)),
  );

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

### อ่านโค้ดนี้ยังไง

**ค้นหาและกรองทำที่ฝั่งหน้าจอ ทั้งที่ API รับ `q` ได้**

```jsx
const items = data?.filter((p) => ...)   // กรองในเบราว์เซอร์
```

เพราะสินค้าของอู่มีไม่กี่ร้อยรายการ โหลดมาทีเดียวแล้วกรองในเครื่อง
**ได้ผลทันทีทุกตัวอักษรที่พิมพ์ ไม่ต้องรอเน็ต** ซึ่งรู้สึกเร็วกว่ามาก

(`q` ที่ API รับไว้เผื่อวันที่แคตตาล็อกโตจริง ๆ และเทสต์ใช้อยู่)

**`data?.filter(...)` — เครื่องหมาย `?` สำคัญ**

ตอนยังโหลดไม่เสร็จ `data` เป็น `undefined` เขียน `data.filter` จะพังทันที
`?.` ทำให้ได้ `undefined` แทน ซึ่งพอส่งเข้า `DataTable` มันจะโชว์
"กำลังโหลด…" ให้ถูกต้อง (จำสามสถานะจากเฟส 2 ได้ไหม)

**ไม่ส่ง `context` ให้ `ListLayout`** — ป๊อปอัพเพิ่มสินค้า (ข้อ 13) บันทึกแล้วสั่ง invalidate `["products"]` เอง
`useQuery` ของหน้านี้ดึงใหม่อัตโนมัติ ไม่ต้องส่ง `reload` ลงไป

**กดเข้าหน้าสินค้าแล้วกดกลับ รายการขึ้นทันที** — ข้อมูล `["products"]` ยังอยู่ใน cache
TanStack Query โชว์ของเดิมก่อนแล้วดึงใหม่เบื้องหลัง ไม่ขึ้น "กำลังโหลด…" ซ้ำ

**การ์ดมือถือเอายอดคงเหลือเป็นตัวใหญ่ที่สุดในการ์ด**

```jsx
<div className="num text-2xl font-bold">{formatQty(p.qty_on_hand)}</div>
```

เพราะคนที่เปิดหน้านี้บนมือถือส่วนใหญ่กำลัง**ยืนอยู่หน้าชั้นของ**
คำถามเดียวในหัวคือ "ยังเหลือกี่ชิ้น" — ตอบให้เห็นแต่ไกล

`num` คือคลาส `tabular-nums` จากเฟส 2 ที่ทำให้ตัวเลขเรียงตรงแนว

**`action={user.role !== "mechanic" && {...}}`**

ช่างได้ `false` → `ListLayout` ข้ามปุ่มเพิ่มทั้งก้อน (ที่เตรียมไว้ตั้งแต่เฟส 2)

ย้ำอีกครั้ง: **นี่คือความสะดวก ไม่ใช่ความปลอดภัย** ของจริงคือ `staff`
ที่ `stock/router.py` ข้อ 5

## 15. `pages/ProductDetailPage.jsx` — หน้ารายละเอียดสินค้า

**ขั้นนี้ทำอะไร** หน้าที่ยาวที่สุดของเฟส — รวมทุกอย่างที่ทำมาเข้าด้วยกัน:
ข้อมูลสินค้า · รายการ Lot · สมุดสต็อก · ปุ่มแก้สินค้า · ปรับเพิ่ม/ปรับลด

**สร้างไฟล์ใหม่** `frontend/src/pages/ProductDetailPage.jsx`

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
import StatusBadge, { productStatus } from "../components/StatusBadge";
import { ProductModal } from "./ProductFormPage";

const SOURCE = { adjustment: "ปรับเพิ่ม", opening: "สต็อกตั้งต้น" };
const MOVE = { adjust: "ปรับสต็อก", opening: "ตั้งต้น" };
const TABS = [
  ["lots", "Lot"],
  ["moves", "สมุดสต็อก"],
];

// หน้าสินค้า /stock/:id: ดึงสินค้า + Lot + สมุดสต็อก, เปิด popup แก้สินค้า / ปรับลด / ปรับเพิ่ม
export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const isStaff = user.role !== "mechanic";
  const product = useQuery({ queryKey: ["products", id] });
  const lots = useQuery({ queryKey: ["products", id, "lots"] });
  const moves = useQuery({ queryKey: ["products", id, "movements"] });
  const [tab, setTab] = useState("lots");
  const [dialog, setDialog] = useState(null); // null | "edit" | "up" | { downLot }
  const closeDialog = () => setDialog(null);

  const p = product.data;
  if (!p) return <DetailLayout back="/stock" backLabel="สต็อก" title={product.error?.message || "กำลังโหลด…"} />;

  return (
    <DetailLayout
      back="/stock"
      backLabel="สต็อก"
      title={p.name}
      subtitle={p.code}
      badge={<StatusBadge status={productStatus(p)} />}
      menu={isAdmin ? [{ label: "ปรับเพิ่ม / สต็อกตั้งต้น", onClick: () => setDialog("up") }] : []}
      footer={
        isStaff && (
          <button type="button" className="btn btn-primary w-full" onClick={() => setDialog("edit")}>
            <Icon name="edit" size={20} />
            แก้สินค้า
          </button>
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
      {tab === "lots" ? (
        <LotList
          lots={lots}
          showCost={isAdmin}
          canAdjust={isStaff}
          onAdjustDown={(lot) => setDialog({ downLot: lot })}
        />
      ) : (
        <MovementList moves={moves} />
      )}

      {dialog === "edit" && <ProductModal initial={p} onClose={closeDialog} onSaved={closeDialog} />}
      {dialog === "up" && <AdjustUpDialog productId={p.id} onClose={closeDialog} />}
      {dialog?.downLot && <AdjustDownDialog lot={dialog.downLot} onClose={closeDialog} />}
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

// รายการ Lot เก่า→ใหม่: ต้นทุนโชว์เฉพาะ admin, Lot ที่ยังเหลือของมีปุ่มปรับลด
function LotList({ lots, showCost, canAdjust, onAdjustDown }) {
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
                Lot #{lot.id} · {SOURCE[lot.source_type]}
              </span>
              <span className="text-sm">{formatDate(lot.created_at)}</span>
            </div>
            <div className="num text-sm">
              รับเข้า {formatQty(lot.qty_received)} · <b>เหลือ {formatQty(lot.qty_remaining)}</b>
            </div>
            {showCost && <div className="num text-sm">ต้นทุน/หน่วย {formatUnitPrice(lot.unit_cost)}</div>}
            {canAdjust && hasStock && (
              <button type="button" className="btn btn-secondary" onClick={() => onAdjustDown(lot)}>
                <Icon name="minus" size={20} />
                ปรับลด
              </button>
            )}
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
                {MOVE[m.movement_type]} · Lot #{m.lot_id}
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

// popup ปรับลด Lot: POST /stock/adjust-down { lot_id, qty, reason }
function AdjustDownDialog({ lot, onClose }) {
  const { register, handleSubmit } = useForm({ defaultValues: { qty: "", reason: "" } });
  const adjustDown = useAdjustStock("/stock/adjust-down", onClose);
  return (
    <ReasonDialog
      title={`ปรับลด Lot #${lot.id}`}
      onClose={onClose}
      register={register}
      mutation={adjustDown}
      onSubmit={handleSubmit((form) => adjustDown.mutate({ ...form, lot_id: lot.id }))}
    >
      <Field
        label={`จำนวนที่ลด (เหลือ ${formatQty(lot.qty_remaining)})`}
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0.001"
        required
        {...register("qty")}
      />
    </ReasonDialog>
  );
}

// popup ปรับเพิ่ม/สต็อกตั้งต้น (admin): POST /stock/adjust-up สร้าง Lot ใหม่
function AdjustUpDialog({ productId, onClose }) {
  const { register, handleSubmit } = useForm({
    defaultValues: { source_type: "adjustment", qty: "", unit_cost: "", reason: "" },
  });
  const adjustUp = useAdjustStock("/stock/adjust-up", onClose);
  return (
    <ReasonDialog
      title="ปรับเพิ่ม / สต็อกตั้งต้น"
      onClose={onClose}
      register={register}
      mutation={adjustUp}
      onSubmit={handleSubmit((form) => adjustUp.mutate({ ...form, product_id: productId }))}
    >
      <label className="block">
        <span className="label">ประเภท</span>
        <select className="input" {...register("source_type")}>
          <option value="adjustment">ปรับเพิ่ม</option>
          <option value="opening">สต็อกตั้งต้น</option>
        </select>
      </label>
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

### อ่านโค้ดนี้ยังไง

**ไฟล์ยาว แต่แบ่งเป็นชิ้นเล็กที่แต่ละชิ้นทำเรื่องเดียว**

```
ProductDetailPage   ดึงข้อมูล 3 ชุด · หัวหน้า · แท็บ · เลือกว่าป๊อปอัพไหนเปิด
 ├─ Fact             กล่อง หัวข้อ + ค่า
 ├─ LotList          รายการ Lot + ปุ่มปรับลด
 ├─ MovementList     สมุดสต็อก
 ├─ AdjustDownDialog ป๊อปอัพปรับลด (ฟอร์ม + ส่ง)
 └─ AdjustUpDialog   ป๊อปอัพปรับเพิ่ม (ฟอร์ม + ส่ง)
useAdjustStock      hook: POST คำสั่งปรับสต็อก แล้ว invalidate
```

อยู่ในไฟล์เดียวกันเพราะใช้แค่หน้านี้ (กฎ "ใช้ 2 ที่ขึ้นไปค่อยแยกไฟล์")
แต่แยกเป็นฟังก์ชันเพื่อให้**แต่ละป๊อปอัพถือ state ฟอร์มของตัวเอง** — หน้าหลักไม่ต้องรู้ว่าป๊อปอัพปรับลดมีช่องจำนวน

**ข้อมูลสามชุด — กุญแจขึ้นต้นด้วย `"products"` ทั้งหมด**

```jsx
const product = useQuery({ queryKey: ["products", id] });                // GET /products/{id}
const lots = useQuery({ queryKey: ["products", id, "lots"] });           // GET /products/{id}/lots
const moves = useQuery({ queryKey: ["products", id, "movements"] });     // GET /products/{id}/movements
```

**ทำไมต้องโหลดใหม่ทั้งสามชุดทุกครั้งที่บันทึก** เพราะทุกชุดเกี่ยวพันกันหมด —
ปรับลด Lot หนึ่งครั้งทำให้ `qty_remaining` ของ Lot เปลี่ยน · `qty_on_hand`
ของสินค้าเปลี่ยน · และมีแถวใหม่ในสมุด (และรายการสินค้าหน้า `/stock` ก็เปลี่ยนด้วย)

**ไม่ต้องจำเลยว่ามีกี่ชุด** — ทุกคำสั่งสั่ง `invalidateQueries({ queryKey: ["products"] })` ครั้งเดียว
ทุกกุญแจที่ขึ้นต้นด้วย `"products"` โดนหมด เฟส 4 เพิ่มข้อมูลใต้ `"products"` อีกก็ไม่ต้องกลับมาแก้ที่นี่

**`if (!p) return <DetailLayout title={product.error?.message || "กำลังโหลด…"} />`**

ยังไม่มีข้อมูล = กำลังโหลด หรือพัง — ถ้าพัง (เช่นเปิด `/stock/999`) backend ตอบ 404 "ไม่พบสินค้า"
ข้อความนั้นขึ้นเป็นหัวหน้าเลย (`?.` เพราะตอนกำลังโหลด `error` เป็น `null`)

**`dialog` — state ตัวเดียวบอกว่าป๊อปอัพไหนเปิด**

```jsx
const [dialog, setDialog] = useState(null); // null | "edit" | "up" | { downLot }

{dialog === "edit" && <ProductModal ... />}
{dialog === "up" && <AdjustUpDialog ... />}
{dialog?.downLot && <AdjustDownDialog lot={dialog.downLot} ... />}
```

ป๊อปอัพเปิดได้ทีละอันอยู่แล้ว ใช้ตัวแปรเดียวแทนการมี `editing` `upOpen` `downLot` แยกกันสามตัว
ปรับลดต้องรู้ว่า Lot ไหน เลยเก็บเป็น object `{ downLot: lot }` ส่วนอีกสองอันเป็นแค่ชื่อ
ปิดทุกอันด้วย `setDialog(null)` บรรทัดเดียว

**`useAdjustStock(path, onDone)` — hook ของเราเอง ห่อ `useMutation`**

```jsx
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
```

ปรับลดกับปรับเพิ่มทำเหมือนกันทุกอย่าง ต่างแค่ URL — เขียนครั้งเดียว
ชื่อขึ้นต้นด้วย `use` เพราะข้างในเรียก hook (`useQueryClient`, `useMutation`) — กฎของ React: ฟังก์ชันที่เรียก hook ต้องชื่อ `use...`

**ป๊อปอัพปรับลด — `useForm` + `useAdjustStock` + `ReasonDialog`**

```jsx
const { register, handleSubmit } = useForm({ defaultValues: { qty: "", reason: "" } });
const adjustDown = useAdjustStock("/stock/adjust-down", onClose);   // สำเร็จ → ปิด
...
onSubmit={handleSubmit((form) => adjustDown.mutate({ ...form, lot_id: lot.id }))}
//                                                  ^ qty + reason จากฟอร์ม · lot_id จาก prop
```

ท่าเดียวกับทุกฟอร์มในโปรเจกต์ (เฟส 1 ข้อ 14): **`useForm` ถือค่า · `useMutation` ส่ง · `handleSubmit` ต่อ**

**สองแท็บตอบคนละคำถาม**

| แท็บ | ตอบคำถาม |
|---|---|
| **Lot** | "ตอนนี้มีของอะไรอยู่บ้าง ต้นทุนเท่าไหร่" |
| **สมุดสต็อก** | "ของหายไปไหน ใครทำ เมื่อไหร่ เพราะอะไร" |

วางไว้ด้วยกันเพราะคนที่สงสัยเรื่องหนึ่งมักสงสัยอีกเรื่องต่อทันที

**การวางปุ่มตามกฎของ `DetailLayout`**

```
ปุ่มหลัก (footer)  → แก้สินค้า            ทุก staff
เมนู ⋯            → ปรับเพิ่ม/ตั้งต้น    เฉพาะ admin (ตรงกับสิทธิ์ backend)
ในแต่ละ Lot        → ปุ่มปรับลด           staff และเฉพาะ Lot ที่ยังมีของ
```

**`showCost={isAdmin}`** — ซ่อนเพื่อความเรียบร้อยของหน้าจอเท่านั้น
ของจริงคือ **backend ไม่ส่งต้นทุนมาให้ตั้งแต่แรกอยู่แล้ว** (`serialize_for_role` ข้อ 4)
ถ้าลบเงื่อนไขนี้ออก พนักงานก็ยังไม่เห็นต้นทุนอยู่ดี จะเห็นเป็นค่าว่าง

**prop ของ `LotList` ตั้งชื่อตามสิ่งที่มันทำ ไม่ใช่ตามบทบาท** — `showCost` `canAdjust` ไม่ใช่ `isAdmin` `isStaff`
`LotList` ไม่ต้องรู้ว่าระบบมีบทบาทอะไรบ้าง รู้แค่ "โชว์ต้นทุนไหม" "มีปุ่มปรับลดไหม"
วันที่กฎสิทธิ์เปลี่ยน แก้ที่หน้าหลักบรรทัดเดียว

**Lot ที่หมดแล้วทำให้จางลง แต่ไม่ซ่อน**

```jsx
const hasStock = Number(lot.qty_remaining) > 0;
<li className={hasStock ? "" : "text-muted"}>
```

ต้องเห็นประวัติครบว่าเคยมีของก้อนไหนบ้าง แต่ไม่ให้แย่งความสนใจจากของที่ยังมีอยู่
และปุ่มปรับลดก็ไม่ขึ้นสำหรับ Lot ที่หมดแล้ว (`canAdjust && hasStock`)

**`formatUnitPrice(lot.unit_cost)`** — ต้นทุนต่อหน่วยโชว์ทศนิยมเท่าที่มีจริง (สูงสุด 4 ตามที่ฐานเก็บ)
`100.0000` เห็นเป็น `100` ส่วน `333.3333` เห็นครบ — ถ้าใช้ `formatMoney` ที่ตัดเหลือ 2 ตำแหน่ง
เลขจะดูไม่ตรงกับยอดรวมที่คำนวณจากค่าเต็ม

**สมุดสต็อกใส่เครื่องหมาย + ให้ชัด และทำตัวลบเป็นสีแดง**

```jsx
const qty = Number(m.qty);
{qty > 0 ? "+" : ""}{formatQty(m.qty)}
```

`formatQty()` ไม่ใส่ `+` ให้เอง ต้องเติมเอง — กวาดตาแล้วแยกเข้า/ออกได้ทันที
แปลง `Number(m.qty)` ครั้งเดียวเก็บไว้ในตัวแปร ใช้สองที่ (เครื่องหมาย · สีแดง) ไม่ต้องแปลงซ้ำ

## 16. เมนูและ route

**ขั้นนี้ทำอะไร** ขั้นสุดท้าย — เพิ่มเมนูตัวแรกของระบบ และผูก URL เข้ากับหน้าที่ทำไว้

**เปิด** `frontend/src/components/AppLayout.jsx` — เติมเมนูตัวแรกของระบบ **ต้องแก้สองตัวแปร ไม่ใช่ตัวเดียว**

```jsx
export const GROUPS = ["คลังสินค้า"];
export const MENU = [
  { to: "/stock", label: "สต็อก", icon: "box", group: "คลังสินค้า" },
];
```

`group` ของเมนูต้องตรงกับชื่อใน `GROUPS` เป๊ะ ๆ เพราะ `SidebarContent` วาดเมนู
ด้วยการไล่ `GROUPS` แล้วหยิบเมนูที่ `group` ตรงกันมาใส่ใต้หัวข้อนั้น

**ใส่ `group` ผิดหรือลืมใส่ = เมนูไม่โผล่บนจอ และไม่มี error ให้เห็น** — ถ้าทำครบแล้ว
เมนูยังไม่ขึ้น ให้มาดูสองบรรทัดนี้ก่อนเลย

**เปิด** `frontend/src/main.jsx` → เติม import สามบรรทัด

```jsx
import ProductFormPage from "./pages/ProductFormPage";
import ProductListPage from "./pages/ProductListPage";
import ProductDetailPage from "./pages/ProductDetailPage";
```

→ แล้วเพิ่มบรรทัด `STAFF` ไว้เหนือ `ADMIN` ที่มีอยู่แล้วจากเฟส 2
**(ตรงนี้ไม่ใช่ import — เป็นตัวแปรธรรมดา)**

```jsx
const STAFF = ["admin", "employee"];
const ADMIN = ["admin"];
```

→ แล้วหาบรรทัด route หน้าแรกที่เขียนว่า `ยินดีต้อนรับ` **แทนที่ด้วยก้อนนี้**

```jsx
            <Route index element={<Navigate to="/stock" replace />} />
            <Route path="stock" element={<ProductListPage />}>
              <Route path="new" element={<Guard roles={STAFF}><ProductFormPage /></Guard>} />
            </Route>
            <Route path="stock/:id" element={<ProductDetailPage />} />
```

**อ่านโครง route นี้ยังไง — สังเกตว่ามีสองแบบปนกัน**

```jsx
<Route path="stock" element={<ProductListPage />}>          ← รายการ
  <Route path="new" ... />                        ← ลูก: ป๊อปอัพเปิดทับ
</Route>
<Route path="stock/:id" element={<ProductDetailPage />} />  ← พี่น้อง: หน้าเต็มคนละหน้า
```

| route | เป็นอะไร | เพราะ |
|---|---|---|
| `stock/new` | **ลูก** ของ `stock` | ฟอร์มสั้น ๆ เปิดทับรายการได้ (กฎจากเฟส 2) |
| `stock/:id` | **พี่น้อง** ของ `stock` | รายละเอียดเป็นหน้าเต็ม ไม่ได้ลอยทับ (เหตุผลในข้อ 11) |

ต่างจากเฟส 2 ที่ `settings/users/:id` เป็นลูก เพราะอันนั้นเป็นฟอร์มแก้ในป๊อปอัพ
ส่วนอันนี้เป็นคนละหน้าจริง ๆ

**`<Route index element={<Navigate to="/stock" replace />} />`**

เปลี่ยนหน้าแรกจาก "ยินดีต้อนรับ" ให้เด้งไปหน้าสต็อกเลย เพราะตอนนี้
เป็นหน้าเดียวที่มีงานให้ทำจริง (เฟส 5 จะเปลี่ยนเป็นหน้าใบงานอีกที)

**`Guard roles={STAFF}` บนฟอร์มเพิ่ม** — ซ่อนปุ่มอย่างเดียวไม่พอ
ช่างพิมพ์ `/stock/new` ลง URL ตรง ๆ ต้องเด้งกลับด้วย

---

## เช็คว่าเฟสนี้เสร็จ

### 1. คำสั่งต้องผ่านทั้งสองอัน

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

### 2. เตรียมข้อมูลไว้ใช้เฟสต่อไป

เพิ่มสินค้า 3-4 ตัว **เก็บไว้ใช้เฟส 4** เช่น

- ผ้าเบรกหน้า (หน่วย: ชิ้น)
- น้ำมันเครื่อง 1 ลิตร (หน่วย: **ขวด** — ปริมาตรอยู่ในชื่อสินค้า ไม่ใช่หน่วยนับ)
- หัวเทียน (หน่วย: ชิ้น)

### 3. ทดสอบ Lot — หัวใจของเฟสนี้

ที่หน้ารายละเอียดหัวเทียน:

1. ใส่**สต็อกตั้งต้น** 2 ชิ้น ต้นทุน 80
2. **ปรับเพิ่ม**อีก 3 ชิ้น ต้นทุน 120

ต้องได้: **Lot แยกกันสองอัน ตัวเก่า (80) อยู่บน** · คงเหลือรวม **5**

ถ้าเห็นเป็นก้อนเดียวหรือต้นทุนเฉลี่ย แปลว่า `adjust_up` ผิด — ย้อนไปข้อ 5

### 4. ทดสอบกฎต่าง ๆ

**ปรับลด**

- ไม่กรอกเหตุผล → กดไม่ผ่าน
- กรอกแล้ว → ผ่าน
- ลดเกินที่เหลือใน Lot นั้น → **ขึ้นข้อความพร้อมตัวเลขที่เหลือ**

**ป้ายเตือน**

- ตั้งจุดเตือนขั้นต่ำให้สูงกว่าของที่มี → ป้าย "ต่ำกว่าขั้นต่ำ" ขึ้นทันที
- กดกรอง "ต่ำกว่าขั้นต่ำ" → เจอสินค้าตัวนั้น
- ตั้งขั้นต่ำกลับเป็น 0 → ป้ายหายไป (ไม่ใช่เตือนตลอด)

**หน่วย**

- ลองเปลี่ยนหน่วยหัวเทียนเป็น "กล่อง" → ขึ้น "เปลี่ยนหน่วยไม่ได้…"

**สมุดสต็อก**

- เปิดแท็บสมุดสต็อก → เห็นทุกการเคลื่อนไหวพร้อม**ชื่อคนทำ**และเหตุผล
- รายการที่เป็นการลด ต้องเป็นตัวเลขติดลบสีแดง

**ข้อมูลอัปเดตเอง (TanStack Query)**

- ปรับลดใน Lot แล้ว → **คงเหลือด้านบน · Lot · สมุดสต็อก เปลี่ยนพร้อมกันทันที** ไม่ต้องรีเฟรช
- กดกลับไปหน้ารายการสต็อก → ยอดคงเหลือของสินค้าตัวนั้นเป็นเลขใหม่แล้ว
  (ถ้าเลขยังเก่า แปลว่า `invalidateQueries` ใช้กุญแจไม่ขึ้นต้นด้วย `"products"`)
- เปิดป๊อปอัพปรับลด พิมพ์ค้างไว้ → กดยกเลิก → เปิดใหม่ → **ช่องต้องว่าง**
- เปิด `/stock/999` → หัวหน้าขึ้น "ไม่พบสินค้า"

### 5. ทดสอบสิทธิ์ — ข้อที่สำคัญที่สุด

**ล็อกอินเป็น `emp1` (พนักงาน)**

- ไม่มีเมนู ⋯ ปรับเพิ่ม
- **ไม่เห็นบรรทัดต้นทุนใน Lot**
- DevTools → แท็บ Network → กดเปิดหน้ารายละเอียด → คลิกดู response
  ของ `/lots` → **ต้องไม่มีคำว่า `unit_cost` อยู่ในนั้นเลย**

ข้อสุดท้ายคือข้อที่พิสูจน์ว่ากันได้จริง ไม่ใช่แค่ซ่อนที่หน้าจอ
ถ้าเห็น `unit_cost` ใน response แปลว่า `serialize_for_role` ไม่ได้ถูกใช้ — ย้อนไปข้อ 5

**ล็อกอินเป็น `mech1` (ช่าง)**

- ไม่มีปุ่มเพิ่มสินค้า · ไม่มีปุ่มแก้ · ไม่มีปุ่มปรับลด
- แต่ยัง**เปิดดูของได้** (ช่างต้องเช็คของก่อนรับงาน)

### 6. มือถือ

- ยอดคงเหลือเป็นตัวใหญ่มุมขวาของการ์ด
- ปุ่มแก้สินค้าลอยติดขอบล่าง เลื่อนหน้ายังไงก็ยังอยู่

## git

```
docker compose run --rm api ruff check --fix .
docker compose run --rm api ruff format .
docker compose exec -T web npm run format
git add -A && git commit -m "feat: products and stock lots"
```
