# เฟส 7 — ประวัติรถ ประกัน และงานเคลม

**จบเฟสนี้แล้ว** ค้นรถแล้วเห็นประวัติซ่อมทั้งหมด งานที่ยังอยู่ในประกันมีปุ่มเปิดงานเคลมฟรี

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 7, 8 · `data_model.md` หัวข้อ "ประวัติรถ"

**ไม่มีตารางใหม่** ประวัติประกอบจากใบงาน + รายการ + บิล ที่มีอยู่แล้ว ส่วนงานเคลมเป็นใบงานชนิดหนึ่ง (คอลัมน์เตรียมไว้ตั้งแต่เฟส 5)

---

## เคลมคืออะไรกันแน่

**รถกลับมาเพราะปัญหาจากงานที่อู่ซ่อมให้ ภายในช่วงประกัน อู่แก้ให้ฟรี**

ไม่ใช่ประกันสินค้าที่ซื้อหน้าร้าน ไม่ใช่ประกันภัยรถยนต์ และไม่ใช่รอบบำรุงรักษา (เฟส 8)

| | ประกันงานซ่อม (เฟสนี้) | รอบบำรุงรักษา (เฟส 8) |
|---|---|---|
| ผูกกับ | บิลงานซ่อมทั้งใบ | รถ + อะไหล่แต่ละตัว |
| หน่วย | **วัน** ตั้งที่หน้าตั้งค่า (ทั้งอู่) | **เดือน** ตั้งที่สินค้าแต่ละตัว |
| ใครเริ่ม | ลูกค้ากลับมาเอง | อู่โทรหาลูกค้า |
| จุดประสงค์ | อู่รับผิดชอบงานที่ซ่อมไป | ชวนลูกค้ากลับมาเปลี่ยนของตามรอบ |

### กฎของงานเคลม

- เปิดจากบิลงานซ่อมเดิม + กรอกอาการที่กลับมา (บังคับ) · **ทุก role เปิดได้**
- **ราคาอะไหล่และค่าแรงบังคับเป็น 0** แต่ตัด Lot จริงและบันทึกต้นทุนจริง → กำไรติดลบเท่าต้นทุน
- ปิดด้วยบิลยอด 0 (เลขชุดเดียวกับบิลปกติ ใส่ส่วนลดไม่ได้) แล้วกด "ยืนยันส่งมอบ"
- **ไม่ตั้งวันหมดประกันใหม่** ประกันยังนับจากบิลเดิม เคลมซ้ำได้จนกว่าจะหมด
- **ไม่นับเป็นผลงานช่าง** (เฟส 9)
- หนึ่งใบงานเป็นเคลมหรืองานคิดเงิน **อย่างใดอย่างหนึ่ง** ถ้าลูกค้าให้ทำงานคิดเงินด้วย ให้เปิดใบงานแยกหลังปิดเคลม
- บิลต้นทางและอาการที่กลับมา **แก้ไม่ได้หลังเปิดงาน** เลือกผิดให้ยกเลิกใบงาน (ก่อนอนุมัติ) แล้วเปิดใหม่

---

# ส่วน backend

## 1. `check_claim` — กฎทั้งหมดของการเคลมอยู่ในฟังก์ชันเดียว

เพิ่มใน `services/jobs.py`:

```python
def check_claim(db, invoice_id, vehicle_id, opened_at) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    reason = None
    if inv is None or inv.job_id is None:
        reason = "ไม่ใช่บิลงานซ่อม"
    elif inv.job.vehicle_id != vehicle_id:
        reason = "เป็นบิลของรถคันอื่น"
    elif inv.status != "issued":
        reason = "บิลถูกยกเลิกแล้ว"
    elif inv.received_at is None:
        reason = "บิลยังไม่รับเงิน"
    elif inv.warranty_expires_on is None:
        reason = "บิลนี้ไม่มีประกันงานซ่อม"
    elif inv.received_at > opened_at or timeutil.bkk_date(opened_at) > inv.warranty_expires_on:
        reason = "หมดประกันแล้ว"
    if reason:
        raise HTTPException(409, f"บิลนี้ใช้เปิดงานเคลมไม่ได้: {reason}")
    return inv
```

**หกเงื่อนไข ตรงกับกรณีตรวจรับข้อ 17 ทีละข้อ**

