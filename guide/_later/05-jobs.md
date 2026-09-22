# เฟส 5 — ลูกค้า รถ และใบงาน

**จบเฟสนี้แล้ว** รับรถ เปิดใบงาน ใส่รายการ เลือกช่าง กดลูกค้าอนุมัติแล้วสต็อกหายจริง พิมพ์ใบเสนอราคาส่งลูกค้าได้

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 1, 2 · `data_model.md` หัวข้อ 2, 5

> **ยังไม่ทำเฟสนี้** ออกบิล/รับเงิน (เฟส 6) · งานเคลม (เฟส 7) — โค้ดที่ให้ไว้เผื่อที่สำหรับสองอย่างนั้นไว้แล้ว

---

## กฎที่ต้องเข้าใจก่อนเขียน

### ลูกค้าและรถ
- **เบอร์โทรซ้ำได้** ครอบครัวใช้เบอร์เดียวกัน ถ้าบังคับไม่ซ้ำจะรับรถคันที่สองไม่ได้
- **ทะเบียน + จังหวัด ห้ามซ้ำ** ทะเบียนซ้ำข้ามจังหวัดได้ในความเป็นจริง
- ช่างเพิ่มลูกค้า/รถใหม่ได้ แต่แก้ของเดิมไม่ได้

### สถานะใบงาน — เดินหน้าทางเดียว

```
รอเริ่มซ่อม → กำลังซ่อม → เสร็จรอส่งมอบ → ปิดงาน
     └─ ยกเลิก (เฉพาะรอเริ่มซ่อม + ยังไม่อนุมัติ + ต้องมีเหตุผล)
```

- **เริ่มซ่อมก่อนลูกค้าอนุมัติไม่ได้**
- **ปิดงานโดยระบบเท่านั้น** ตอนรับเงินครบ ไม่มี endpoint ให้กดปิดเอง
- **รถหนึ่งคันมีใบงานค้างได้ใบเดียว**

### ช่าง
หนึ่งใบงานมีช่างหลายคน แต่ **ช่างหลักได้คนเดียว** (ใช้นับผลงาน ไม่ให้นับซ้ำตอนงานหนึ่งมีช่างสามคน)

### ราคา
**ราคาทุกจุดที่คุยกับลูกค้าคือราคารวม VAT แล้ว** พิมพ์ 5,000 ลูกค้าจ่าย 5,000 ระบบถอด VAT เองตอนออกบิล
ราคาตั้งต้นดึงจากสินค้า แก้ได้ แล้ว**เก็บค้างไว้กับใบงาน** ราคากลางเปลี่ยนทีหลังไม่กระทบใบงานเก่า

---

# ส่วน backend

## 1. ตารางที่เพิ่ม

```python
class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = created()
    vehicles: Mapped[list["Vehicle"]] = relationship(order_by="Vehicle.id", back_populates="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = fk("customers.id")
    plate: Mapped[str] = mapped_column(String(20))
    plate_province: Mapped[str] = mapped_column(String(50))
    vehicle_type: Mapped[str] = mapped_column(String(12))
    brand: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)
    customer: Mapped["Customer"] = relationship(back_populates="vehicles")
    __table_args__ = (
        UniqueConstraint("plate_province", "plate"),
        CheckConstraint("vehicle_type in ('car','motorcycle')", name="vehicle_type"),
        CheckConstraint("plate <> '' and plate_province <> ''", name="plate_required"),
    )


class JobOrder(Base):
    __tablename__ = "job_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = fk("vehicles.id")
    customer_id: Mapped[int] = fk("customers.id")
    mileage: Mapped[int]
    symptom: Mapped[str] = mapped_column(Text)
    warranty_source_invoice_id: Mapped[int | None] = fk("invoices.id", use_alter=True)
    claim_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12))
    labor_total: Mapped[Decimal] = mapped_column(MONEY, default=0, server_default="0")
    approved_by: Mapped[int | None] = fk("users.id")
    approved_at: Mapped[datetime | None] = mapped_column(TS)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[int | None] = fk("users.id")
    cancelled_at: Mapped[datetime | None] = mapped_column(TS)
    opened_by: Mapped[int] = fk("users.id")
    opened_at: Mapped[datetime] = created()
    closed_at: Mapped[datetime | None] = mapped_column(TS)
    vehicle: Mapped["Vehicle"] = relationship()
    customer: Mapped["Customer"] = relationship()
    items: Mapped[list["JobItem"]] = relationship(order_by="JobItem.id")
    mechanics: Mapped[list["JobMechanic"]] = relationship()
    __table_args__ = (
        CheckConstraint("status in ('pending','in_progress','done','closed','cancelled')", name="status"),
        CheckConstraint("(approved_at is null) = (approved_by is null)", name="approved"),
        CheckConstraint("status not in ('done','closed') or approved_at is not null", name="done_approved"),
        CheckConstraint("status <> 'cancelled' or (cancel_reason is not null and approved_at is null)",
                        name="cancel"),
        CheckConstraint("(warranty_source_invoice_id is null) = (claim_reason is null)", name="claim"),
        CheckConstraint("mileage >= 0 and labor_total >= 0", name="amounts"),
        Index("job_orders_one_active_per_vehicle", "vehicle_id", unique=True,
              postgresql_where=text("status not in ('closed','cancelled')")),
    )


class JobMechanic(Base):
    __tablename__ = "job_mechanics"
    job_id: Mapped[int] = mapped_column(ForeignKey("job_orders.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    is_primary: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    user: Mapped["User"] = relationship()
    __table_args__ = (
        Index("job_mechanics_one_primary", "job_id", unique=True, postgresql_where=text("is_primary")),
    )


class JobItem(Base):
    __tablename__ = "job_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = fk("job_orders.id")
    product_id: Mapped[int] = fk("products.id")
    description: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(20))
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_price: Mapped[Decimal] = mapped_column(PRICE)
    line_total: Mapped[Decimal] = mapped_column(MONEY)
    product: Mapped["Product"] = relationship()
    __table_args__ = (
        UniqueConstraint("job_id", "product_id"),
        CheckConstraint("qty > 0 and unit_price >= 0", name="qty_price"),
    )
```

### สอง partial index ที่เป็นกฎธุรกิจทั้งดุ้น

```python
Index("job_orders_one_active_per_vehicle", "vehicle_id", unique=True,
      postgresql_where=text("status not in ('closed','cancelled')"))
```
**"รถหนึ่งคันมีใบงานค้างได้ใบเดียว"** เขียนเป็น index ได้เลย — ไม่ซ้ำเฉพาะแถวที่ยังไม่ปิด/ยกเลิก ส่วนใบที่จบไปแล้วมีกี่ใบก็ได้
service ก็เช็คด้วย (เพื่อข้อความ error ที่บอกเลขใบงานที่ค้างอยู่) แต่ index คือตัวที่รับประกันจริง แม้สองคนกดพร้อมกัน

```python
Index("job_mechanics_one_primary", "job_id", unique=True, postgresql_where=text("is_primary"))
```
**"ช่างหลักได้คนเดียวต่อใบงาน"** — ไม่ซ้ำเฉพาะแถวที่ `is_primary` เป็นจริง ช่างร่วมมีกี่คนก็ได้

รูปแบบนี้ทรงพลังมาก **กฎแบบ "มีได้อย่างมากหนึ่ง เมื่อเงื่อนไข X" เขียนเป็น partial unique index ได้เสมอ** และ Postgres บังคับให้ 100%

**`CHECK status not in ('done','closed') or approved_at is not null`** — จะเสร็จหรือปิดงานได้ ต้องเคยอนุมัติ ป้องกันสภาพ "ซ่อมเสร็จโดยไม่เคยให้ลูกค้าอนุมัติ"

**`CHECK status <> 'cancelled' or (cancel_reason is not null and approved_at is null)`** — ยกเลิกต้องมีเหตุผล **และต้องยังไม่อนุมัติ** ถ้าอนุมัติแล้ว = ของถูกเบิกออกจากคลังไปแล้ว ยกเลิกเฉย ๆ คือของหายไปโดยไม่มีเอกสาร

**`CHECK (warranty_source_invoice_id is null) = (claim_reason is null)`** — งานเคลมต้องมีทั้งบิลต้นทางและอาการ หรือไม่มีทั้งคู่

