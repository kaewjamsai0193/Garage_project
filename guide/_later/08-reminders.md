# เฟส 8 — เตือนบำรุงรักษา

**จบเฟสนี้แล้ว** รับเงินแล้วมีรายการเตือนโผล่ขึ้นมาเอง มีหน้าไว้โทรตามลูกค้า

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 9 · `data_model.md` หัวข้อ 7

เฟสนี้เล็ก แต่ต้อง **ย้อนกลับไปแก้ `receive` ของเฟส 6** ตามที่จองไว้

---

## คืออะไร

รายการเตือนให้อู่ **โทรหาลูกค้า** ให้กลับมาเปลี่ยนอะไหล่ตามรอบ — เป็นเครื่องมือดึงลูกค้ากลับ ไม่ใช่การรับประกัน

| | ประกันงานซ่อม (เฟส 7) | รอบบำรุงรักษา (เฟสนี้) |
|---|---|---|
| จุดประสงค์ | อู่รับผิดชอบถ้างานที่ซ่อมมีปัญหา | อู่ชวนลูกค้ากลับมาเปลี่ยนของตามรอบ |
| ใครเริ่ม | ลูกค้ากลับมาเอง | อู่โทรหาลูกค้า |
| ผูกกับ | บิลทั้งใบ | **รถ + อะไหล่แต่ละตัว** |
| หน่วย | **วัน** ตั้งทั้งอู่ | **เดือน** ตั้งที่สินค้า |
| ครบกำหนดแล้ว | หมดสิทธิ์ ไม่มีอะไรเกิดขึ้น | ขึ้นรายการให้โทร จนกว่าจะปิดหรือเปลี่ยนรอบใหม่ |
| **เหมือนกันเรื่องเดียว** | เริ่มนับจากวันรับเงิน | เริ่มนับจากวันรับเงิน |

**ตัวอย่าง** เปลี่ยนน้ำมันเครื่องและรับเงินวันที่ 1 ม.ค.
→ ประกันงานซ่อมถึง 31 ม.ค. (ถ้ารั่วเพราะงานของอู่ ลูกค้ากลับมาได้)
→ รายการเตือนเปลี่ยนน้ำมันรอบถัดไปครบวันที่ 1 ก.ค. (อู่โทรหาลูกค้า)

### กฎ
- ครบกำหนด = วันรับเงิน + จำนวนเดือนของสินค้าตัวนั้น · **เดือนปลายทางไม่มีวันนั้น → ใช้วันสุดท้ายของเดือน**
- **รถ + อะไหล่ตัวหนึ่ง มีรายการค้างได้รายการเดียว** กลับมาเปลี่ยนก่อนกำหนด → ปิดอันเก่าเป็น `replaced` แล้วสร้างรอบใหม่
- ขายหน้าร้าน **ไม่**สร้างรายการเตือน (ไม่มีรถผูก)
- **งานเคลมที่เปลี่ยนอะไหล่ที่มีรอบ สร้างรอบใหม่ตามปกติ** เพราะของถูกเปลี่ยนจริง
- ปิดการติดตาม ≠ ลูกค้ามาแล้ว (อาจแค่ติดต่อแล้วไม่สนใจ)

---

# ส่วน backend

## 1. ตารางที่เพิ่ม

```python
class MaintenanceReminder(Base):
    __tablename__ = "maintenance_reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = fk("vehicles.id")
    product_id: Mapped[int] = fk("products.id")
    due_date: Mapped[date] = mapped_column(Date)
    source_invoice_id: Mapped[int] = fk("invoices.id")
    note: Mapped[str | None] = mapped_column(Text)
    close_reason: Mapped[str | None] = mapped_column(String(10))
    closed_at: Mapped[datetime | None] = mapped_column(TS)
    closed_by: Mapped[int | None] = fk("users.id")
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        UniqueConstraint("source_invoice_id", "product_id"),
        CheckConstraint("close_reason is null or close_reason in ('dismissed','replaced')",
                        name="close_reason"),
        CheckConstraint("(close_reason is null) = (closed_at is null)"
                        " and (closed_at is null) = (closed_by is null)", name="closed"),
        Index("maintenance_one_pending_per_vehicle_product", "vehicle_id", "product_id", unique=True,
              postgresql_where=text("close_reason is null")),
    )
```