| เช็ค | กันอะไร |
|---|---|
| `job_id is None` | บิลขายหน้าร้านเอามาเคลมไม่ได้ (ไม่มีรถ ไม่มีงานซ่อม) |
| `job.vehicle_id != vehicle_id` | เอาบิลของรถคันอื่นมาเคลมกับรถคันนี้ไม่ได้ |
| `status != "issued"` | บิลที่ยกเลิกแล้วไม่มีผล |
| `received_at is None` | ยังไม่จ่ายเงิน = ยังไม่เริ่มนับประกัน |
| `warranty_expires_on is None` | บิลงานเคลมเอง (ไม่ตั้งประกันใหม่) และบิลที่ออกตอนตั้งค่าประกัน 0 วัน |
| วันหมดอายุ | หมดประกันแล้ว |

**`bkk_date(opened_at) > warranty_expires_on`** ใช้ `>` ไม่ใช่ `>=`
เปิดงาน**ตรงวันหมดประกันยังได้** วันถัดไปไม่ได้ — นี่คือข้อความตรงตัวจากข้อกำหนด และเป็นเคสที่ต้องมีเทสต์เพราะพลาดง่ายมาก

**`inv.received_at > opened_at`** กันการเปิดงานเคลม "ย้อนหลัง" ก่อนบิลต้นทางจะถูกรับเงินด้วยซ้ำ

**ฟังก์ชันนี้ถูกเรียกสองครั้ง** — ตอนเปิดงาน และ**ตอนอนุมัติ** ทั้งสองครั้งส่ง `job.opened_at` ตัวเดียวกัน:

```python
# ใน open_job
if data.warranty_source_invoice_id:
    check_claim(db, data.warranty_source_invoice_id, vehicle.id, opened_at)

# ใน approve
if job.warranty_source_invoice_id:
    check_claim(db, job.warranty_source_invoice_id, job.vehicle_id, job.opened_at)
```

**ทำไมเช็คตอนอนุมัติด้วย และทำไมใช้วันเปิดงานไม่ใช่วันอนุมัติ**

ลูกค้าเอารถเข้าวันสุดท้ายของประกัน แต่ช่างคุยเสร็จแล้วกดอนุมัติวันรุ่งขึ้น
ถ้าเช็คด้วยวันอนุมัติ = ลูกค้าเสียสิทธิ์เพราะความช้าของอู่ ซึ่งไม่ยุติธรรม
**สิทธิ์ตัดสินที่วันที่รถเข้ามา** ส่วนการเช็คซ้ำตอนอนุมัติมีไว้กันกรณีบิลต้นทางถูกยกเลิกไปในระหว่างนั้น

## 2. `claimable_invoices` — บิลที่ยังเคลมได้ของรถคันนี้

เพิ่มใน `services/customers.py`:

```python
def claimable_invoices(db, vehicle_id: int) -> list[Invoice]:
    return db.scalars(
        select(Invoice).join(JobOrder, JobOrder.id == Invoice.job_id)
        .where(JobOrder.vehicle_id == vehicle_id, Invoice.status == "issued",
               Invoice.received_at.is_not(None), Invoice.warranty_expires_on >= timeutil.today())
        .order_by(Invoice.id.desc())
    ).all()
```

**เงื่อนไขเดียวกับ `check_claim` แต่เขียนเป็น query** — ให้หน้าจอเอาไปทำ dropdown ผู้ใช้จึงเลือกได้เฉพาะบิลที่ใช้ได้จริง ไม่ต้องลองผิดลองถูก
(`check_claim` ยังตรวจจริงตอนบันทึกอยู่ดี — หน้าจอเชื่อไม่ได้ และรายการอาจค้างจนหมดอายุระหว่างที่เปิดหน้าไว้)

**`warranty_expires_on >= today()`** — บิลที่ไม่มีวันหมดประกัน (`NULL`) ถูกตัดออกอัตโนมัติ เพราะ `NULL >= x` ได้ `NULL` ซึ่งไม่ผ่านเงื่อนไข

API: `GET /api/vehicles/{id}/claimable-invoices` → `ClaimableInvoiceOut` (`id`, `display_number`, `warranty_expires_on`)

## 3. ราคา 0 บังคับที่ service

`save_items` (เขียนไว้แล้วในเฟส 5) มีบรรทัดนี้:

```python
claim = job.warranty_source_invoice_id is not None
price = Decimal(0) if claim else (item.unit_price if item.unit_price is not None else p.sale_price)
...
job.labor_total = Decimal(0) if claim else data.labor_total
```

**บังคับที่เซิร์ฟเวอร์ ไม่ใช่แค่ล็อกช่องบนหน้าจอ** — ยิง API ตรง ๆ ใส่ราคามาก็โดนล้างเป็น 0