**`fk("invoices.id", use_alter=True)`** — `job_orders` ชี้ไป `invoices` และ `invoices` ก็ชี้กลับมาที่ `job_orders` เป็นวงกลม `use_alter` บอกให้สร้างตารางก่อนแล้วค่อย `ALTER TABLE ADD CONSTRAINT` ทีหลัง ไม่งั้น migration สร้างไม่ได้เพราะไม่รู้จะสร้างตารางไหนก่อน

**`JobItem` เก็บ `description` และ `unit` ซ้ำกับ `products`** — ตั้งใจ ชื่อสินค้าเปลี่ยนทีหลังต้องไม่กระทบใบงานเก่า **ใบเสนอราคาที่พิมพ์ให้ลูกค้าเมื่อวานต้องพิมพ์ซ้ำได้เหมือนเดิม**

**`line_total` เก็บ ไม่คำนวณสด** — เหตุผลเดียวกัน มันคือเลขที่ตกลงกับลูกค้าแล้ว ไม่ใช่ผลคูณที่คำนวณใหม่ได้เรื่อย ๆ

**`UniqueConstraint("job_id", "product_id")`** สินค้าตัวเดียวอยู่แถวเดียวในใบงาน เพิ่มซ้ำ = เพิ่มจำนวนในแถวเดิม (หน้าจอทำให้)

## 2. `services/customers.py`

```python
import re

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app import timeutil
from app.db import get_or_404
from app.models import Customer, Invoice, JobOrder, Vehicle
from app.services.purchasing import digits


def no_spaces(s: str) -> str:
    return re.sub(r"\s", "", s)


def save_customer(db, customer_id, data) -> Customer:
    customer = get_or_404(db, Customer, customer_id, "ลูกค้า") if customer_id else Customer()
    phone = digits(data.phone)
    if not phone:
        raise HTTPException(422, "เบอร์โทรไม่ถูกต้อง")
    for key, value in {**data.model_dump(), "phone": phone, "tax_id": digits(data.tax_id)}.items():
        setattr(customer, key, value)
    db.add(customer)
    db.commit()
    return customer


def save_vehicle(db, vehicle_id, data) -> Vehicle:
    vehicle = get_or_404(db, Vehicle, vehicle_id, "รถ") if vehicle_id else Vehicle()
    get_or_404(db, Customer, data.customer_id, "ลูกค้า")
    plate = no_spaces(data.plate)
    if db.scalar(select(Vehicle.id).where(Vehicle.plate == plate,
                                          Vehicle.plate_province == data.plate_province,
                                          Vehicle.id != vehicle_id)):
        raise HTTPException(409, "ทะเบียนนี้มีในระบบแล้ว")
    for key, value in {**data.model_dump(), "plate": plate}.items():
        setattr(vehicle, key, value)
    db.add(vehicle)
    db.commit()
    return vehicle


def _match(q: str):
    conds = [Customer.name.ilike(f"%{q}%"), Vehicle.plate.ilike(f"%{no_spaces(q)}%")]
    if digits(q):
        conds.append(Customer.phone.like(f"%{digits(q)}%"))
    return or_(*conds)


def search_customers(db, q: str) -> list[Customer]:
    stmt = (select(Customer).outerjoin(Vehicle, Vehicle.customer_id == Customer.id)
            .options(selectinload(Customer.vehicles)).distinct().order_by(Customer.name).limit(50))
    if q.strip():
        stmt = stmt.where(_match(q.strip()))
    return db.scalars(stmt).all()


def search_vehicles(db, q: str) -> list[Vehicle]:
    stmt = (select(Vehicle).join(Customer, Customer.id == Vehicle.customer_id)
            .options(selectinload(Vehicle.customer)).order_by(Vehicle.id.desc()).limit(50))
    if q.strip():
        stmt = stmt.where(_match(q.strip()))
    return db.scalars(stmt).all()
```

**`no_spaces` กับ `digits` คือหัวใจของการค้นหาที่ใช้ได้จริง**

ลูกค้าพูดทะเบียนว่า "1กข 1234" พนักงานพิมพ์บ้าง "1กข1234" บ้าง เบอร์โทรก็ "081-234-5678" บ้าง "0812345678" บ้าง
**เก็บแบบ normalize แล้ว และ normalize คำค้นด้วยแบบเดียวกัน** ไม่งั้นค้นไม่เจอทั้งที่ข้อมูลอยู่ในระบบ

**`_match` ค้นทีเดียวได้ทั้งสามอย่าง** (ชื่อ / ทะเบียน / เบอร์) — พนักงานไม่ต้องเลือกว่าจะค้นด้วยอะไร พิมพ์ลงไปช่องเดียว
**เพิ่มเงื่อนไขเบอร์เฉพาะเมื่อคำค้นมีตัวเลข** (`if digits(q)`) ไม่งั้นค้นคำว่า "สมชาย" แล้ว `digits` คืน `None` ทำให้ query พัง

**`selectinload(Customer.vehicles)`** โหลดรถของลูกค้าทุกคนมาใน query เดียว ถ้าไม่ใส่ SQLAlchemy จะยิงทีละคน (ปัญหา N+1) — ลูกค้า 50 คน = 51 query

**`outerjoin` + `distinct()` ใน `search_customers`** — outer เพราะลูกค้าใหม่ที่ยังไม่มีรถต้องค้นเจอ · distinct เพราะ join แล้วลูกค้าที่มี 3 คันจะซ้ำ 3 แถว

**`save_customer` ไม่มีเช็คเบอร์ซ้ำ** ตั้งใจ ตามกฎ "เบอร์ซ้ำได้"

## 3. `services/jobs.py`

```python
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from app import timeutil
from app.db import get_or_404, lock_shop
from app.models import Customer, Invoice, JobItem, JobMechanic, JobOrder, User, Vehicle
from app.money import line_total
from app.schemas.customers import CustomerOut, VehicleBrief
from app.services.customers import no_spaces
from app.services.purchasing import digits, products_by_id
from app.services.stock import issue_fifo, return_issued

EDITABLE = ("pending", "in_progress")


def display(job_id: int) -> str:
    return f"JO-{job_id:05d}"


def _job(db, job_id) -> JobOrder:
    return get_or_404(db, JobOrder, job_id, "ใบงาน")


def _set_mechanics(db, job, mechanics) -> None:
    ids = [m.user_id for m in mechanics]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "เลือกช่างซ้ำกัน")
    if mechanics and sum(m.is_primary for m in mechanics) != 1:
        raise HTTPException(422, "ต้องมีช่างหลัก 1 คน")
    found = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))}
    for m in mechanics:
        u = found.get(m.user_id)
        if u is None or u.role != "mechanic" or not u.is_active:
            raise HTTPException(422, f"{u.full_name if u else 'ผู้ใช้นี้'} ไม่ใช่ช่าง")
    db.execute(delete(JobMechanic).where(JobMechanic.job_id == job.id))
    db.add_all(JobMechanic(job_id=job.id, user_id=m.user_id, is_primary=m.is_primary) for m in mechanics)
```

**`_set_mechanics` ลบทั้งหมดแล้วใส่ใหม่** — ง่ายกว่าไล่เทียบว่าใครเพิ่มใครออกเยอะ และถูกต้องแน่นอน เพราะอยู่ในทรานแซกชันเดียว
(ช่างในใบงานหนึ่งมี 1-3 คน จะมาคิดเรื่องประสิทธิภาพตรงนี้คือเสียเวลาเปล่า)

**`sum(m.is_primary for m in mechanics) != 1`** — `True` เป็น 1 ใน Python เลยนับได้ตรง ๆ **ต้องเท่ากับ 1 พอดี** ไม่ใช่ `<= 1` — เลือกช่างแล้วไม่มีหลักก็ไม่ได้
แต่ `if mechanics and ...` ยอมให้ไม่เลือกช่างเลยตอนเปิดใบงาน (ค่อยเลือกทีหลังก่อนอนุมัติ)

**เช็คว่าเป็น `mechanic` จริงและยัง `is_active`** — ไม่งั้นจะมอบหมายงานให้พนักงานบัญชีหรือคนที่ลาออกไปแล้วได้