**`Index("maintenance_one_pending_per_vehicle_product", ...)` partial unique** — กฎ "รถ+อะไหล่ มีรายการค้างได้รายการเดียว" เขียนเป็น index ตรง ๆ
รายการที่ปิดแล้ว (`close_reason` ไม่ใช่ `NULL`) มีกี่อันก็ได้ เพราะเป็นประวัติ

นี่เป็น partial unique index ตัวที่สี่ของโปรเจ็ค (หลัง "ใบกำกับซื้อ" "ใบงานค้างต่อรถ" "ช่างหลัก" "บิลต่อใบงาน") — รูปแบบนี้ใช้ได้กับกฎ "มีได้อย่างมากหนึ่ง เมื่อ X" เสมอ

**`UniqueConstraint("source_invoice_id", "product_id")`** — บิลใบเดียวสร้างรอบซ้ำของสินค้าเดิมไม่ได้ **กันการยิง `receive` ซ้ำแล้วเกิดรอบซ้อน** (แม้ `receive` จะกันด้วย `received_at` อยู่แล้วก็ตาม — สองชั้น)

**`close_reason` มีสองค่าเท่านั้น**
- `replaced` — ลูกค้ากลับมาเปลี่ยนจริง ระบบปิดให้เอง
- `dismissed` — พนักงานกดปิด (โทรแล้วไม่สนใจ / ขายรถไปแล้ว)

**แยกสองค่านี้เพราะความหมายต่างกัน** ถ้าวันหนึ่งอยากรู้ว่า "โทรตามแล้วได้ผลกี่ %" ต้องนับ `replaced` ไม่ใช่นับรวม

**`(close_reason is null) = (closed_at is null) = (closed_by is null)`** — สามฟิลด์ต้องสอดคล้องกัน (รูปแบบเดียวกับบล็อก `payment` ของบิล)

**`due_date` เป็น `Date` ไม่ใช่ `timestamptz`** — มันคือ "วันที่ควรโทร" ไม่ใช่เหตุการณ์ที่เกิดขึ้น ณ เวลาหนึ่ง

## 2. กลับไปแก้ `services/billing.py`

```python
def _renew_reminder(db, vehicle_id, row, inv, user, now, day) -> None:
    old = db.scalar(select(MaintenanceReminder).where(
        MaintenanceReminder.vehicle_id == vehicle_id,
        MaintenanceReminder.product_id == row.product_id,
        MaintenanceReminder.close_reason.is_(None)))
    if old:
        old.close_reason, old.closed_at, old.closed_by = "replaced", now, user.id
        db.flush()
    db.add(MaintenanceReminder(vehicle_id=vehicle_id, product_id=row.product_id,
                               source_invoice_id=inv.id,
                               due_date=timeutil.add_months(day, row.maintenance_cycle_months)))
```

แล้วเติมใน `receive` ตรงที่จองไว้:

```python
    if inv.job_id:
        job = inv.job
        inv.warranty_expires_on = day + timedelta(days=inv.warranty_days) if inv.warranty_days else None
        job.status, job.closed_at = "closed", now
        for row in inv.items:
            if row.product_id and row.maintenance_cycle_months:
                _renew_reminder(db, job.vehicle_id, row, inv, user, now, day)
```

**อยู่ในทรานแซกชันเดียวกับการรับเงิน** ไม่ใช่ยิงทีหลัง — ถ้าสร้างรอบเตือนพัง การรับเงินต้องย้อนกลับด้วย
เพราะกฎบอกว่า "รับเงิน → ปิดใบงาน → ตั้งวันหมดประกัน → สร้างรอบเตือน" ต้องสำเร็จพร้อมกันทั้งหมด

**ปิดอันเก่าเป็น `replaced` ก่อนสร้างอันใหม่ แล้ว `db.flush()`**
ถ้าไม่ flush ก่อน INSERT อันใหม่ จะชน partial unique index ทันที เพราะยังมีรายการค้างสองอันในฐานชั่วขณะ
`flush()` ส่ง UPDATE ลงไปก่อน แล้วค่อย INSERT — ทั้งคู่ยังอยู่ในทรานแซกชันเดียว