**แต่ยังตัดสต็อกจริงและเก็บต้นทุนจริง** — ของที่ใช้ไปในงานเคลมคือของจริงที่หายจากคลังจริง และเป็นต้นทุนที่อู่ต้องแบก
ผลคือบิลเคลมมี `grand_total = 0` แต่ `cost_total > 0` → **`gross_profit` ติดลบ** ตรงตามความจริง

และใน `issue_job_invoice` (เฟส 6):
```python
if claim and data.discount_amount > 0:
    raise HTTPException(409, "งานเคลมใส่ส่วนลดไม่ได้")
```
ยอดเป็น 0 อยู่แล้ว ลดอะไรไม่ได้ และถ้าปล่อยผ่านจะได้ยอดติดลบ

## 4. `vehicle_history` — ประกอบประวัติรถ

เพิ่มไฟล์ `services/reports.py`:

```python
def vehicle_history(db, vehicle_id) -> dict:
    vehicle = get_or_404(db, Vehicle, vehicle_id, "รถ")
    jobs = db.scalars(select(JobOrder).where(JobOrder.vehicle_id == vehicle.id)
                      .options(selectinload(JobOrder.items), selectinload(JobOrder.vehicle),
                               selectinload(JobOrder.customer),
                               selectinload(JobOrder.mechanics).selectinload(JobMechanic.user))
                      .order_by(JobOrder.opened_at.desc(), JobOrder.id.desc())).all()
    source_ids = [j.warranty_source_invoice_id for j in jobs if j.warranty_source_invoice_id]
    sources = dict(db.execute(select(Invoice.id, Invoice.display_number)
                              .where(Invoice.id.in_(source_ids))).all())
    today = timeutil.today()
    rows = []
    for job, view in zip(jobs, job_views(db, jobs)):
        expires = view["warranty_expires_on"]
        rows.append({
            **view, "mileage": job.mileage, "symptom": job.symptom, "claim_reason": job.claim_reason,
            "warranty_source_invoice_id": job.warranty_source_invoice_id,
            "warranty_source_number": sources.get(job.warranty_source_invoice_id),
            "labor_total": job.labor_total,
            "items": [{"description": i.description, "unit": i.unit, "qty": i.qty,
                       "unit_price": i.unit_price, "line_total": i.line_total} for i in job.items],
            "mechanics": [{"user_id": m.user_id, "full_name": m.user.full_name,
                           "is_primary": m.is_primary} for m in view["mechanics_sorted"]],
            "in_warranty": bool(expires and expires >= today),
        })
    visits = [j for j in jobs if j.status != "cancelled"]
    return {"vehicle": VehicleBrief.model_validate(vehicle),
            "customer": CustomerOut.model_validate(vehicle.customer),
            "visits": len(visits), "last_visit_at": visits[0].opened_at if visits else None,
            "last_mileage": visits[0].mileage if visits else None, "jobs": rows}
```

**ใช้ `job_views` ตัวเดียวกับหน้ารายการใบงาน** — ประวัติรถไม่ได้สร้างข้อมูลใหม่ แค่จัดกลุ่มใบงานของรถคันเดียวแล้วเติมรายละเอียด
ใช้ซ้ำแบบนี้แปลว่า **เลขในประวัติรถกับในหน้าใบงานตรงกันเสมอ** ไม่มีทางคำนวณคนละแบบ

**`zip(jobs, job_views(db, jobs))`** — `job_views` รับ list และคืน list เรียงตรงกัน จับคู่กลับได้

**`sources` โหลดเลขบิลต้นทางทีเดียว** ไม่ยิงต่อใบงานเคลม (N+1)

**`in_warranty` คำนวณที่เซิร์ฟเวอร์ ไม่ให้หน้าจอคิด** — หน้าจอใช้เวลาของเครื่องผู้ใช้ซึ่งอาจตั้งผิด และต้องแปลงโซนเวลาเอง คิดที่เดียวด้วยวันไทยจบ

**`visits` ไม่นับใบงานที่ยกเลิก** — "เข้ารับบริการ 5 ครั้ง" ต้องหมายถึงครั้งที่เข้ามาจริง ส่วนใบที่ยกเลิกยังแสดงในไทม์ไลน์เพื่อความครบถ้วน

**`last_mileage` เอาจากใบงานล่าสุด** — หน้าเปิดใบงาน (เฟส 5) แสดงเลขนี้ให้เทียบตอนกรอกไมล์ใหม่