### เปิดใบงาน

```python
def open_job(db, data, user) -> JobOrder:
    lock_shop(db)
    vehicle = get_or_404(db, Vehicle, data.vehicle_id, "รถ")
    claim_reason = data.claim_reason or None
    if (data.warranty_source_invoice_id is None) != (claim_reason is None):
        raise HTTPException(422, "งานเคลมต้องเลือกบิลเดิมและกรอกอาการที่กลับมา")
    active = db.scalar(select(JobOrder.id).where(JobOrder.vehicle_id == vehicle.id,
                                                 JobOrder.status.not_in(("closed", "cancelled"))))
    if active:
        raise HTTPException(409, f"รถคันนี้มีใบงานค้างอยู่ ({display(active)})")
    opened_at = timeutil.now()
    if data.warranty_source_invoice_id:
        check_claim(db, data.warranty_source_invoice_id, vehicle.id, opened_at)   # เฟส 7
    job = JobOrder(vehicle_id=vehicle.id, customer_id=vehicle.customer_id, mileage=data.mileage,
                   symptom=data.symptom, warranty_source_invoice_id=data.warranty_source_invoice_id,
                   claim_reason=claim_reason, status="pending", opened_by=user.id, opened_at=opened_at)
    db.add(job)
    db.flush()
    _set_mechanics(db, job, data.mechanics)
    db.commit()
    return job
```

**`customer_id` คัดลอกมาจากรถ ณ ตอนเปิด** ไม่ใช่ join เอาตอนอ่าน — รถขายต่อเปลี่ยนเจ้าของได้ ใบงานเก่าต้องยังบอกว่าตอนนั้นใครเป็นคนเอารถมา

**ข้อความ error บอกเลขใบงานที่ค้างอยู่** พนักงานเปิดใบนั้นต่อได้ทันที ไม่ต้องไปนั่งหา

**`opened_at` คำนวณครั้งเดียวแล้วใช้ซ้ำ** — ใช้ทั้งตรวจสิทธิ์ประกันและเก็บลงฐาน ถ้าเรียก `now()` สองครั้งจะได้คนละค่า (ต่างกันไม่กี่ไมโครวินาที แต่ตอนดีบักจะงง)

### แก้รายการ

```python
def save_items(db, job_id, data, user) -> JobOrder:
    lock_shop(db)
    job = _job(db, job_id)
    if job.status not in EDITABLE:
        raise HTTPException(409, "ใบงานสถานะนี้แก้รายการไม่ได้")
    if job.approved_at is not None:
        raise HTTPException(409, "รายการถูกล็อกหลังลูกค้าอนุมัติ ยกเลิกการอนุมัติก่อนแก้")
    products = products_by_id(db, [i.product_id for i in data.items], "ใบงาน")
    claim = job.warranty_source_invoice_id is not None
    db.execute(delete(JobItem).where(JobItem.job_id == job.id))
    for item in data.items:
        p = products[item.product_id]
        price = Decimal(0) if claim else (item.unit_price if item.unit_price is not None else p.sale_price)
        db.add(JobItem(job_id=job.id, product_id=p.id, description=p.name, unit=p.unit, qty=item.qty,
                       unit_price=price, line_total=line_total(item.qty, price)))
    job.labor_total = Decimal(0) if claim else data.labor_total
    db.commit()
    db.expire(job)
    return job
```

**API แทนที่รายการทั้งชุด ไม่ใช่เพิ่ม/ลบทีละแถว**
ฝั่งหน้าจอส่งรายการทั้งหมดที่ควรจะเป็นมา แล้วเซิร์ฟเวอร์ลบของเก่าเขียนใหม่
- ไม่มีปัญหาลำดับคำสั่งสลับกันตอนเน็ตช้า
- ไม่ต้องมี endpoint แยกสำหรับเพิ่ม ลบ แก้จำนวน แก้ราคา
- **สั่งซ้ำได้ผลเดิม (idempotent)** กดปุ่มรัว ๆ ก็ไม่เพี้ยน

**`price = item.unit_price if is not None else p.sale_price`** — ราคาตั้งต้นจากสินค้า แต่พิมพ์ทับได้ **และเก็บค้างไว้ที่ใบงาน** ขึ้นราคากลางพรุ่งนี้ใบงานวันนี้ไม่ขยับ

**`Decimal(0) if claim`** งานเคลมบังคับราคา 0 ที่ service ไม่ใช่ที่หน้าจอ ต่อให้ยิง API ตรง ๆ ใส่ราคามาก็โดนล้างเป็น 0

**`db.expire(job)`** บอก SQLAlchemy ให้ลืมค่าที่ cache ไว้แล้วอ่านใหม่ — ไม่งั้น `job.items` ยังเป็นรายการเก่าที่เพิ่งลบไป

### อนุมัติ — คำสั่งที่สำคัญที่สุดของระบบ

```python
def approve(db, job_id, user) -> JobOrder:
    lock_shop(db)
    job = _job(db, job_id)
    if job.status not in EDITABLE:
        raise HTTPException(409, "สถานะนี้อนุมัติไม่ได้")
    if job.approved_at is not None:
        raise HTTPException(409, "ใบงานนี้อนุมัติแล้ว")
    if not db.scalar(select(JobMechanic.user_id).where(JobMechanic.job_id == job.id,
                                                       JobMechanic.is_primary)):
        raise HTTPException(409, "ต้องเลือกช่างหลักก่อนอนุมัติ")
    if job.warranty_source_invoice_id:
        check_claim(db, job.warranty_source_invoice_id, job.vehicle_id, job.opened_at)   # เฟส 7
    for item in job.items:
        issue_fifo(db, item.product_id, item.qty, user, job_id=job.id)
    job.approved_by, job.approved_at = user.id, timeutil.now()
    db.commit()
    return job


def unapprove(db, job_id, user) -> JobOrder:
    lock_shop(db)
    job = _job(db, job_id)
    if job.status not in EDITABLE or job.approved_at is None:
        raise HTTPException(409, "ใบงานนี้ยกเลิกการอนุมัติไม่ได้")
    return_issued(db, user, job_id=job.id)
    job.approved_by = job.approved_at = None
    db.commit()
    return job
```

**"ลูกค้าอนุมัติ" ไม่ได้แค่เปลี่ยนสถานะ มันคือจุดที่ของออกจากคลังจริง**

ทำไมตัดของตอนอนุมัติ ไม่ใช่ตอนออกบิล
- ช่างต้องหยิบของไปใส่รถทันทีที่ลูกค้าตกลง ระบบต้องตรงกับความจริง
- ถ้ารอถึงตอนออกบิล อาจมีคนเอาของชิ้นนั้นไปใช้กับงานอื่นก่อน แล้วออกบิลไม่ได้ทั้งที่ซ่อมเสร็จแล้ว

**`issue_fifo` ทุกรายการ ถ้ารายการไหนไม่พอ → 409 และ rollback ทั้งชุด**
ไม่มีสภาพ "อนุมัติครึ่งใบ" — นี่คือกรณีตรวจรับข้อ 1

**เช็คช่างหลักด้วย query ไม่ใช่ `job.mechanics`** — ตรงกับ partial index ที่ฐานบังคับอยู่ และไม่ต้องพึ่งค่าที่ ORM cache ไว้

**`unapprove` คือทางแก้ของ "งานบานปลาย"** เจอของเสียเพิ่มตอนแกะเครื่อง ต้องเพิ่มอะไหล่ ระบบไม่ให้แก้รายการที่อนุมัติแล้ว (ของเบิกไปแล้ว ตัวเลขจะไม่ตรง)
ทางที่ถูกคือ **คืนของเข้า Lot เดิมก่อน แล้วค่อยแก้ แล้วให้ลูกค้าอนุมัติใหม่** ซึ่งตรงกับความจริง ลูกค้าต้องรับรู้ราคาใหม่ด้วย

**ทำไม `approve` เป็น staff แต่ `start`/`finish` ทุก role ทำได้** (ตรวจที่ router) — การอนุมัติคือการยืนยันว่าคุยราคากับลูกค้าแล้ว เป็นงานหน้าร้าน ส่วนเริ่ม/เสร็จคืองานช่าง

### สถานะและยกเลิก