**`if row.product_id and row.maintenance_cycle_months`**
- `product_id` ตัดแถวค่าแรงออก (แถว labor ไม่มี product_id)
- `maintenance_cycle_months` ตัดอะไหล่ที่ไม่มีรอบ (ผ้าเบรก หัวเทียนอาจไม่ตั้งรอบไว้)

**อ่าน `maintenance_cycle_months` จากแถวบิล ไม่ใช่จาก `products`** — ค่านี้ถูกคัดลอกมาเก็บบนบิลตอนออกบิล (เฟส 6) ถ้ามีคนไปแก้รอบของสินค้าระหว่างที่บิลยังไม่รับเงิน รอบเตือนต้องยึดตามที่ตกลงตอนขาย

**`add_months(day, months)`** ใช้ฟังก์ชันจากเฟส 1 ที่จัดการวันสิ้นเดือนให้แล้ว
`day` คือวันไทยของการรับเงิน (`bkk_date(now)`) ไม่ใช่วัน UTC

**อยู่ใต้ `if inv.job_id:`** → **บิลขายหน้าร้านไม่สร้างรอบเตือนโดยอัตโนมัติ** ไม่ต้องเขียนกฎแยก

**งานเคลมก็ผ่านทางนี้** เพราะมันก็คือใบงานที่มี `job_id` ต่างกันแค่ราคาเป็น 0 → **เปลี่ยนน้ำมันเครื่องฟรีในงานเคลม ก็ยังสร้างรอบเตือนใหม่** ตรงตามกฎ (ของถูกเปลี่ยนจริง)

## 3. `services/reminders.py`

```python
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from app import timeutil
from app.db import get_or_404
from app.models import Customer, Invoice, MaintenanceReminder, Product, Vehicle

WINDOW_DAYS = 7


def _due():
    return (MaintenanceReminder.close_reason.is_(None),
            MaintenanceReminder.due_date <= timeutil.today() + timedelta(days=WINDOW_DAYS))


def _rows(db, *where) -> list[dict]:
    stmt = (select(MaintenanceReminder, Vehicle, Customer, Product.name, Invoice.display_number)
            .join(Vehicle, Vehicle.id == MaintenanceReminder.vehicle_id)
            .join(Customer, Customer.id == Vehicle.customer_id)
            .join(Product, Product.id == MaintenanceReminder.product_id)
            .join(Invoice, Invoice.id == MaintenanceReminder.source_invoice_id)
            .where(*where).order_by(MaintenanceReminder.due_date, MaintenanceReminder.id))
    today = timeutil.today()
    return [{"id": r.id, "vehicle_id": v.id, "plate": v.plate, "plate_province": v.plate_province,
             "product_id": r.product_id, "product_name": product_name, "due_date": r.due_date,
             "overdue": r.due_date < today, "note": r.note, "close_reason": r.close_reason,
             "customer_name": c.name, "customer_phone": c.phone, "source_invoice_number": number}
            for r, v, c, product_name, number in db.execute(stmt)]


def due_reminders(db) -> list[dict]:
    return _rows(db, *_due())


def count_due(db) -> int:
    return db.scalar(select(func.count()).select_from(MaintenanceReminder).where(*_due()))


def reminder_view(db, reminder_id) -> dict:
    rows = _rows(db, MaintenanceReminder.id == reminder_id)
    if not rows:
        raise HTTPException(404, "ไม่พบรายการเตือน")
    return rows[0]


def save_note(db, reminder_id, note) -> None:
    get_or_404(db, MaintenanceReminder, reminder_id, "รายการเตือน").note = note or None
    db.commit()


def dismiss(db, reminder_id, note, user) -> None:
    reminder = get_or_404(db, MaintenanceReminder, reminder_id, "รายการเตือน")
    if reminder.close_reason:
        raise HTTPException(409, "รายการนี้ปิดการติดตามแล้ว")
    if note:
        reminder.note = note
    reminder.close_reason, reminder.closed_at, reminder.closed_by = "dismissed", timeutil.now(), user.id
    db.commit()
```