API: `GET /api/vehicles/{id}/history` — **ทุก role เรียกได้** แต่ `invoice_id` ที่ส่งมาช่างกดเข้าไม่ได้อยู่ดี (endpoint บิลเป็น staff)

## 5. เทสต์ — `tests/test_claims.py`

```python
from datetime import date, timedelta

from sqlalchemy import update
from app.db import SessionLocal
from app.models import Invoice
from tests.flows import ready_job


def paid_job_invoice(client, h, vid, pid, users, **kw):
    """เปิด → ซ่อม → ออกบิล → รับเงิน · คืน dict ของบิลที่รับเงินแล้ว"""
    job = ready_job(client, h, vid, pid, users, **kw)
    inv = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    client.post(f"/api/invoices/{inv['id']}/receive",
                json={"payment_method": "cash", "amount_received": inv["grand_total"],
                      "withholding_amount": "0"}, headers=h["admin"])
    return client.get(f"/api/invoices/{inv['id']}", headers=h["admin"]).json()


def set_expiry(invoice_id, day):
    with SessionLocal() as s:
        s.execute(update(Invoice).where(Invoice.id == invoice_id).values(warranty_expires_on=day))
        s.commit()


def test_claim_job_is_free_but_costs_real_money(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 10, "80")
    src = paid_job_invoice(client, h, vid, pid, users, qty="1", price="1000", labor="70")

    job = client.post("/api/jobs", json={
        "vehicle_id": vid, "mileage": 51000, "symptom": "เบรกมีเสียงอีก",
        "warranty_source_invoice_id": src["id"], "claim_reason": "เสียงเดิมกลับมา",
    }, headers=h["mechanic"]).json()                     # ช่างเปิดงานเคลมได้

    # ใส่ราคามาก็โดนล้างเป็น 0
    j = client.put(f"/api/jobs/{job['id']}/items",
                   json={"labor_total": "500",
                         "items": [{"product_id": pid, "qty": "1", "unit_price": "999"}]},
                   headers=h["admin"]).json()
    assert j["items"][0]["unit_price"] == "0.0000"
    assert j["labor_total"] == "0.00" and j["total"] == "0.00"

    client.put(f"/api/jobs/{job['id']}/mechanics",
               json={"mechanics": [{"user_id": users["mechanic"].id, "is_primary": True}]},
               headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"])
    # ตัดสต็อกจริง
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert lots[0]["qty_remaining"] == "8.000"           # 10 − 1 (บิลแรก) − 1 (เคลม)

    client.post(f"/api/jobs/{job['id']}/start", headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/finish", headers=h["admin"])
    inv = client.post("/api/invoices/job", json={"job_id": job["id"]}, headers=h["admin"]).json()
    assert inv["grand_total"] == "0.00"
    assert inv["cost_total"] == "80.00"
    assert inv["gross_profit"] == "-80.00"               # กำไรติดลบเท่าต้นทุน
    assert inv["suggested_withholding"] == "0.00"

    # ยืนยันส่งมอบ
    client.post(f"/api/invoices/{inv['id']}/receive",
                json={"payment_method": "zero_total", "amount_received": "0",
                      "withholding_amount": "0"}, headers=h["admin"])
    assert client.get(f"/api/jobs/{job['id']}", headers=h["admin"]).json()["status"] == "closed"
    # ไม่ตั้งประกันใหม่
    assert client.get(f"/api/invoices/{inv['id']}",
                      headers=h["admin"]).json()["warranty_expires_on"] is None


def test_claim_source_must_be_valid(client, h, make_vehicle, make_product, stock, users):
    vid, other, pid = make_vehicle(), make_vehicle(plate="ขค5678", phone="0822222222"), make_product()
    stock(pid, 20, "80")
    src = paid_job_invoice(client, h, vid, pid, users)

    def open_claim(vehicle_id, invoice_id, reason="อาการเดิม"):
        return client.post("/api/jobs", json={
            "vehicle_id": vehicle_id, "mileage": 52000, "symptom": "x",
            "warranty_source_invoice_id": invoice_id, "claim_reason": reason}, headers=h["admin"])

    # บิลของรถคันอื่น
    assert open_claim(other, src["id"]).status_code == 409
    # ไม่กรอกอาการ
    assert open_claim(vid, src["id"], reason="").status_code == 422

    # บิลขายหน้าร้าน
    sale = client.post("/api/invoices/sale",
                       json={"items": [{"product_id": pid, "qty": "1", "unit_price": "600"}]},
                       headers=h["admin"]).json()
    assert open_claim(vid, sale["id"]).status_code == 409

    # บิลที่ยังไม่รับเงิน
    job2 = ready_job(client, h, other, pid, users)
    unpaid = client.post("/api/invoices/job", json={"job_id": job2}, headers=h["admin"]).json()
    assert open_claim(other, unpaid["id"]).status_code == 409


def test_expiry_boundary(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 10, "80")
    src = paid_job_invoice(client, h, vid, pid, users)

    def open_claim():
        return client.post("/api/jobs", json={
            "vehicle_id": vid, "mileage": 52000, "symptom": "x",
            "warranty_source_invoice_id": src["id"], "claim_reason": "อาการเดิม"}, headers=h["admin"])

    # วันหมดประกัน = วันนี้ → เปิดได้
    set_expiry(src["id"], date.today())
    r = open_claim()
    assert r.status_code == 201
    client.post(f"/api/jobs/{r.json()['id']}/cancel",
                json={"reason": "ทดสอบ"}, headers=h["admin"])

    # หมดไปเมื่อวาน → เปิดไม่ได้
    set_expiry(src["id"], date.today() - timedelta(days=1))
    assert open_claim().status_code == 409
```