```python
def _advance(db, job_id, current, target) -> JobOrder:
    lock_shop(db)
    job = _job(db, job_id)
    if job.status != current:
        raise HTTPException(409, "สถานะนี้ทำรายการนี้ไม่ได้")
    if job.approved_at is None:
        raise HTTPException(409, "ต้องให้ลูกค้าอนุมัติก่อนเริ่มซ่อม")
    job.status = target
    db.commit()
    return job


def start(db, job_id, user) -> JobOrder:
    return _advance(db, job_id, "pending", "in_progress")


def finish(db, job_id, user) -> JobOrder:
    return _advance(db, job_id, "in_progress", "done")


def cancel_job(db, job_id, reason, user) -> JobOrder:
    lock_shop(db)
    job = _job(db, job_id)
    if job.status != "pending" or job.approved_at is not None:
        raise HTTPException(409, "ใบงานที่อนุมัติแล้วหรือเริ่มซ่อมแล้วยกเลิกไม่ได้")
    job.status, job.cancel_reason = "cancelled", reason
    job.cancelled_by, job.cancelled_at = user.id, timeutil.now()
    db.commit()
    return job
```

**`_advance(current, target)` บังคับลำดับด้วยตัวมันเอง** — ข้ามขั้นไม่ได้เพราะสถานะปัจจุบันต้องตรงเป๊ะ ไม่ต้องเขียนตารางสถานะแยก
**ไม่มี `_advance(..., "closed")`** เพราะปิดงานเป็นหน้าที่ของการรับเงินเท่านั้น (เฟส 6)

### ประกอบข้อมูลให้หน้าจอ

```python
def list_jobs(db, status: str, q: str) -> list[JobOrder]:
    stmt = (select(JobOrder).join(Vehicle, Vehicle.id == JobOrder.vehicle_id)
            .join(Customer, Customer.id == JobOrder.customer_id)
            .options(selectinload(JobOrder.items), selectinload(JobOrder.vehicle),
                     selectinload(JobOrder.customer),
                     selectinload(JobOrder.mechanics).selectinload(JobMechanic.user))
            .order_by(JobOrder.id.desc()).limit(200))
    if status == "active":
        stmt = stmt.where(JobOrder.status.not_in(("closed", "cancelled")))
    elif status != "all":
        stmt = stmt.where(JobOrder.status == status)
    q = q.strip()
    if q:
        conds = [Customer.name.ilike(f"%{q}%"), Vehicle.plate.ilike(f"%{no_spaces(q)}%")]
        if digits(q):
            conds += [Customer.phone.like(f"%{digits(q)}%"), JobOrder.id == int(digits(q))]
        stmt = stmt.where(or_(*conds))
    return db.scalars(stmt).all()


def job_views(db, jobs) -> list[dict]:
    issued = {i.job_id: i for i in db.scalars(
        select(Invoice).where(Invoice.job_id.in_([j.id for j in jobs]), Invoice.status == "issued"))}
    views = []
    for job in jobs:
        inv = issued.get(job.id)
        parts = sum((i.line_total for i in job.items), Decimal(0))
        mechanics = sorted(job.mechanics, key=lambda m: (not m.is_primary, m.user.full_name))
        views.append({
            "id": job.id, "display_number": display(job.id), "status": job.status,
            "is_claim": job.warranty_source_invoice_id is not None,
            "approved": job.approved_at is not None,
            "vehicle_id": job.vehicle_id, "vehicle_plate": job.vehicle.plate,
            "vehicle_province": job.vehicle.plate_province, "vehicle_type": job.vehicle.vehicle_type,
            "customer_name": job.customer.name, "customer_phone": job.customer.phone,
            "primary_mechanic_name": next((m.user.full_name for m in mechanics if m.is_primary), None),
            "parts_total": parts, "total": parts + job.labor_total, "opened_at": job.opened_at,
            "invoice_id": inv.id if inv else None,
            "invoice_number": inv.display_number if inv else None,
            "invoice_paid": bool(inv and inv.received_at), "mechanics_sorted": mechanics,
            "warranty_expires_on": inv.warranty_expires_on if inv else None,
        })
    return views
```

**`job_views` รับ list ไม่ใช่ตัวเดียว** — โหลดบิลของทุกใบงานในหนึ่ง query (`Invoice.job_id.in_(...)`) แทนที่จะยิงต่อใบงาน
หน้ารายการ 200 ใบงานจะได้ไม่เกิด 200 query

**`selectinload(JobOrder.mechanics).selectinload(JobMechanic.user)`** โหลดสองชั้นลึกล่วงหน้า — ช่างของทุกใบงาน แล้วก็ข้อมูลผู้ใช้ของช่างทุกคน

**`sorted(key=lambda m: (not m.is_primary, m.user.full_name))`** ช่างหลักขึ้นก่อนเสมอ ที่เหลือเรียงตามชื่อ
`not m.is_primary` ทำให้ `False`(=0) มาก่อน `True`(=1) — สำนวนเรียงแบบ "ตัวนี้ขึ้นก่อน แล้วที่เหลือเรียงตาม..."

**`total` คำนวณจากรายการ ไม่เก็บ** ต่างจาก `line_total` ของแต่ละแถว — แถวเก็บเพราะเป็นราคาที่ตกลงกับลูกค้า ส่วนผลรวมคำนวณใหม่ได้เสมอและไม่มีวันไม่ตรง

`job_detail` เพิ่มข้อมูลที่หน้ารายละเอียดต้องใช้ (รายการ ช่างทั้งหมด ลูกค้า รถ ผู้อนุมัติ เหตุผลยกเลิก) ลงบน view เดิม — เขียนตามรูปแบบเดียวกับ `po_view` ในเฟส 4

## 4. schemas และ routers

```python
class JobIn(In):
    vehicle_id: int
    mileage: int = Field(ge=0)
    symptom: str = Field(min_length=1)
    warranty_source_invoice_id: int | None = None
    claim_reason: str | None = None
    mechanics: list[MechanicIn] = []


class ItemIn(In):
    product_id: int
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=0, decimal_places=4)


class ItemsIn(In):
    labor_total: Decimal = Field(ge=0, decimal_places=2)
    items: list[ItemIn]
```

**`JobListOut` กับ `JobOut`** — `JobOut` สืบทอดจาก `JobListOut` แล้วเติมของหนัก (รายการ ช่าง ลูกค้า รถ) หน้ารายการไม่ต้องรับข้อมูลที่ไม่ได้ใช้

**`items: list[ItemIn]` ไม่มี `min_length`** — ใบงานที่มีแต่ค่าแรงไม่มีอะไหล่เป็นเรื่องปกติ (เช่นล้างแอร์)

```python
router = APIRouter(prefix="/api/jobs", tags=["jobs"])
staff = require_role("admin", "employee")


@router.get("", response_model=list[JobListOut])
def list_jobs(status: str = "active", q: str = "", db=Depends(get_db), _=Depends(current_user)):
    return svc.job_views(db, svc.list_jobs(db, status, q))


@router.post("", response_model=JobOut, status_code=201)
def open_job(data: JobIn, db=Depends(get_db), user=Depends(current_user)):
    return svc.job_detail(db, svc.open_job(db, data, user))


@router.put("/{job_id}/items", response_model=JobOut)
def save_items(job_id: int, data: ItemsIn, db=Depends(get_db), user=Depends(current_user)):
    return svc.job_detail(db, svc.save_items(db, job_id, data, user))


@router.post("/{job_id}/approve", response_model=JobOut)
def approve(job_id: int, db=Depends(get_db), user=Depends(staff)):
    return svc.job_detail(db, svc.approve(db, job_id, user))


@router.post("/{job_id}/unapprove", response_model=JobOut)
def unapprove(job_id: int, db=Depends(get_db), user=Depends(staff)):
    return svc.job_detail(db, svc.unapprove(db, job_id, user))


@router.post("/{job_id}/start", response_model=JobOut)
def start(job_id: int, db=Depends(get_db), user=Depends(current_user)):
    return svc.job_detail(db, svc.start(db, job_id, user))


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel(job_id: int, data: ReasonIn, db=Depends(get_db), user=Depends(staff)):
    return svc.job_detail(db, svc.cancel_job(db, job_id, data.reason, user))
```
(`finish` และ `get_job` เขียนแบบเดียวกัน)