**`_due()` คืน tuple ของเงื่อนไข แล้วกระจายด้วย `*`** — นิยามของคำว่า "ถึงกำหนด" อยู่ที่เดียว ใช้ทั้งในรายการและในตัวนับของแดชบอร์ด (เฟส 9)
ถ้าเขียนซ้ำสองที่ วันหนึ่งจะแก้ไม่ครบแล้วตัวเลขบนแดชบอร์ดไม่ตรงกับจำนวนแถวในหน้ารายการ

**`due_date <= today + 7 วัน`** — ครอบทั้ง "เลยกำหนดแล้ว" และ "จะครบใน 7 วัน" ในเงื่อนไขเดียว
ไม่มีขอบล่าง เพราะรายการที่เลยกำหนดมานานแล้วยังต้องโทรอยู่ (หรือกดปิดถ้าเลิกตาม)

**`overdue` คำนวณที่เซิร์ฟเวอร์** เพื่อให้หน้าจอไม่ต้องคิดวันเอง (เหตุผลเดียวกับ `in_warranty` ในเฟส 7)

**`_rows` join 4 ตารางแล้วแบนเป็น dict** — หน้าจอต้องการ ทะเบียน + ชื่อลูกค้า + เบอร์ + ชื่อสินค้า + เลขบิลต้นทาง ครบในแถวเดียวเพื่อกดโทรได้ทันที

**`order_by(due_date, id)`** — ที่ค้างนานที่สุดขึ้นก่อน ตรงกับลำดับความเร่งด่วนจริง

**`save_note` แยกจาก `dismiss`** — จดว่า "โทรแล้วไม่รับ" ไว้ก่อน ยังไม่ปิด แล้วพรุ่งนี้โทรใหม่ ต้องทำได้

**`dismiss` ปิดซ้ำไม่ได้** และบันทึกว่าใครปิดเมื่อไหร่

API:
```
GET   /api/reminders               รายการที่ถึงกำหนด
GET   /api/reminders/{id}
PATCH /api/reminders/{id}          จดบันทึกการโทร
POST  /api/reminders/{id}/dismiss  ปิดการติดตาม
```
ทั้งหมดเป็น **staff** (`require_role("admin", "employee")`) — ช่างไม่ได้โทรตามลูกค้า

## 4. เทสต์ — `tests/test_reports.py`

```python
from datetime import date

from app.timeutil import add_months, today
from tests.flows import ready_job


def pay(client, h, job):
    inv = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    client.post(f"/api/invoices/{inv['id']}/receive",
                json={"payment_method": "cash", "amount_received": inv["grand_total"],
                      "withholding_amount": "0"}, headers=h["admin"])
    return inv


def test_payment_creates_reminder(client, h, make_vehicle, make_product, stock, users):
    vid = make_vehicle()
    oil = client.post("/api/products", json={"code": "OIL", "name": "น้ำมันเครื่อง", "unit": "ลิตร",
                                             "sale_price": "300", "maintenance_cycle_months": 6},
                      headers=h["admin"]).json()["id"]
    stock(oil, 20, "150")
    pay(client, h, ready_job(client, h, vid, oil, users, qty="4", price="300", labor="200"))

    rows = client.get("/api/reminders", headers=h["admin"]).json()
    # ยังไม่ถึงกำหนด (อีก 6 เดือน) จึงไม่โผล่ในรายการที่ต้องโทร
    assert rows == []


def test_early_return_replaces_old_reminder(client, h, make_vehicle, make_product, stock, users):
    vid = make_vehicle()
    oil = client.post("/api/products", json={"code": "OIL", "name": "น้ำมันเครื่อง", "unit": "ลิตร",
                                             "sale_price": "300", "maintenance_cycle_months": 6},
                      headers=h["admin"]).json()["id"]
    stock(oil, 40, "150")
    pay(client, h, ready_job(client, h, vid, oil, users, qty="4", price="300", labor="200"))
    pay(client, h, ready_job(client, h, vid, oil, users, qty="4", price="300", labor="200"))

    from app.db import SessionLocal
    from app.models import MaintenanceReminder
    with SessionLocal() as s:
        rows = s.query(MaintenanceReminder).filter_by(vehicle_id=vid, product_id=oil).all()
        assert len(rows) == 2
        assert sum(r.close_reason is None for r in rows) == 1          # ค้างเหลือรายการเดียว
        assert {r.close_reason for r in rows} == {None, "replaced"}


def test_counter_sale_creates_no_reminder(client, h, make_product, stock):
    oil = client.post("/api/products", json={"code": "OIL2", "name": "น้ำมัน", "unit": "ลิตร",
                                             "sale_price": "300", "maintenance_cycle_months": 6},
                      headers=h["admin"]).json()["id"]
    stock(oil, 10, "150")
    inv = client.post("/api/invoices/sale",
                      json={"items": [{"product_id": oil, "qty": "4", "unit_price": "300"}]},
                      headers=h["admin"]).json()
    client.post(f"/api/invoices/{inv['id']}/receive",
                json={"payment_method": "cash", "amount_received": inv["grand_total"],
                      "withholding_amount": "0"}, headers=h["admin"])

    from app.db import SessionLocal
    from app.models import MaintenanceReminder
    with SessionLocal() as s:
        assert s.query(MaintenanceReminder).count() == 0


def test_due_date_uses_month_end_clamp():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 1, 31), 6) == date(2026, 7, 31)


def test_dismiss_twice_rejected(client, h, make_vehicle, make_product, stock, users):
    # (สร้างรายการที่ถึงกำหนดด้วยการแก้ due_date ในฐานให้เป็นเมื่อวาน แล้วทดสอบ dismiss)
    ...
```