**`set_expiry` แก้วันหมดประกันตรง ๆ ในเทสต์** — วิธีเดียวที่จะทดสอบเส้นแบ่งวันได้โดยไม่ต้องรอ 30 วัน หรือไปทำระบบปลอมเวลาให้ซับซ้อน
**ทดสอบทั้งสองฝั่งของเส้นแบ่ง** (ตรงวัน = ได้ / เลยไปวันเดียว = ไม่ได้) เพราะ off-by-one ตรงนี้คือบั๊กที่ลูกค้าจะโวยแน่นอน

---

# ส่วนหน้าจอ

## 6. `pages/VehiclesPage.jsx` — ค้นหารถ

```jsx
import { useState } from "react";
import { carName, useApi } from "../api";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import SearchBar from "../components/SearchBar";

export default function VehiclesPage() {
  const [q, setQ] = useState("");
  const { data, error, reload } = useApi(`/vehicles?${new URLSearchParams({ q: q.trim() })}`);

  return (
    <ListLayout title="ประวัติรถ" basePath="/vehicles" context={{ reload }}
      toolbar={<SearchBar q={q} setQ={setQ} placeholder="ค้นทะเบียน เบอร์ หรือชื่อลูกค้า" />}>
      {error && <p role="alert" className="field-error">{error}</p>}
      {!q.trim() && <p className="text-sm text-muted">แสดงรถที่เพิ่มล่าสุด ค้นหาเพื่อดูคันอื่น</p>}
      <DataTable items={data} to={(v) => `/vehicles/${v.id}`} empty="ไม่พบรถ"
        card={(v) => (
          <>
            <div className="text-lg font-bold">
              {v.plate} <span className="text-sm font-normal text-muted">{v.plate_province}</span>
            </div>
            <div className="text-sm">{carName(v)}</div>
            <div className="mt-1 truncate text-sm text-muted">{v.customer.name} · {v.customer.phone}</div>
          </>
        )}
        columns={[
          { label: "ทะเบียน", render: (v) => v.plate },
          { label: "จังหวัด", render: (v) => v.plate_province },
          { label: "รถ", render: carName },
          { label: "เจ้าของ", render: (v) => v.customer.name },
          { label: "เบอร์", render: (v) => v.customer.phone },
        ]} />
    </ListLayout>
  );
}
```

**ไม่มีปุ่ม "เพิ่มรถ"** — รถเกิดจากการเปิดใบงานเท่านั้น ไม่มีใครมาลงทะเบียนรถไว้เฉย ๆ

**บอกว่ากำลังแสดงอะไรอยู่ตอนยังไม่ค้น** — ป้องกันคนเข้าใจผิดว่าระบบมีรถแค่ 50 คัน (API `limit(50)`)

## 7. `pages/VehiclePage.jsx` — ไทม์ไลน์ประวัติ + ปุ่มเคลม