**ทุก endpoint คืน `JobOut` เต็ม** — หน้าจอได้สถานะล่าสุดทั้งใบทันทีหลังทำอะไรก็ตาม ไม่ต้องยิงถามซ้ำ

**สิทธิ์ตรงกับตารางใน `data_model.md` เป๊ะ** — `approve` / `unapprove` / `cancel` เป็น staff · เปิดใบงาน แก้รายการ เลือกช่าง เริ่ม/เสร็จ ทุก role

## 5. เทสต์ — `tests/test_jobs.py`

เพิ่ม fixture ใน `conftest.py`:

```python
@pytest.fixture
def make_vehicle():
    def make(plate="กข1234", phone="0811111111", name="ลูกค้า", **customer):
        with SessionLocal() as s:
            c = models.Customer(phone=phone, name=name, **customer)
            s.add(c)
            s.flush()
            v = models.Vehicle(customer_id=c.id, plate=plate,
                               plate_province="กรุงเทพมหานคร", vehicle_type="car")
            s.add(v)
            s.commit()
            return v.id
    return make
```

```python
def open_job(client, h, vid, role="admin", **extra):
    return client.post("/api/jobs", json={"vehicle_id": vid, "mileage": 50000,
                                          "symptom": "เบรกมีเสียง", **extra}, headers=h[role])


def test_approve_blocked_when_stock_short(client, h, make_vehicle, make_product, stock):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 2, "80")
    job = open_job(client, h, vid).json()
    client.put(f"/api/jobs/{job['id']}/items",
               json={"labor_total": "500", "items": [{"product_id": pid, "qty": "3"}]}, headers=h["admin"])
    client.put(f"/api/jobs/{job['id']}/mechanics",
               json={"mechanics": [{"user_id": mech_id, "is_primary": True}]}, headers=h["admin"])

    r = client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"])
    assert r.status_code == 409
    # สต็อกต้องไม่ขยับ
    assert client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()[0]["qty_remaining"] == "2.000"


def test_mechanic_cannot_approve(client, h, make_vehicle):
    job = open_job(client, h, make_vehicle()).json()
    assert client.post(f"/api/jobs/{job['id']}/approve", headers=h["mechanic"]).status_code == 403


def test_cannot_start_before_approval(client, h, make_vehicle):
    job = open_job(client, h, make_vehicle()).json()
    assert client.post(f"/api/jobs/{job['id']}/start", headers=h["admin"]).status_code == 409


def test_one_active_job_per_vehicle(client, h, make_vehicle):
    vid = make_vehicle()
    assert open_job(client, h, vid).status_code == 201
    assert open_job(client, h, vid).status_code == 409


def test_cancel_rules(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "80")
    job = open_job(client, h, vid).json()
    assert client.post(f"/api/jobs/{job['id']}/cancel",
                       json={"reason": ""}, headers=h["admin"]).status_code == 422

    mech = users["mechanic"].id
    client.put(f"/api/jobs/{job['id']}/items",
               json={"labor_total": "0", "items": [{"product_id": pid, "qty": "1"}]}, headers=h["admin"])
    client.put(f"/api/jobs/{job['id']}/mechanics",
               json={"mechanics": [{"user_id": mech, "is_primary": True}]}, headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"])
    assert client.post(f"/api/jobs/{job['id']}/cancel",
                       json={"reason": "ลูกค้าเปลี่ยนใจ"}, headers=h["admin"]).status_code == 409


def test_unapprove_returns_to_same_lot(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "80")
    mech = users["mechanic"].id
    job = open_job(client, h, vid).json()
    client.put(f"/api/jobs/{job['id']}/items",
               json={"labor_total": "0", "items": [{"product_id": pid, "qty": "2"}]}, headers=h["admin"])
    client.put(f"/api/jobs/{job['id']}/mechanics",
               json={"mechanics": [{"user_id": mech, "is_primary": True}]}, headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/start", headers=h["admin"])

    assert client.post(f"/api/jobs/{job['id']}/unapprove", headers=h["admin"]).status_code == 200
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert len(lots) == 1                         # ต้องไม่เกิด Lot ใหม่
    assert lots[0]["qty_remaining"] == "5.000"    # ของกลับเข้า Lot เดิมครบ


def test_primary_mechanic_rules(client, h, make_vehicle, users):
    job = open_job(client, h, make_vehicle()).json()
    mech, emp = users["mechanic"].id, users["employee"].id
    url = f"/api/jobs/{job['id']}/mechanics"

    # ไม่มีช่างหลัก
    assert client.put(url, json={"mechanics": [{"user_id": mech, "is_primary": False}]},
                      headers=h["admin"]).status_code == 422
    # คนที่ไม่ใช่ช่าง
    assert client.put(url, json={"mechanics": [{"user_id": emp, "is_primary": True}]},
                      headers=h["admin"]).status_code == 422
    # ไม่มีช่างหลัก → อนุมัติไม่ได้
    assert client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"]).status_code == 409
```

**เทสต์สำคัญที่สุดสองข้อ**
- `test_approve_blocked_when_stock_short` — ไม่ใช่แค่ได้ 409 แต่ต้องพิสูจน์ว่า**สต็อกไม่ขยับ** (ข้อ 1)
- `test_unapprove_returns_to_same_lot` — ต้องเช็คว่า **`len(lots) == 1`** ไม่ใช่แค่ยอดรวมถูก ถ้าโค้ดสร้าง Lot ใหม่ ยอดรวมจะถูกแต่ต้นทุนจะพังในระยะยาว (ข้อ 7)

---

# ส่วนหน้าจอ

## 6. `components/MechanicPicker.jsx`

```jsx
// value: [{ user_id, is_primary }]
export default function MechanicPicker({ mechanics, value, onChange }) {
  if (!mechanics) return <p className="text-muted">กำลังโหลด…</p>;
  if (mechanics.length === 0) return <p className="text-muted">ยังไม่มีผู้ใช้ที่เป็นช่าง</p>;
  const picked = (id) => value.find((m) => m.user_id === id);
  const toggle = (id, on) => onChange(on
    ? [...value, { user_id: id, is_primary: value.length === 0 }]
    : value.filter((m) => m.user_id !== id));
  const setPrimary = (id) => onChange([
    ...value.filter((m) => m.user_id !== id).map((m) => ({ ...m, is_primary: false })),
    { user_id: id, is_primary: true },
  ]);
  const noPrimary = value.length > 0 && !value.some((m) => m.is_primary);

  return (
    <fieldset className="space-y-2">
      <legend className="sr-only">เลือกช่าง</legend>
      {mechanics.map((u) => {
        const m = picked(u.id);
        return (
          <div key={u.id} className={`flex items-center gap-2 rounded-lg border p-1.5
                                      ${m ? "border-accent bg-accent-soft" : "border-line"}`}>
            <label className="flex min-h-11 flex-1 cursor-pointer items-center gap-3 px-2">
              <input type="checkbox" className="size-5 accent-accent" checked={!!m}
                     onChange={(e) => toggle(u.id, e.target.checked)} />
              <span className="font-medium">{u.full_name}</span>
            </label>
            <label className="flex min-h-11 cursor-pointer items-center gap-2 px-2 text-sm">
              <input type="radio" name="primary-mechanic" className="size-5 accent-accent"
                     checked={!!m?.is_primary} onChange={() => setPrimary(u.id)} />
              ช่างหลัก
            </label>
          </div>
        );
      })}
      {noPrimary && <p className="field-error">เลือกช่างหลัก 1 คน (ต้องมีก่อนลูกค้าอนุมัติ)</p>}
    </fieldset>
  );
}
```

**checkbox + radio ในแถวเดียว** — checkbox ตอบว่า "ทำงานนี้ไหม" (หลายคนได้) radio ตอบว่า "ใครเป็นหลัก" (คนเดียว) ตรงกับกฎเป๊ะ และ radio ที่ `name` เดียวกันเบราว์เซอร์บังคับเลือกได้อันเดียวให้เอง

**`is_primary: value.length === 0`** — คนแรกที่เลือกได้เป็นช่างหลักอัตโนมัติ ส่วนใหญ่งานมีช่างคนเดียว กดครั้งเดียวจบ