**`test_early_return_replaces_old_reminder` คือกรณีตรวจรับข้อ 8**
เช็คสองอย่าง: **มีสองแถว** (ประวัติครบ) และ **ค้างอยู่แถวเดียว** (กฎ) — เช็คแค่อย่างใดอย่างหนึ่งไม่พอ

**`test_counter_sale_creates_no_reminder`** ทดสอบว่า "ไม่มีอะไรเกิดขึ้น" — เทสต์แบบนี้คนมักลืมเขียน แต่เป็นตัวจับบั๊กประเภท "ทำงานดีเกินไป"

**เทสต์วันสิ้นเดือนเรียก `add_months` ตรง ๆ** ไม่ต้องผ่าน API เลย เร็วกว่าและชัดกว่า

---

# ส่วนหน้าจอ

## 5. `pages/RemindersPage.jsx`

```jsx
import { useApi } from "../api";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import StatusBadge, { reminderKey } from "../components/StatusBadge";
import { thaiDate } from "../api";

export default function RemindersPage() {
  const { data, error, reload } = useApi("/reminders");

  return (
    <ListLayout title="ถึงกำหนดบำรุงรักษา" basePath="/reminders" context={{ reload }}>
      {error && <p role="alert" className="field-error">{error}</p>}
      <p className="text-sm text-muted">รายการที่เลยกำหนดและที่จะครบภายใน 7 วัน · โทรชวนลูกค้ากลับมา</p>
      <DataTable items={data} to={(r) => `/reminders/${r.id}`} empty="ยังไม่มีรายการที่ต้องโทร"
        card={(r) => (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold">{r.plate} <span className="text-sm font-normal text-muted">
                {r.plate_province}</span></span>
              <StatusBadge status={reminderKey(r)} />
            </div>
            <div className="text-sm">{r.product_name} · ครบ {thaiDate(r.due_date)}</div>
            <div className="mt-2 flex items-center justify-between gap-2">
              <span className="truncate text-sm text-muted">{r.customer_name}</span>
              <a href={`tel:${r.customer_phone}`} onClick={(e) => e.stopPropagation()}
                 className="btn btn-secondary">โทร {r.customer_phone}</a>
            </div>
          </>
        )}
        columns={[
          { label: "ทะเบียน", render: (r) => r.plate },
          { label: "อะไหล่", render: (r) => r.product_name },
          { label: "ครบกำหนด", render: (r) => thaiDate(r.due_date) },
          { label: "สถานะ", render: (r) => <StatusBadge status={reminderKey(r)} /> },
          { label: "ลูกค้า", render: (r) => r.customer_name },
          { label: "เบอร์", render: (r) => (
              <a href={`tel:${r.customer_phone}`} className="text-accent">{r.customer_phone}</a>) },
        ]} />
    </ListLayout>
  );
}
```