```jsx
export default function VehiclePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isStaff = user.role !== "mechanic";
  const { data: h, error, reload } = useApi(`/vehicles/${id}/history`);
  const [editing, setEditing] = useState(false);

  if (error) return <DetailLayout back="/vehicles" backLabel="ประวัติรถ" title="ประวัติรถ">
    <p role="alert" className="field-error">{error}</p></DetailLayout>;
  if (!h) return <DetailLayout back="/vehicles" backLabel="ประวัติรถ" title="กำลังโหลด…" />;

  const v = h.vehicle;
  const c = h.customer;
  const active = h.jobs.find((j) => !["closed", "cancelled"].includes(j.status));
  const summary = [
    ["เข้ารับบริการ", `${h.visits} ครั้ง`],
    ["ล่าสุด", thaiDate(h.last_visit_at)],
    ["ไมล์ล่าสุด", h.last_mileage != null ? qty(h.last_mileage) : "-"],
  ];

  return (
    <DetailLayout back="/vehicles" backLabel="ประวัติรถ" title={`${v.plate} ${v.plate_province}`}
      subtitle={carName(v)}
      menu={isStaff ? [{ label: "แก้ข้อมูลรถและลูกค้า", onClick: () => setEditing(true) }] : []}
      footer={active ? (
        <Link to={`/jobs/${active.id}`} className="btn btn-primary w-full">
          <Icon name="wrench" size={20} />ไปที่ใบงานค้าง {active.display_number}
        </Link>
      ) : (
        <Link to={`/jobs/new?vehicle=${v.id}`} className="btn btn-primary w-full">
          <Icon name="plus" size={20} />เปิดใบงาน
        </Link>
      )}>
      <div className="flex items-center justify-between gap-3 rounded-xl border border-line p-4">
        <div className="min-w-0">
          <div className="font-semibold">{c.name}</div>
          <div className="text-sm text-muted">
            {c.phone}{c.tax_id && ` · เลขผู้เสียภาษี ${c.tax_id}`}
          </div>
          {c.address && <div className="text-sm text-muted">{c.address}</div>}
        </div>
        <a href={`tel:${c.phone}`} className="btn btn-secondary"><Icon name="phone" size={20} />โทร</a>
      </div>
      <dl className="grid grid-cols-3 gap-2 text-sm">
        {summary.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-surface p-2">
            <dt className="text-muted">{label}</dt><dd className="num font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      {v.notes && <p className="text-sm text-muted">หมายเหตุรถ: {v.notes}</p>}

      <section className="space-y-2">
        <h2 className="font-semibold">ประวัติการเข้ารับบริการ</h2>
        {h.jobs.length === 0 && <p className="text-muted">ยังไม่เคยเข้ารับบริการ</p>}
        <ol className="divide-y divide-line rounded-xl border border-line">
          {h.jobs.map((j) => (
            <li key={j.id} className="space-y-2 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link to={`/jobs/${j.id}`} className="font-semibold text-accent hover:underline">
                  {j.display_number}
                </Link>
                <span className="flex flex-wrap gap-1">
                  {j.is_claim && <StatusBadge status="claim" />}<StatusBadge status={jobKey(j)} />
                </span>
              </div>
              <div className="num text-sm text-muted">
                {thaiDate(j.opened_at)} · {qty(j.mileage)} กม.
                {j.mechanics.length > 0 && ` · ${j.mechanics.map((m) => m.full_name).join(", ")}`}
              </div>
              <p className="text-sm">{j.symptom}</p>
              {j.is_claim && (
                <p className="text-sm text-muted">
                  เคลมจากบิล {j.warranty_source_number}: {j.claim_reason}
                </p>
              )}
              <ul className="text-sm text-muted">
                {j.items.map((i, k) => (
                  <li key={k} className="flex justify-between gap-2">
                    <span>{i.description} × {qty(i.qty)}</span><span className="num">{money(i.line_total)}</span>
                  </li>
                ))}
                <li className="flex justify-between gap-2">
                  <span>ค่าแรง</span><span className="num">{money(j.labor_total)}</span>
                </li>
              </ul>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm">
                  {!j.invoice_number ? "ยังไม่มีบิล"
                    : isStaff ? <Link to={`/invoices/${j.invoice_id}`}
                                      className="text-accent underline">{j.invoice_number}</Link>
                    : j.invoice_number}
                </span>
                <span className="num font-bold">{money(j.total)}</span>
              </div>
              {j.in_warranty && (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg
                                bg-ok-soft px-3 py-1.5 text-ok-ink">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Icon name="shield" size={18} />ในประกันถึง {thaiDate(j.warranty_expires_on)}
                  </span>
                  {!active && (
                    <Link to={`/jobs/new?vehicle=${v.id}&claim=${j.invoice_id}`}
                          className="btn btn-secondary">เปิดงานเคลม</Link>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
      </section>

      {editing && <VehicleEditPage history={h} onClose={() => setEditing(false)}
                               onSaved={() => { setEditing(false); reload(); }} />}
    </DetailLayout>
  );
}
```