**`setPrimary` ล้าง `is_primary` ของคนอื่นก่อนเสมอ** — ป้องกันสภาพช่างหลักสองคนที่ทั้ง service และ partial index จะปฏิเสธ

**`fieldset` + `legend`** กลุ่ม input ที่เกี่ยวข้องกันต้องมี label ของกลุ่ม ไม่งั้น screen reader อ่านทีละช่องแล้วไม่รู้ว่ากำลังเลือกอะไร

## 7. `pages/JobsPage.jsx`

```jsx
import { useState } from "react";
import { money, thaiDate, useApi } from "../api";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import StatusBadge, { jobKey, waitingApproval } from "../components/StatusBadge";
import SearchBar from "../components/SearchBar";

const FILTERS = [
  ["active", "ค้างอยู่"], ["pending", "รอเริ่มซ่อม"], ["in_progress", "กำลังซ่อม"],
  ["done", "เสร็จรอส่งมอบ"], ["closed", "ปิดแล้ว"], ["cancelled", "ยกเลิก"],
];

function Flags({ job }) {
  if (!waitingApproval(job) && !job.is_claim) return null;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {waitingApproval(job) && <StatusBadge status="unapproved" />}
      {job.is_claim && <StatusBadge status="claim" />}
    </span>
  );
}

export default function JobsPage() {
  const [status, setStatus] = useState("active");
  const [q, setQ] = useState("");
  const { data, error, reload } = useApi(`/jobs?${new URLSearchParams({ status, q: q.trim() })}`);

  return (
    <ListLayout title="ใบงาน" basePath="/jobs" context={{ reload }}
      action={{ label: "เปิดใบงาน", to: "/jobs/new" }}
      toolbar={<SearchBar q={q} setQ={setQ} placeholder="ค้นทะเบียน ชื่อ เบอร์ หรือเลขใบงาน"
                        filters={FILTERS} filter={status} setFilter={setStatus} />}>
      {error && <p role="alert" className="field-error">{error}</p>}
      <DataTable items={data} to={(j) => `/jobs/${j.id}`} empty="ไม่มีใบงาน"
        card={(j) => (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-muted">{j.display_number}</span>
              <StatusBadge status={jobKey(j)} />
            </div>
            <div className="mt-1 text-lg font-bold">
              {j.vehicle_plate} <span className="text-sm font-normal text-muted">{j.vehicle_province}</span>
            </div>
            <div className="truncate text-sm">{j.customer_name} · {j.customer_phone}</div>
            <div className="mt-2"><Flags job={j} /></div>
            <div className="mt-2 flex justify-between gap-2 text-sm">
              <span className="truncate text-muted">{j.primary_mechanic_name ?? "ยังไม่มีช่างหลัก"}</span>
              <span className="num font-semibold">{money(j.total)}</span>
            </div>
          </>
        )}
        columns={[
          { label: "เลขที่", render: (j) => j.display_number },
          { label: "ทะเบียน", render: (j) => `${j.vehicle_plate} ${j.vehicle_province}` },
          { label: "ลูกค้า", render: (j) => j.customer_name },
          { label: "สถานะ", render: (j) => (
              <span className="inline-flex flex-wrap gap-1">
                <StatusBadge status={jobKey(j)} /><Flags job={j} />
              </span>) },
          { label: "ช่างหลัก", render: (j) => j.primary_mechanic_name ?? "-" },
          { label: "ยอด", align: "right", render: (j) => money(j.total) },
          { label: "วันที่เปิด", render: (j) => thaiDate(j.opened_at) },
        ]} />
    </ListLayout>
  );
}
```

เพิ่มใน `StatusBadge.jsx`:

```jsx
pending: ["รอเริ่มซ่อม", "neutral"],
in_progress: ["กำลังซ่อม", "info"],
done: ["เสร็จรอส่งมอบ", "ok"],
job_closed: ["ปิดงานแล้ว", "neutral"],
unapproved: ["รออนุมัติ", "warn"],
claim: ["งานเคลม", "info"],

export const jobKey = (job) => (job.status === "closed" ? "job_closed" : job.status);
export const waitingApproval = (job) => !job.approved && ["pending", "in_progress"].includes(job.status);
```

**ป้ายสองชั้น: สถานะ + ธง** — "กำลังซ่อม" คือสถานะ ส่วน "รออนุมัติ" กับ "งานเคลม" เป็นข้อมูลคนละแกน ใบงานหนึ่งเป็นได้ทั้ง "กำลังซ่อม + งานเคลม" พร้อมกัน

**"รออนุมัติ" เป็นสีเหลือง = ต้องทำอะไรสักอย่าง** พนักงานกวาดตาดูรายการแล้วเห็นทันทีว่าใบไหนค้างรอตัวเอง

**`jobKey` แปลง `closed` เป็น `job_closed`** เพราะตาราง `STATUS` มี key `closed` ของ PO อยู่แล้ว (คำว่า "ปิดแล้ว") แต่ใบงานควรอ่านว่า "ปิดงานแล้ว"

**ทะเบียนรถเป็นตัวใหญ่สุดบนการ์ด** — คนที่เปิดหน้านี้กำลังมองหารถคันหนึ่ง ไม่ได้มองหาเลขใบงาน

**ค้นหายิง API (ไม่กรองในเบราว์เซอร์แบบหน้าสต็อก)** — ใบงานสะสมเป็นพัน โหลดมาทั้งหมดไม่ไหว และ backend ค้นได้ทั้งเบอร์/ทะเบียน/ชื่อ/เลขใบงานอยู่แล้ว

## 8. `pages/JobNewPage.jsx` — ป๊อปอัพรับรถ

ฟอร์มนี้ต้องทำสามอย่างในจอเดียว: **หาลูกค้า → เลือก/เพิ่มรถ → กรอกอาการ**

```jsx
export default function JobNewPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { reload, close } = useOutletContext();
  const mechanics = useApi("/users/mechanics");
  const [q, setQ] = useState("");
  const search = q.trim();
  const found = useApi(search.length >= 2 ? `/customers?${new URLSearchParams({ q: search })}` : "");
  const [vehicleId, setVehicleId] = useState(params.get("vehicle") || "");
  const picked = useApi(vehicleId ? `/vehicles/${vehicleId}/history` : "");
  const [newFor, setNewFor] = useState(null);  // "customer" = ลูกค้าใหม่ · object = ลูกค้าเดิมเพิ่มรถ
  const [customer, setCustomer] = useState(BLANK_CUSTOMER);
  const [vehicle, setVehicle] = useState(BLANK_VEHICLE);
  const [createdCustomerId, setCreatedCustomerId] = useState(null);
  const [job, setJob] = useState({ mileage: "", symptom: "" });
  const [crew, setCrew] = useState([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    setBusy(true);
    try {
      let vid = vehicleId;
      if (!vid) {
        let customerId = newFor === "customer" ? createdCustomerId : newFor.id;
        if (!customerId) {
          customerId = (await api("/customers", { method: "POST", body: customer })).id;
          setCreatedCustomerId(customerId);   // ลองใหม่หลังรถ error ต้องไม่สร้างลูกค้าซ้ำ
        }
        vid = String((await api("/vehicles", { method: "POST",
                                 body: { ...vehicle, customer_id: customerId } })).id);
        setVehicleId(vid);
        setNewFor(null);
      }
      const created = await api("/jobs", { method: "POST", body: {
        vehicle_id: Number(vid), mileage: Number(job.mileage), symptom: job.symptom, mechanics: crew,
      } });
      reload();
      navigate(`/jobs/${created.id}`);
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  };
  // ... ส่วนวาด (ดูด้านล่าง)
}
```

**สามสถานะของส่วน "รถที่เข้าซ่อม"**

| สถานะ | แสดงอะไร |
|---|---|
| `vehicleId` มีค่า | การ์ดรถที่เลือก + ปุ่ม "เปลี่ยน" |
| `newFor` มีค่า | ฟอร์มกรอกลูกค้า/รถใหม่ |
| ทั้งคู่ว่าง | ช่องค้นหา + ผลลัพธ์ |