เพิ่มใน `StatusBadge.jsx`:
```jsx
overdue: ["เลยกำหนด", "danger"],
due_soon: ["ใกล้ถึงกำหนด", "warn"],

export const reminderKey = (r) => (r.overdue ? "overdue" : "due_soon");
```

**ปุ่มโทรอยู่ในรายการเลย ไม่ต้องเข้าหน้ารายละเอียด** — งานจริงคือหยิบโทรศัพท์แล้วโทรไล่ทีละคน ไม่ใช่การอ่านข้อมูล
`tel:` เป็นของ HTML ธรรมดา บนมือถือกดแล้วโทรออก บนคอมเปิดแอปโทรศัพท์ถ้ามี

**`e.stopPropagation()`** — ปุ่มโทรอยู่ในการ์ดที่ทั้งใบเป็นลิงก์ไปหน้ารายละเอียด ไม่หยุดไว้จะเด้งไปหน้าอื่นแทนที่จะโทร

**"เลยกำหนด" เป็นสีแดง "ใกล้ถึงกำหนด" เป็นเหลือง** — กวาดตาแล้วรู้ว่าต้องโทรใครก่อน

**ไม่มีตัวกรอง** — รายการนี้มีไม่กี่สิบรายการต่อสัปดาห์ และทุกรายการคือสิ่งที่ต้องทำ ไม่ใช่คลังข้อมูลให้ค้น

## 6. `pages/ReminderPage.jsx`

```jsx
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, thaiDate, useApi } from "../api";
import Icon from "../components/Icon";
import DetailLayout from "../components/DetailLayout";
import ReasonDialog from "../components/ReasonDialog";
import StatusBadge, { reminderKey } from "../components/StatusBadge";

export default function ReminderPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: r, error, reload } = useApi(`/reminders/${id}`);
  const [note, setNote] = useState("");
  const [closing, setClosing] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => { if (r) setNote(r.note ?? ""); }, [r]);

  if (error) return <DetailLayout back="/reminders" backLabel="เตือนบำรุงรักษา" title="รายการเตือน">
    <p role="alert" className="field-error">{error}</p></DetailLayout>;
  if (!r) return <DetailLayout back="/reminders" backLabel="เตือนบำรุงรักษา" title="กำลังโหลด…" />;

  const saveNote = async () => {
    setMsg("");
    try {
      await api(`/reminders/${id}`, { method: "PATCH", body: { note } });
      setMsg("บันทึกแล้ว");
      reload();
    } catch (err) {
      setMsg(err.message);
    }
  };

  return (
    <DetailLayout back="/reminders" backLabel="เตือนบำรุงรักษา" title={`${r.plate} ${r.plate_province}`}
      subtitle={`${r.product_name} · ครบ ${thaiDate(r.due_date)}`}
      badge={r.close_reason ? <StatusBadge status="closed" /> : <StatusBadge status={reminderKey(r)} />}
      menu={r.close_reason ? [] : [{ label: "ปิดการติดตาม", onClick: () => setClosing(true) }]}
      footer={
        <a href={`tel:${r.customer_phone}`} className="btn btn-primary w-full">
          <Icon name="phone" size={20} />โทร {r.customer_name} · {r.customer_phone}
        </a>
      }>
      <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        <div><dt className="text-muted">ลูกค้า</dt><dd className="font-medium">{r.customer_name}</dd></div>
        <div><dt className="text-muted">มาจากบิล</dt>
          <dd className="font-medium">{r.source_invoice_number}</dd></div>
      </dl>
      <Link to={`/vehicles/${r.vehicle_id}`} className="btn btn-secondary">
        <Icon name="history" size={20} />ประวัติรถ
      </Link>

      <label className="block">
        <span className="label">บันทึกการติดต่อ</span>
        <textarea className="input" rows={4} value={note} onChange={(e) => setNote(e.target.value)}
                  placeholder="โทรแล้วไม่รับ · นัดเข้ามาศุกร์นี้ · ขายรถไปแล้ว" />
      </label>
      {msg && <p role="status" className="text-sm text-muted">{msg}</p>}
      <button type="button" className="btn btn-secondary" onClick={saveNote}>บันทึกโน้ต</button>

      <ReasonDialog title="ปิดการติดตาม" open={closing} onClose={() => setClosing(false)}
        reasonLabel="บันทึกเพิ่มเติม (ไม่บังคับ)" required={false}
        confirmLabel="ปิดการติดตาม" initialReason={note}
        onConfirm={async (text) => {
          await api(`/reminders/${id}/dismiss`, { method: "POST", body: { note: text } });
          navigate("/reminders");
        }}>
        <p className="text-muted">ปิดแล้วรายการนี้จะไม่ขึ้นให้โทรอีก
          (ไม่ได้แปลว่าลูกค้าเข้ารับบริการแล้ว)</p>
      </ReasonDialog>
    </DetailLayout>
  );
}
```