**นี่คือหน้าที่พนักงานเปิดตอนลูกค้ายืนอยู่ตรงหน้า** — ทุกอย่างที่ต้องตอบลูกค้าอยู่ในจอเดียว: เคยซ่อมอะไรไป ใครซ่อม จ่ายไปเท่าไหร่ ยังอยู่ในประกันไหม

**แถบเขียว "ในประกันถึง …" พร้อมปุ่มเปิดงานเคลม**
สองอย่างนี้ต้องอยู่ติดกัน เพราะเป็นคำถามกับคำตอบของสถานการณ์เดียวกัน ("ลูกค้าบอกว่าอาการเดิมกลับมา")

**ปุ่มเคลมหายเมื่อรถมีใบงานค้าง** (`!active`) — รถหนึ่งคันมีใบงานค้างได้ใบเดียว กดไปก็โดน 409 อยู่ดี

**`?vehicle=5&claim=12` ส่งต่อไปหน้าเปิดใบงาน** ซึ่งเลือกรถให้ เปิดโหมดเคลมให้ และเลือกบิลต้นทางให้ (`JobNewPage` อ่าน `useSearchParams` ตั้งแต่เฟส 5) เหลือแค่กรอกอาการที่กลับมา

**ปุ่มหลักเปลี่ยนตามสถานการณ์** — มีใบงานค้าง = "ไปที่ใบงานค้าง JO-xxxxx" · ไม่มี = "เปิดใบงาน"

**ปุ่มโทรข้างชื่อลูกค้า** — หน้านี้ถูกเปิดบ่อยตอนจะโทรตามลูกค้า

**ช่างเห็นเลขบิลแต่ไม่ใช่ลิงก์** (`isStaff ? <Link> : j.invoice_number`) — ตรงกับกฎที่ backend บังคับ (endpoint บิลเป็น staff) ให้ข้อมูลอ้างอิงได้ แต่กดเข้าไม่ได้

**`<ol>` ไม่ใช่ `<ul>`** — ลำดับมีความหมาย (เรียงจากล่าสุด)

## 8. `pages/VehicleEditPage.jsx` — แก้ข้อมูลรถและลูกค้า

ป๊อปอัพเดียวที่แก้ทั้งสองตาราง (`PUT /api/customers/{id}` แล้ว `PUT /api/vehicles/{id}`)

**เฉพาะ staff** — ตามกฎ "ช่างเพิ่มลูกค้าและรถใหม่ได้ตอนเปิดใบงาน แต่แก้ข้อมูลเดิมไม่ได้"
เหตุผล: ข้อมูลเดิมผูกกับเอกสารที่ออกไปแล้ว การแก้ต้องมีคนที่รับผิดชอบเรื่องเอกสาร
(หน้าจอซ่อนเมนูให้ ส่วนจริง ๆ router ก็ตรวจ `require_role` อยู่แล้ว)

## 9. กลับไปเติมหน้า `JobPage.jsx`

```jsx
{/* แถวข้อมูลใบงาน */}
{job.is_claim && <Row label={`เคลมจากบิล ${job.warranty_source_number}`}>{job.claim_reason}</Row>}

{/* ใต้หัวข้อรายการ */}
{job.is_claim && editable &&
  <p className="text-sm text-muted">งานเคลม: ใส่อะไหล่และจำนวนที่ใช้จริง ราคาและค่าแรงเป็น 0</p>}

{/* ในป๊อปอัพเพิ่มอะไหล่ */}
{job.is_claim ? (
  <div><span className="label">ราคา/หน่วย</span>
    <p className="input flex items-center text-muted">0 (งานเคลม)</p></div>
) : (
  <Field label="ราคา/หน่วย" ... />
)}

{/* ปุ่มลิงก์ */}
<Link to={`/vehicles/${job.vehicle_id}`} className="btn btn-secondary">
  <Icon name="history" size={20} />ประวัติรถ
</Link>
```

**ช่องราคาแสดงเป็นข้อความ "0 (งานเคลม)" ไม่ใช่ input ที่ disabled** — บอกเหตุผลไปเลยว่าทำไมแก้ไม่ได้ ดีกว่าช่องเทา ๆ ที่ไม่มีคำอธิบาย

**ค่าแรงก็เช่นกัน** (`editable && !job.is_claim` ถึงจะเป็นช่องกรอก)