```jsx
<section className="space-y-3">
  <h3 className="font-semibold">รถที่เข้าซ่อม</h3>
  {vehicleId ? (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-accent
                    bg-accent-soft p-3">
      {v ? (
        <div className="min-w-0">
          <div className="text-lg font-bold">
            {v.plate} <span className="text-sm font-normal">{v.plate_province}</span>
          </div>
          <div className="text-sm">
            {[VEHICLE_TYPE[v.vehicle_type], v.brand, v.model].filter(Boolean).join(" ")}
          </div>
          <div className="text-sm text-muted">{owner.name} · {owner.phone}</div>
          {picked.data.last_mileage != null && (
            <div className="num text-sm text-muted">ไมล์ล่าสุด {qty(picked.data.last_mileage)} กม.</div>
          )}
        </div>
      ) : <span className="text-muted">{picked.error || "กำลังโหลด…"}</span>}
      <button type="button" className="btn btn-secondary"
              onClick={() => setVehicleId("")}>เปลี่ยน</button>
    </div>
  ) : newFor ? (
    /* ฟอร์มลูกค้า/รถใหม่ */
  ) : (
    <>
      <SearchBar q={q} setQ={setQ} placeholder="ค้นเบอร์ ชื่อ หรือทะเบียน" />
      {search.length < 2 && <p className="text-sm text-muted">พิมพ์อย่างน้อย 2 ตัวอักษร</p>}
      {search.length >= 2 && found.data?.length === 0 &&
        <p className="text-sm text-muted">ไม่พบลูกค้า เพิ่มเป็นลูกค้าใหม่ได้</p>}
      <ul className="space-y-2">
        {found.data?.map((c) => (
          <li key={c.id} className="rounded-lg border border-line p-3">
            <div className="font-semibold">{c.name}</div>
            <div className="text-sm text-muted">{c.phone}</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {c.vehicles.map((car) => (
                <button key={car.id} type="button" className="btn btn-secondary"
                        onClick={() => setVehicleId(String(car.id))}>
                  <Icon name="car" size={20} />{car.plate} {car.plate_province}
                </button>
              ))}
              <button type="button" className="btn btn-ghost" onClick={() => startNew(c)}>
                <Icon name="plus" size={20} />เพิ่มรถ
              </button>
            </div>
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn-secondary w-full" onClick={() => startNew("customer")}>
        <Icon name="plus" size={20} />ลูกค้าใหม่
      </button>
    </>
  )}
</section>
```

**ค้นครั้งเดียวได้ทั้งลูกค้าและรถ แล้วแสดงรถทุกคันของลูกค้าเป็นปุ่ม** — ลูกค้าบอกเบอร์ พนักงานพิมพ์ ขึ้นชื่อพร้อมรถ 2 คัน กดคันที่ถูก **จบใน 2 การกระทำ**

**`search.length >= 2` ถึงจะยิง** — พิมพ์ตัวเดียวแล้วค้นได้ผลครึ่งฐาน เปลืองเปล่า

**`createdCustomerId` แก้บั๊กที่เจอจริง**
สร้างลูกค้าสำเร็จ → สร้างรถพัง (ทะเบียนซ้ำ) → ผู้ใช้แก้ทะเบียนแล้วกดใหม่ → **ถ้าไม่จำ id ไว้ จะสร้างลูกค้าซ้ำอีกคน** ทุกครั้งที่กด
นี่คือปัญหาคลาสสิกของฟอร์มที่ยิง API หลายก้อนต่อกัน — จำสิ่งที่สำเร็จไปแล้วไว้เสมอ

**แสดง "ไมล์ล่าสุด" จากประวัติรถ** (endpoint ของเฟส 7 — ถ้ายังไม่มี ข้ามส่วนนี้ไปก่อน) เลขไมล์ต้องมากกว่าครั้งก่อน มีให้เทียบแล้วพิมพ์ผิดยาก

**ปุ่มเลือกรถเป็น `type="button"` ทุกอัน** — อยู่ใน `<form>` ลืมใส่แล้วกดแล้วฟอร์มจะ submit ทันที

## 9. `pages/JobPage.jsx` — หน้าที่ใหญ่ที่สุดในระบบ

ทั้งใบงานจบในหน้าเดียว: ข้อมูลรถ → รายการ → ช่าง → ปุ่มขั้นถัดไป

### ปุ่มหลักเปลี่ยนตามสถานะ

```jsx
let primary = null;
if (isStaff && editable)
  primary = { label: "ลูกค้าอนุมัติ", icon: "check", onClick: () => step("approve") };
else if (job.approved && job.status === "pending")
  primary = { label: "เริ่มซ่อม", icon: "wrench", onClick: () => step("start") };
else if (job.approved && job.status === "in_progress")
  primary = { label: "ซ่อมเสร็จ", icon: "check", onClick: () => step("finish") };
// เฟส 6 มาเติมต่อ: ออกบิลและรับเงิน / รับเงิน

const menu = [
  ...(isStaff && open && job.approved
      ? [{ label: "ยกเลิกการอนุมัติ", danger: true, onClick: () => setModal("unapprove") }] : []),
  ...(isStaff && job.status === "pending" && !job.approved
      ? [{ label: "ยกเลิกใบงาน", danger: true, onClick: () => setModal("cancel") }] : []),
];
```

**หัวใจของหน้านี้: มีปุ่มใหญ่ปุ่มเดียวเสมอ และมันคือสิ่งที่ควรทำต่อ**

พนักงานไม่ต้องจำว่าขั้นตอนถัดไปคืออะไร หน้าจอบอกเอง — ที่เหลือไปอยู่ในเมนู ⋯
และลำดับ `if/else` นี้**สะท้อนสถานะที่ service อนุญาตพอดี** ผู้ใช้เลยแทบไม่มีทางเจอ error "สถานะนี้ทำรายการนี้ไม่ได้"

**ช่างที่เปิดหน้าใบงานที่ยังไม่อนุมัติ เห็นข้อความแทนปุ่ม** — "รอพนักงานกดลูกค้าอนุมัติ" บอกว่าต้องรอใคร ไม่ใช่ปุ่มที่กดแล้วเด้ง 403

### รายการแก้ในที่

```jsx
const putItems = async (items, laborTotal) => {
  await api(`/jobs/${id}/items`, { method: "PUT", body: {
    labor_total: job.is_claim ? "0" : laborTotal || "0",
    items: items.map((it) => ({
      product_id: it.product_id, qty: String(Number(it.qty)),
      unit_price: job.is_claim ? null : String(Number(it.unit_price)),
    })),
  } });
  reload();
};
```

**ทุกการเปลี่ยนแปลงส่งรายการทั้งชุด** ตรงกับ API ที่ออกแบบไว้ — ลบแถว = ส่งรายการที่ไม่มีแถวนั้น

**ช่องค่าแรงบันทึกตอน `onBlur` ไม่ใช่ทุกตัวอักษร**

```jsx
<input className="input num text-right" type="number" value={labor}
  onChange={(e) => setLabor(e.target.value)}
  onBlur={() => Number(labor || 0) !== Number(job.labor_total) && run(() => putItems(job.items, labor))} />
```
พิมพ์ "1500" = 4 ครั้งที่เปลี่ยน ถ้ายิงทุกครั้งคือ 4 request และค่ากลางคัน (1, 15, 150) ถูกบันทึกลงฐานจริง ๆ
`onBlur` ยิงครั้งเดียวตอนออกจากช่อง **และเช็คว่าค่าเปลี่ยนจริงก่อนยิง** คลิกเข้าออกเฉย ๆ ไม่ต้องยิง

### ป๊อปอัพเพิ่มอะไหล่

```jsx
const existing = job.items.find((it) => it.product_id === picked.id);
const items = existing
  ? job.items.map((it) => (it === existing
      ? { ...it, qty: Number(it.qty) + Number(count), unit_price: price } : it))
  : [...job.items, { product_id: picked.id, qty: count, unit_price: price }];
```
**เลือกสินค้าเดิมซ้ำ = บวกจำนวนในแถวเดิม ไม่ใช่สร้างแถวที่สอง** — ตรงกับ `UniqueConstraint(job_id, product_id)` ที่ฐาน ถ้าปล่อยให้เพิ่มซ้ำจะโดน 409 ตอนบันทึก