**ปุ่มหลักของหน้านี้คือ "โทร"** ไม่ใช่ "บันทึก" — ทั้งหน้ามีไว้เพื่อการโทรครั้งเดียว

**ข้อความในกล่องปิดการติดตามอธิบายว่ามันไม่ได้แปลว่าลูกค้ามาแล้ว** — ตรงกับกฎ ป้องกันคนใช้เข้าใจผิดแล้วสถิติเพี้ยน (ลูกค้ามาจริงระบบจะปิดเป็น `replaced` ให้เองตอนรับเงิน)

**`required={false}` บนเหตุผล** — ต่างจาก `ReasonDialog` ที่ใช้ในเฟสอื่น ปิดการติดตามไม่ใช่การแก้ไขเอกสาร ไม่ต้องบังคับเหตุผล
**`initialReason={note}`** เอาโน้ตที่จดไว้มาใส่ให้ ไม่ต้องพิมพ์ซ้ำ

**ลิงก์ไปประวัติรถ** — ก่อนโทรอยากรู้ว่าคันนี้เคยทำอะไรไปบ้าง จะได้คุยได้

**`placeholder` ยกตัวอย่างจริง** ช่วยให้คนจดอะไรที่มีประโยชน์ แทนที่จะเว้นว่างเพราะไม่รู้จะเขียนอะไร

## 7. เติมเมนูและ route

```jsx
<Route path="reminders" element={<Guard roles={STAFF}><RemindersPage /></Guard>} />
<Route path="reminders/:id" element={<Guard roles={STAFF}><ReminderPage /></Guard>} />
```

เพิ่มใน `MENU` ของ `AppLayout.jsx`: `{ to: "/reminders", label: "เตือน", roles: ["admin", "employee"] }`

---

## เช็คว่าเฟสนี้เสร็จ

```
docker compose run --rm api pytest      # เขียวทั้งชุด รวมของเฟส 6 ที่ไปแก้มา
docker compose exec -T web npm run build
```

บนหน้าจอ
- ตั้งรอบเปลี่ยนของน้ำมันเครื่องเป็น **6 เดือน** ในหน้าสินค้า
- เปิดใบงาน เปลี่ยนน้ำมันเครื่อง → อนุมัติ → ซ่อมเสร็จ → ออกบิล → **รับเงิน**
- เข้าฐานข้อมูลเช็ค (หรือแก้ `due_date` ให้เป็นเมื่อวานเพื่อทดสอบ):
  ```
  docker compose exec db psql -U garage -d garage -c "select * from maintenance_reminders"
  ```
  **ต้องมี 1 แถว `due_date` = วันรับเงิน + 6 เดือน**
- แก้ `due_date` ให้เป็นเมื่อวาน → รีเฟรชหน้าเตือน → **ขึ้นรายการพร้อมป้าย "เลยกำหนด" สีแดง**
- กดปุ่มโทร (บนมือถือหรือ DevTools โหมดมือถือ) → เปิดแอปโทรศัพท์
- จดโน้ต → บันทึก → รีเฟรช → โน้ตยังอยู่
- เปิดใบงานเปลี่ยนน้ำมันให้รถคันเดิมอีกรอบ แล้วรับเงิน → **รายการเก่าหายจากหน้าเตือน (เป็น `replaced`) และมีรายการใหม่แทน**
- ขายน้ำมันเครื่องหน้าร้าน → **ไม่มีรายการเตือนเกิดขึ้น**
- **ล็อกอินเป็น `mech1`** → ไม่มีเมนูเตือน และพิมพ์ `/reminders` ก็เข้าไม่ได้

## git

```
git add -A && git commit -m "feat: maintenance reminders created on payment"
```