**ป๊อปอัพรับเงินของบิลยอด 0 เปลี่ยนเป็น "ยืนยันส่งมอบ" เอง** — `ReceivePayment` จากเฟส 6 เช็ค `grand_total === 0` อยู่แล้ว ไม่ต้องแก้อะไร

## 10. เติมใน `JobNewPage.jsx`

ส่วนงานเคลมที่เตรียมไว้ในเฟส 5 มาใช้งานได้จริงเฟสนี้:

```jsx
const claimable = useApi(vehicleId ? `/vehicles/${vehicleId}/claimable-invoices` : "");
const canClaim = vehicleId && claimable.data?.length > 0;
const [claimOn, setClaimOn] = useState(!!params.get("claim"));
const [claim, setClaim] = useState({ invoice_id: params.get("claim") || "", reason: "" });

...
{canClaim && (
  <section className="space-y-3">
    <h3 className="font-semibold">งานเคลมประกัน</h3>
    <label className="flex min-h-11 cursor-pointer items-center gap-3">
      <input type="checkbox" role="switch" className="size-5 accent-accent"
             checked={claimOn} onChange={(e) => setClaimOn(e.target.checked)} />
      เปิดเป็นงานเคลม (อะไหล่และค่าแรงเป็น 0)
    </label>
    {claimOn && (
      <>
        <label className="block">
          <span className="label">บิลงานซ่อมเดิม</span>
          <select className="input" required value={claim.invoice_id}
                  onChange={(e) => setClaim({ ...claim, invoice_id: e.target.value })}>
            <option value="">— เลือกบิล —</option>
            {claimable.data.map((i) => (
              <option key={i.id} value={i.id}>
                {i.display_number} · ประกันถึง {thaiDate(i.warranty_expires_on)}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="label">อาการที่กลับมา</span>
          <textarea className="input" rows={2} required value={claim.reason}
                    onChange={(e) => setClaim({ ...claim, reason: e.target.value })} />
        </label>
      </>
    )}
  </section>
)}
```

และตอนส่ง:
```jsx
...(canClaim && claimOn && {
  warranty_source_invoice_id: Number(claim.invoice_id), claim_reason: claim.reason }),
```

**ทั้งส่วนนี้ไม่โผล่เลยถ้ารถคันนั้นไม่มีบิลที่เคลมได้** (`canClaim`) — ไม่ต้องอธิบายให้พนักงานฟังว่าทำไมกดไม่ได้ เพราะเขาไม่เห็นตั้งแต่แรก

**dropdown แสดงวันหมดประกันข้างเลขบิล** — เลือกได้ถูกใบโดยไม่ต้องไปเปิดดู

**มาจากปุ่มในหน้าประวัติรถ (`?claim=12`) แล้วติ๊กถูกและเลือกบิลให้อัตโนมัติ** เหลือกรอกอาการอย่างเดียว

---

## เช็คว่าเฟสนี้เสร็จ

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

บนหน้าจอ
- เปิดหน้าประวัติรถที่ปิดงานไปในเฟส 6 → เห็นการเข้ารับบริการ 1 ครั้ง พร้อมรายการ ช่าง ยอดเงิน และ**แถบเขียว "ในประกันถึง …"**
- กด "เปิดงานเคลม" → ฟอร์มเลือกรถและบิลให้แล้ว → กรอกอาการ → เปิดได้
- ในใบงานเคลม: **ช่องราคาเป็น "0 (งานเคลม)"** ใส่อะไหล่ได้ → อนุมัติ → **เปิดหน้าสต็อกดู ของถูกตัดจริง**
- ซ่อมเสร็จ → ออกบิล → **ยอด 0 ปุ่มเป็น "ยืนยันส่งมอบ"** → งานปิด
- เปิดบิลเคลม (เป็น admin) → **กำไรขั้นต้นติดลบสีแดง** เท่ากับต้นทุนอะไหล่
- กลับไปหน้าประวัติรถ → **แถบเขียวยังบอกวันหมดประกันเดิม** ไม่ได้ต่ออายุ
- ลองเปิดเคลมจากบิลขายหน้าร้าน → **ไม่ขึ้นให้เลือกใน dropdown เลย**
- **ล็อกอินเป็น `mech1`** → เปิดงานเคลมได้ · เห็นเลขบิลในประวัติแต่กดเข้าไม่ได้ · ไม่มีเมนูแก้ข้อมูลรถ

## git

```
git add -A && git commit -m "feat: vehicle history, repair warranty and claim jobs"
```