```jsx
const short = picked && Number(count) > Number(picked.qty_on_hand);
...
{short && <span className="field-hint font-semibold text-danger">ไม่พอ ต้องรับของเข้าก่อนอนุมัติ</span>}
```
**เตือนตั้งแต่ตอนใส่ ไม่ปล่อยให้ไปตายตอนกดอนุมัติ** — แต่**ยังใส่ได้** เพราะใบเสนอราคาต้องมีของครบตามที่ลูกค้าจะซ่อม แล้วค่อยสั่งของเข้ามา
การตรวจจริงยังอยู่ที่ `approve` ที่เซิร์ฟเวอร์เหมือนเดิม

**ปุ่ม +/− ข้างช่องจำนวน** — ส่วนใหญ่ 1-2 ชิ้น กดปุ่มเร็วกว่าพิมพ์บนมือถือมาก

### ส่วนอื่นของหน้า

```jsx
<dl className="divide-y divide-line rounded-xl border border-line text-sm">
  <Row label="รถ">{...} · <span className="num">{qty(job.mileage)}</span> กม.</Row>
  <Row label="อาการ">{job.symptom}</Row>
  <Row label="ช่าง">
    {open ? (
      <button type="button" className={`... ${noPrimary ? "text-danger" : "text-accent"}`}
              onClick={() => setModal("mechanics")}>
        {crew || "เลือกช่าง (ต้องมีช่างหลักก่อนอนุมัติ)"}<Icon name="chevron" size={18} />
      </button>
    ) : crew || "-"}
  </Row>
  <Row label="เปิดโดย">{job.opened_by_name} · {thaiDateTime(job.opened_at)}</Row>
  {job.approved && <Row label="ลูกค้าอนุมัติ">{job.approved_by_name} · {thaiDateTime(job.approved_at)}</Row>}
</dl>
```

**เบอร์ลูกค้าเป็น `<a href="tel:...">`** อยู่ใน subtitle — บนมือถือกดแล้วโทรออกได้เลย ไม่ต้องจดเบอร์

**แสดง "ใครอนุมัติ เมื่อไหร่"** — ระบบนี้ไม่มี audit log ทุกขั้นตอน แต่เก็บผู้ทำและเวลาของ**เหตุการณ์สำคัญ**ไว้บนเอกสาร เพราะเป็นหลักฐานที่ต้องตอบได้จริงเวลามีปัญหา

**ช่องช่างเป็นสีแดงเมื่อยังไม่มีช่างหลัก** — บอกล่วงหน้าว่าจะติดตรงนี้ตอนกดอนุมัติ

## 10. `pages/PrintQuotePage.jsx`

```jsx
import { useParams } from "react-router-dom";
import { carName, money, qty, thaiDate, useApi } from "../api";
import PrintLayout, { Party, PrintTable, Signatures } from "../components/PrintLayout";

export default function PrintQuotePage() {
  const { id } = useParams();
  const { data: j, error } = useApi(`/jobs/${id}`);
  const rows = j ? [
    ...j.items.map((i, k) => [k + 1, i.description, qty(i.qty), i.unit,
                              money(i.unit_price), money(i.line_total)]),
    [j.items.length + 1, "ค่าแรง", "1", "งาน", money(j.labor_total), money(j.labor_total)],
  ] : [];

  return (
    <PrintLayout title="ใบเสนอราคา" number={j?.display_number} date={j && thaiDate(j.opened_at)}
                 loading={!j} error={error}>
      {j && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <Party title="ลูกค้า" lines={[j.customer.name, `โทร ${j.customer.phone}`, j.customer.address]} />
            <Party title="รถ" lines={[`${j.vehicle.plate} ${j.vehicle.plate_province}`,
                                      carName(j.vehicle), `เลขไมล์ ${qty(j.mileage)} กม.`]} />
          </div>
          <Party title="อาการ / งานที่แจ้ง" lines={[j.symptom]} />
          <PrintTable head={[["ลำดับ"], ["รายการ"], ["จำนวน", true], ["หน่วย"],
                             ["ราคา/หน่วย", true], ["จำนวนเงิน", true]]}
            rows={rows} foot={[["รวมทั้งสิ้น (ราคารวมภาษีมูลค่าเพิ่มแล้ว)", money(j.total), true]]} />
          <p className="text-muted">ราคาประเมินจากอาการที่ตรวจพบ หากพบความเสียหายเพิ่มเติม
             อู่จะแจ้งลูกค้าก่อนดำเนินการทุกครั้ง</p>
          <Signatures labels={["ผู้เสนอราคา", "ลูกค้าอนุมัติ"]} />
        </>
      )}
    </PrintLayout>
  );
}
```

**ค่าแรงเป็นแถวสุดท้ายของตาราง** — ลูกค้าเห็นค่าอะไหล่กับค่าแรงแยกกันชัด และ**โครงนี้ตรงกับบิลในเฟส 6** ที่ต้องแยกค่าแรงเพื่อคำนวณหัก ณ ที่จ่าย

**"(ราคารวมภาษีมูลค่าเพิ่มแล้ว)" ต้องเขียนไว้** — ไม่งั้นลูกค้าถามว่าต้องบวก VAT อีกไหม

**ประโยคเรื่องความเสียหายเพิ่มเติม** — ป้องกันข้อพิพาทเวลางานบานปลาย ซึ่งเป็นสถานการณ์ที่ระบบรองรับด้วย `unapprove` อยู่แล้ว

**`carName` เป็นตัวช่วยใน `api.js`**
```js
export const VEHICLE_TYPE = { car: "รถยนต์", motorcycle: "มอเตอร์ไซค์" };
export const carName = (v) => [VEHICLE_TYPE[v.vehicle_type], v.brand, v.model, v.year]
  .filter(Boolean).join(" ");
```

## 11. route ที่เพิ่ม

```jsx
<Route path="/print/quote/:id" element={<Guard><PrintQuotePage /></Guard>} />
...
<Route path="jobs" element={<JobsPage />}>
  <Route path="new" element={<JobNewPage />} />
</Route>
<Route path="jobs/:id" element={<JobPage />} />
```

**ใบเสนอราคา `<Guard>` ไม่ระบุ role** — ช่างพิมพ์ใบเสนอราคาได้ (ไม่มีต้นทุนบนนั้น) ต่างจากบิลที่ต้องเป็น staff

ตั้ง `/jobs` เป็นหน้าแรกหลังล็อกอิน (`<Route index element={<Navigate to="/jobs" replace />} />`) — เป็นหน้าที่ทุก role เปิดบ่อยที่สุด

---

## เช็คว่าเฟสนี้เสร็จ

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

บนหน้าจอ
- เปิดใบงานให้ลูกค้าใหม่ → กรอกเบอร์ ชื่อ ทะเบียน จังหวัด อาการ → เปิดได้
- เปิดใบงานให้รถคันเดิมอีกใบ → **"รถคันนี้มีใบงานค้างอยู่ (JO-00001)"**
- ใส่อะไหล่เกินที่มีในคลัง → ขึ้นเตือนสีแดงตอนใส่ → กดอนุมัติ → **"สินค้า … ในคลังไม่พอ (ต้องการ 3 มี 2)"** และเปิดหน้าสต็อกดู **ของไม่หายไปไหน**
- ลดจำนวนลง → เลือกช่างหลัก → อนุมัติ → เปิดหน้าสต็อก **ของถูกตัดจาก Lot เก่าก่อน**
- ยกเลิกการอนุมัติ → กลับไปดู Lot **จำนวน Lot เท่าเดิม ของกลับเข้า Lot เดิม**
- เริ่มซ่อม → ซ่อมเสร็จ → ปุ่มหลักหายไป (เฟส 6 จะมาเติม "ออกบิลและรับเงิน")
- พิมพ์ใบเสนอราคา → ตรวจว่ามีค่าแรงแยกแถว และยอดรวมตรงกับหน้าจอ
- **ล็อกอินเป็น `mech1`** → เปิดใบงานได้ ใส่อะไหล่ได้ เลือกช่างได้ **แต่ไม่มีปุ่มอนุมัติ** ขึ้นข้อความ "รอพนักงานกดลูกค้าอนุมัติ" แทน

## git

```
git add -A && git commit -m "feat: customers, vehicles and job orders with approval"
```
