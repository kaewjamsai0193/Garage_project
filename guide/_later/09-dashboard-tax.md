# เฟส 9 — แดชบอร์ด รายงานภาษี และข้อมูลเดโม

**จบเฟสนี้แล้ว** ระบบครบทั้ง 16 หน้าจอ เห็นกำไรจริง ออกรายงานให้ผู้ทำบัญชีได้

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 10, 11

**ไม่มีตารางใหม่ อ่านอย่างเดียวทั้งเฟส** — ถ้าเขียนแล้วรู้สึกว่าต้องเพิ่มคอลัมน์ แปลว่าเฟสก่อนเก็บข้อมูลไม่ครบ ให้กลับไปแก้ที่ต้นทาง ไม่ใช่เพิ่มตารางสรุป

---

# ส่วน backend

## 1. ตัวช่วยเรื่องโซนเวลาใน SQL

```python
from sqlalchemy import literal_column

# ใส่เป็น literal ตรง ๆ (ไม่ใช่ bind param) เพื่อให้นิพจน์เดียวกันใช้ได้ทั้งใน SELECT และ GROUP BY
BKK = literal_column("'Asia/Bangkok'")


def bkk_day(col):
    return func.date(func.timezone(BKK, col))
```

**ทำไมต้องแปลงโซนเวลาใน SQL ไม่ใช่ใน Python** — รายงานต้อง `GROUP BY วัน` ซึ่งฐานต้องเป็นคนทำ
ถ้าดึงทุกแถวมาแล้วจัดกลุ่มใน Python จะช้าและเปลืองหน่วยความจำเมื่อข้อมูลโต

**ทำไม `literal_column` ไม่ใช่พารามิเตอร์** — Postgres ต้องเห็นนิพจน์ **เหมือนกันเป๊ะ** ทั้งใน `SELECT` และ `GROUP BY` ถึงจะยอมจัดกลุ่มให้
ถ้าใช้ bind param มันจะกลายเป็น `$1` คนละตัวแล้วฟ้อง `column must appear in the GROUP BY clause`

**`date(timezone('Asia/Bangkok', issued_at))`** — บิลที่ออกสี่ทุ่มครึ่งของวันที่ 31 ต้องนับเป็นยอดของวันที่ 31 ไม่ใช่วันที่ 30 (ซึ่งเป็นวัน UTC ตอนนั้น)

## 2. สุขภาพสต็อก

```python
def _low_stock(db) -> list[dict]:
    return [_stock_row(p) for p in db.scalars(
        select(Product).where(Product.is_active, Product.min_stock > 0,
                              Product.qty_on_hand <= Product.min_stock)
        .order_by(Product.code))]


def _dead_stock(db) -> list[dict]:
    days = db.get(Setting, 1).dead_stock_days
    last_issue = (select(func.max(StockMovement.created_at))
                  .join(StockLot, StockLot.id == StockMovement.lot_id)
                  .where(StockLot.product_id == Product.id, StockMovement.movement_type == "issue")
                  .correlate(Product).scalar_subquery())
    first_lot = (select(func.min(StockLot.created_at)).where(StockLot.product_id == Product.id)
                 .correlate(Product).scalar_subquery())
    moved = func.coalesce(last_issue, first_lot)
    rows = db.execute(select(Product, moved)
                      .where(Product.qty_on_hand > 0, moved < timeutil.now() - timedelta(days=days))
                      .order_by(moved)).all()
    return [_stock_row(p, m) for p, m in rows]
```

**`min_stock > 0` ก่อนเทียบ** — ขั้นต่ำ 0 แปลว่าไม่อยากให้เตือน ไม่ใช่ "เตือนตลอดเพราะ 0 ≤ 0"

**`qty_on_hand` ใช้ใน `WHERE` ได้เลย** เพราะเป็น `column_property` (subquery ที่ประกาศไว้ในเฟส 3) ไม่ใช่ค่าที่คำนวณใน Python

**ของนิ่ง: `coalesce(วันเบิกล่าสุด, วันรับเข้าครั้งแรก)`**
สินค้าที่**ไม่เคยถูกเบิกเลย**คือของนิ่งที่แย่ที่สุด แต่ไม่มี movement ขาเบิกให้วัด ต้องนับจากวันที่มันเข้ามาแทน
ถ้าใช้แค่ `max(วันเบิก)` ของพวกนี้จะได้ `NULL` แล้วหลุดจากรายงานไปทั้งที่เป็นปัญหาที่สุด

**`Product.qty_on_hand > 0`** ของที่ขายหมดแล้วไม่ใช่ของนิ่ง

## 3. ผลงานช่าง

```python
def _mechanics(db, today) -> list[dict]:
    closed_day = bkk_day(JobOrder.closed_at)
    rows = db.execute(
        select(User.id, User.full_name, Invoice).select_from(JobOrder)
        .join(JobMechanic, and_(JobMechanic.job_id == JobOrder.id, JobMechanic.is_primary))
        .join(User, User.id == JobMechanic.user_id)
        .outerjoin(Invoice, and_(Invoice.job_id == JobOrder.id, Invoice.status == "issued"))
        .where(JobOrder.status == "closed", JobOrder.warranty_source_invoice_id.is_(None),
               closed_day >= today.replace(day=1), closed_day <= today)
        .options(selectinload(Invoice.items))).all()
    perf = {}
    for user_id, full_name, inv in rows:
        row = perf.setdefault(user_id, {"user_id": user_id, "full_name": full_name, "jobs": 0,
                                        "labor_value": Decimal("0.00")})
        row["jobs"] += 1
        if inv:
            lines = sum((i.line_total for i in inv.items), Decimal(0))
            labor = sum((i.line_total for i in inv.items if i.item_type == "labor"), Decimal(0))
            row["labor_value"] += labor_net_ex_vat(labor, inv.discount_amount, lines, inv.vat_rate)
    return sorted(perf.values(), key=lambda r: (-r["jobs"], r["full_name"]))
```

**`join(JobMechanic, and_(..., JobMechanic.is_primary))` — นับให้ช่างหลักคนเดียว**
งานที่มีช่างสามคน ถ้านับทุกคนจะกลายเป็น 3 งาน ยอดรวมทั้งอู่เฟ้อขึ้นสามเท่า
เงื่อนไข `is_primary` อยู่**ใน `ON` ไม่ใช่ `WHERE`** เพื่อให้ความหมายชัดว่าเป็นส่วนหนึ่งของการจับคู่

**`warranty_source_invoice_id.is_(None)` — ไม่นับงานเคลม**
งานเคลมคืองานแก้ของที่เคยมีปัญหา ไม่ควรนับเป็นผลงาน (และไม่มีรายได้ให้นับด้วย)

**`labor_net_ex_vat` ตัวเดียวกับที่ใช้คำนวณหัก ณ ที่จ่าย** — "มูลค่าค่าแรงที่ช่างคนนี้ทำได้" กับ "ฐานหัก ณ ที่จ่าย" คือเลขเดียวกัน คือค่าแรงสุทธิก่อน VAT
ใช้ฟังก์ชันเดียวกันแปลว่าไม่มีทางคำนวณคนละแบบ

**`outerjoin` กับ `Invoice`** — งานที่ปิดแล้วต้องมีบิลเสมอ (ปิดพร้อมรับเงิน) แต่ outer join กันพังถ้าข้อมูลผิดปกติ นับจำนวนงานได้แม้หาบิลไม่เจอ

**`sorted(key=lambda r: (-r["jobs"], r["full_name"]))`** งานเยอะขึ้นก่อน เท่ากันเรียงตามชื่อ

## 4. การเงิน

```python
def _money(sales=Decimal(0), cost=Decimal(0)) -> dict:
    return {"sales": sales, "cost": cost, "profit": sales - cost}


def _finance(db, today) -> dict:
    day = bkk_day(Invoice.issued_at)
    month_key = func.to_char(func.timezone(BKK, Invoice.issued_at), literal_column("'YYYY-MM'"))
    sums = (func.coalesce(func.sum(Invoice.subtotal_ex_vat), 0),
            func.coalesce(func.sum(Invoice.cost_total), 0))
    month_start = today.replace(day=1)
    first_month = timeutil.add_months(month_start, -11)
    issued = Invoice.status == "issued"
    by_day = {d: _money(s, c) for d, s, c in db.execute(
        select(day, *sums).where(issued, day >= month_start, day <= today).group_by(day)).all()}
    by_month = {m: _money(s, c) for m, s, c in db.execute(
        select(month_key, *sums).where(issued, day >= first_month, day <= today)
        .group_by(month_key)).all()}
    days = [month_start + timedelta(days=i) for i in range(today.day)]
    months = [timeutil.add_months(first_month, i).strftime("%Y-%m") for i in range(12)]
    return {"today": by_day.get(today, _money()),
            "month": by_month.get(today.strftime("%Y-%m"), _money()),
            "daily": [{"day": d, **by_day.get(d, _money())} for d in days],
            "monthly": [{"month": m, **by_month.get(m, _money())} for m in months]}
```

**สูตรกำไรขั้นต้น = `subtotal_ex_vat − cost_total`**

**ยอดขาย "ก่อน VAT หลังหักส่วนลด"** ซึ่งก็คือ `subtotal_ex_vat` ที่เก็บไว้บนบิลตั้งแต่เฟส 6
ถ้าใช้ `grand_total` (รวม VAT) กำไรจะสูงเกินจริงเท่ากับ VAT ทั้งก้อน ซึ่งเป็นเงินที่ต้องส่งสรรพากร ไม่ใช่ของอู่

**`status == "issued"` เท่านั้น** บิลที่ยกเลิกไม่นับเป็นยอดขาย

**งานเคลมนับด้วยโดยอัตโนมัติ** — ยอดขาย 0 ต้นทุนมีจริง → **กำไรติดลบ** ไม่ต้องเขียนเงื่อนไขพิเศษ
ตัวเลขบนแดชบอร์ดจึงบอกความจริงว่าเคลมทำให้อู่เสียเงินเท่าไหร่

**เติมวันและเดือนที่ไม่มียอดให้ครบ**
```python
days = [month_start + timedelta(days=i) for i in range(today.day)]
"daily": [{"day": d, **by_day.get(d, _money())} for d in days]
```
`GROUP BY` คืนเฉพาะวันที่มีบิล วันที่ปิดร้านจะหายไป → กราฟจะบีบวันให้ชิดกันแล้วอ่านผิด
เติมศูนย์ให้ครบทุกวันก่อนส่งออกไป **หน้าจอจะได้ไม่ต้องคิดเอง**

**`month_key` ใช้ `to_char(..., 'YYYY-MM')`** ได้สตริงที่เรียงตามลำดับเวลาอยู่แล้ว ไม่ต้องแยกปีกับเดือนเป็นสองคอลัมน์

## 5. รวมเป็นแดชบอร์ด

```python
def dashboard(db, user) -> dict:
    today = timeutil.today()
    counts = dict(db.execute(select(JobOrder.status, func.count()).group_by(JobOrder.status)).all())
    out = {"queue": {s: counts.get(s, 0) for s in ("pending", "in_progress", "done")},
           "low_stock": _low_stock(db), "dead_stock": _dead_stock(db)}
    if user.role != "mechanic":
        out |= {"reminders_due": count_due(db), "mechanics": _mechanics(db, today)}
    if user.role == "admin":
        out["finance"] = _finance(db, today)
    return out
```

**ตัดข้อมูลตาม role ที่ตัวคำสั่งเลย ไม่ใช่ที่ schema** — ต่างจากบิลกับ Lot ที่ใช้ `by_role`
เพราะที่นี่ไม่ใช่แค่ซ่อนฟิลด์ แต่คือ**ไม่ต้องคำนวณเลย** (`_finance` ยิงหลาย query) ช่างเปิดแดชบอร์ดแล้วไม่ต้องเสียเวลารวมยอดขายที่เขาไม่ได้เห็น

**`out |= {...}`** เป็นการรวม dict แบบ Python 3.9+ อ่านง่ายกว่า `out.update(...)` ในบริบทนี้

**คิวงานทุก role เห็น** — ช่างต้องรู้ว่ามีรถรออยู่กี่คัน

## 6. รายงานภาษี

```python
def tax_report(db, month: str) -> dict:
    start = date.fromisoformat(f"{month}-01")
    end = timeutil.add_months(start, 1)
    day = bkk_day(Invoice.issued_at)
    bills = db.execute(select(Invoice, day).where(day >= start, day < end)
                       .order_by(Invoice.doc_year, Invoice.doc_number)).all()
    sales = [{"id": i.id, "issued_on": d, "display_number": i.display_number,
              "buyer_name": i.buyer_name, "buyer_tax_id": i.buyer_tax_id,
              "tax_invoice_form": i.tax_invoice_form, "subtotal_ex_vat": i.subtotal_ex_vat,
              "vat_amount": i.vat_amount, "grand_total": i.grand_total}
             for i, d in bills if i.status == "issued"]
    cancelled = [{"id": i.id, "issued_on": d, "display_number": i.display_number,
                  "cancel_reason": i.cancel_reason, "cancelled_at": i.cancelled_at}
                 for i, d in bills if i.status == "cancelled"]
    receipts = db.execute(
        select(GoodsReceipt, func.sum(StockLot.cost_total), func.sum(StockLot.vat_amount))
        .join(StockLot, StockLot.receipt_id == GoodsReceipt.id)
        .where(GoodsReceipt.supplier_invoice_no.is_not(None),
               GoodsReceipt.supplier_invoice_date >= start, GoodsReceipt.supplier_invoice_date < end)
        .group_by(GoodsReceipt.id)
        .order_by(GoodsReceipt.supplier_invoice_date, GoodsReceipt.id)).all()
    purchases = [{"id": g.id, "display_number": f"GR-{g.id:05d}",
                  "invoice_date": g.supplier_invoice_date,
                  "supplier_invoice_no": g.supplier_invoice_no, "supplier_name": g.supplier_name,
                  "supplier_tax_id": g.supplier_tax_id, "cost_total": cost, "vat_amount": vat}
                 for g, cost, vat in receipts]
    sales_vat, purchase_vat = _sum(sales, "vat_amount"), _sum(purchases, "vat_amount")
    return {"month": month, "sales": sales, "cancelled": cancelled, "purchases": purchases,
            "summary": {"sales_base": _sum(sales, "subtotal_ex_vat"), "sales_vat": sales_vat,
                        "purchase_base": _sum(purchases, "cost_total"), "purchase_vat": purchase_vat,
                        "net_vat": sales_vat - purchase_vat}}
```

**ภาษีขายเรียงตาม `doc_year, doc_number` ไม่ใช่ตามวันที่**
เพราะจุดประสงค์ของรายงานนี้คือ **ให้ผู้ทำบัญชีไล่ตรวจว่าเลขไม่ข้าม** เรียงตามเลขถึงจะตรวจได้

**บิลที่ยกเลิกแยกเป็นตารางของตัวเอง แต่ต้องมี**
กฎหมายต้องการให้เห็นว่าเลขที่หายไปจากลำดับนั้น "ถูกยกเลิก" ไม่ใช่ "ถูกซ่อน" — นี่คือเหตุผลทั้งหมดที่เราไม่ใช้ SEQUENCE ในเฟส 6

**ภาษีซื้อกรองด้วย `supplier_invoice_date` ไม่ใช่วันรับของ**
ใบกำกับลงวันที่ 28 มี.ค. แต่ของมาถึงวันที่ 2 เม.ย. → **ต้องเข้ารายงานเดือนมีนาคม** ตามวันบนกระดาษ

**`supplier_invoice_no.is_not(None)`** — รับของที่ร้านไม่ออกใบกำกับ ไม่มีภาษีซื้อให้ขอคืน ไม่เข้ารายงาน

**`group_by(GoodsReceipt.id)` = หนึ่งใบกำกับหนึ่งแถว** ใบรับของหนึ่งใบมีหลาย Lot แต่ในรายงานภาษีต้องยุบเป็นบรรทัดเดียวตามใบกำกับ

**`net_vat = ภาษีขาย − ภาษีซื้อ`** คือตัวเลขที่ต้องนำส่งใน ภ.พ.30 (ถ้าติดลบคือขอคืน)

API: `GET /api/reports/tax?month=2026-09` — **admin เท่านั้น**

## 7. `app/demo.py` — ข้อมูลตัวอย่าง

```
docker compose exec api python -m app.demo --reset
```

**หลักการสำคัญ: เดโมต้องเดินผ่าน service จริงทุกขั้น**

```python
from app.services import billing, customers, jobs, purchasing, reminders, stock, users
```
ไม่ใช่ `INSERT` ตรงเข้าตาราง — ถ้า insert ตรง ๆ จะได้ข้อมูลที่ผิดกฎของระบบเอง (Lot ไม่ตรงกับ movement, บิลที่ไม่มีใบงาน, เลขบิลข้าม) แล้วหน้าจอจะแสดงอะไรแปลก ๆ ที่หาสาเหตุไม่เจอ
**เดโมที่เดินผ่าน service จริง = การทดสอบทั้งระบบไปในตัว** ถ้ารันแล้วพัง แปลว่ามีบั๊กจริง

**แล้วค่อยเลื่อนเวลาย้อนหลังทีหลัง**
```python
SHIFTED = [(PurchaseOrder, "created_at"), (GoodsReceipt, "created_at"), (StockLot, "created_at"),
           (JobOrder, "opened_at"), (Invoice, "issued_at"), (Invoice, "received_at"), ...]
```
สร้างข้อมูลวันนี้ทั้งหมด แล้ว `UPDATE` เวลาให้ย้อนไปหลายเดือน — แดชบอร์ดกับกราฟ 12 เดือนถึงจะมีอะไรให้ดู
**ต้องเลื่อนทุกคอลัมน์เวลาที่เกี่ยวข้องพร้อมกัน** ไม่งั้นจะได้บิลที่รับเงินก่อนออก

**เนื้อหาที่ควรมี** — ผู้ใช้ครบ 3 role (รหัส `demo1234`) · สินค้าพร้อม Lot หลายต้นทุน · PO ที่รับครบและรับบางส่วน · ลูกค้ากับรถหลายคัน · ใบงานทุกสถานะ (รออนุมัติ / กำลังซ่อม / เสร็จรอส่งมอบ / ปิดแล้ว / ยกเลิก) · บิลที่รับเงินแล้วและบิลที่ยกเลิก · งานเคลม · รายการเตือนที่ถึงกำหนด

**`--reset` ล้างฐานก่อน** — เดโมต้องรันซ้ำได้เสมอ และรันแล้วได้ผลเหมือนเดิม

## 8. เทสต์

```python
def test_dashboard_hides_finance_from_non_admin(client, h):
    assert "finance" in client.get("/api/dashboard", headers=h["admin"]).json()
    assert "finance" not in client.get("/api/dashboard", headers=h["employee"]).json()
    mech = client.get("/api/dashboard", headers=h["mechanic"]).json()
    assert "finance" not in mech and "mechanics" not in mech


def test_tax_report_admin_only(client, h):
    assert client.get("/api/reports/tax?month=2026-09", headers=h["employee"]).status_code == 403
    assert client.get("/api/reports/tax?month=2026-09", headers=h["admin"]).status_code == 200


def test_claim_makes_profit_negative(client, h, make_vehicle, make_product, stock, users):
    # ... เปิดงานเคลม ออกบิลยอด 0 ยืนยันส่งมอบ ...
    fin = client.get("/api/dashboard", headers=h["admin"]).json()["finance"]
    assert Decimal(fin["month"]["cost"]) > 0
    assert Decimal(fin["month"]["profit"]) < Decimal(fin["month"]["sales"])


def test_tax_report_lists_cancelled_bills(client, h, ...):
    # ออกบิล → ยกเลิก → ต้องอยู่ใน "cancelled" ไม่ใช่ "sales"
    ...


def test_demo_runs_twice(capsys):
    from app import demo
    demo.main(["--reset"])
    demo.main(["--reset"])      # รันซ้ำต้องไม่พัง
```

**`test_dashboard_hides_finance_from_non_admin`** ต้องเช็คว่า **key ไม่มีอยู่** ไม่ใช่ค่าว่าง

---

# ส่วนหน้าจอ

## 9. `pages/DashboardPage.jsx`

```jsx
function Tile({ label, value, note, to }) {
  return (
    <Link to={to} className="card block hover:border-accent">
      <div className="text-sm text-muted">{label}</div>
      <div className="num text-2xl font-bold">{value}</div>
      {note && <div className="num text-sm text-muted">{note}</div>}
    </Link>
  );
}
```

**การ์ดทุกใบเป็นลิงก์** — เห็น "เสร็จรอส่งมอบ 3 คัน" แล้วกดไปหน้าใบงานที่กรองสถานะนั้นได้เลย
แดชบอร์ดที่กดอะไรไม่ได้คือโปสเตอร์ ไม่ใช่เครื่องมือ

### กราฟยอดขาย — ทำด้วย CSS ล้วน ไม่ลงไลบรารี

```jsx
function SalesBars({ rows }) {
  const max = Math.max(0, ...rows.map((r) => Number(r.sales)));
  const total = rows.reduce((sum, r) => sum + Number(r.sales), 0);
  const width = { minWidth: `${rows.length * 16}px` };
  return (
    <figure className="card space-y-3">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold">ยอดขายรายวัน (เดือนนี้)</span>
        <span className="num text-sm text-muted">รวม {money(total)}</span>
      </figcaption>
      {max === 0 ? (
        <p className="py-6 text-center text-sm text-muted">ยังไม่มียอดขายในช่วงนี้</p>
      ) : (
        <div className="overflow-x-auto pt-14">
          <div className="flex h-36 items-end gap-0.5 border-b border-line" style={width}>
            {rows.map((r) => (
              <div key={r.day} tabIndex={0}
                aria-label={`${thaiDate(r.day)} · ยอดขาย ${money(r.sales)} · กำไร ${money(r.profit)}`}
                className="group relative flex h-full min-w-3 flex-1 items-end rounded-sm
                           focus-visible:outline-2">
                <div className="w-full rounded-t bg-accent group-hover:bg-accent-ink
                                group-focus-visible:bg-accent-ink"
                     style={{ height: `${(Number(r.sales) / max) * 100}%` }} />
                <div role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10
                     mb-1 hidden -translate-x-1/2 rounded-lg bg-ink px-2 py-1 text-xs whitespace-nowrap
                     text-white group-hover:block group-focus-visible:block">
                  {thaiDate(r.day)}<br />ขาย {money(r.sales)} · กำไร {money(r.profit)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <details>
        <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium">
          ดูเป็นตาราง
        </summary>
        {/* ตารางที่มีทุกค่า */}
      </details>
    </figure>
  );
}
```

**ทำไมไม่ลง Chart.js / Recharts** — กราฟที่ต้องการคือแท่งตั้งเรียงกัน `<div>` ที่ตั้ง `height: %` ทำได้จบ
ไลบรารีกราฟมีขนาดหลายร้อย KB มี API ให้เรียนรู้ และต้องปรับ theme/ฟอนต์ให้เข้ากับระบบอีก — ไม่คุ้มสำหรับกราฟสองอัน

**`height: (sales / max) * 100%`** — แท่งสูงสุดเต็ม 100% ที่เหลือเทียบสัดส่วนกัน นี่คือกราฟแท่งทั้งหมดที่ต้องรู้

**`tabIndex={0}` + `aria-label` ทุกแท่ง** — คนที่ใช้คีย์บอร์ดหรือ screen reader ต้องเข้าถึงข้อมูลเดียวกันได้ กราฟที่แตะไม่ได้ด้วยคีย์บอร์ดคือข้อมูลที่หายไปสำหรับคนกลุ่มหนึ่ง

**`<details>ดูเป็นตาราง</details>`** — กราฟตอบว่า "แนวโน้มเป็นยังไง" ตารางตอบว่า "วันที่ 12 ขายได้เท่าไหร่เป๊ะ"
เป็นทางออกที่ทั้งเข้าถึงได้และมีประโยชน์จริงกับคนที่อยากได้ตัวเลข

**`pt-14` บนกล่องกราฟ** — เว้นที่ให้ tooltip ที่ลอยขึ้นด้านบน ไม่งั้นแท่งที่สูงสุดจะโดนตัด

**`max === 0` ขึ้นข้อความแทน** — ไม่งั้นได้กราฟเปล่าที่ดูเหมือนพัง (และหารด้วยศูนย์)

### การ์ดที่แสดง

```jsx
{/* ทุก role */}
<Tile label="รอเริ่มซ่อม" value={d.queue.pending} to="/jobs?status=pending" />
<Tile label="กำลังซ่อม" value={d.queue.in_progress} to="/jobs?status=in_progress" />
<Tile label="เสร็จรอส่งมอบ" value={d.queue.done} to="/jobs?status=done" />

{/* admin */}
{d.finance && (
  <>
    <Tile label="ยอดขายวันนี้" value={money(d.finance.today.sales)}
          note={`กำไร ${money(d.finance.today.profit)}`} to="/reports/tax" />
    <Tile label="ยอดขายเดือนนี้" value={money(d.finance.month.sales)}
          note={`กำไร ${money(d.finance.month.profit)}`} to="/reports/tax" />
  </>
)}

{/* admin/employee */}
{d.reminders_due != null &&
  <Tile label="ถึงกำหนดบำรุงรักษา" value={d.reminders_due} to="/reminders" />}
```

**แสดงกำไรใต้ยอดขายเสมอ** — ยอดขายอย่างเดียวหลอกตา ขายเยอะแต่กำไรน้อยคือปัญหาที่ต้องเห็น

**`{d.finance && ...}`** หน้าจอไม่ต้องเช็ค role เอง — ถ้าเซิร์ฟเวอร์ไม่ส่งมาก็ไม่แสดง **แหล่งความจริงมีที่เดียว**

**สุขภาพสต็อกเป็นรายการ ไม่ใช่ตัวเลข** — "ของต่ำกว่าขั้นต่ำ 5 รายการ" ไม่มีประโยชน์เท่ากับ "ผ้าเบรกหน้าเหลือ 1 ชุด" ที่กดไปสั่งซื้อได้เลย

## 10. `pages/TaxReportPage.jsx`

```jsx
export default function TaxReportPage() {
  const [month, setMonth] = useState(() => todayBangkok().slice(0, 7));
  const { data, error } = useApi(`/reports/tax?month=${month}`);
  ...
  return (
    <section className="space-y-4">
      <h1 className="page-title">รายงานภาษี</h1>
      <label className="block max-w-xs">
        <span className="label">เดือน</span>
        <input type="month" className="input" value={month} onChange={(e) => setMonth(e.target.value)} />
      </label>
      {/* สรุป → ภาษีขาย → บิลยกเลิก → ภาษีซื้อ */}
    </section>
  );
}
```

**`<input type="month">` ของ HTML ล้วน** — ไม่ต้องลง date picker library เบราว์เซอร์มีให้แล้ว และได้รูปแบบ `YYYY-MM` ที่ API ต้องการพอดี

**เรียงลำดับบนหน้า: สรุป → ภาษีขาย → บิลยกเลิก → ภาษีซื้อ**
ผู้ทำบัญชีอยากเห็นตัวเลขสรุปก่อน แล้วค่อยไล่ตรวจรายละเอียด

**ตารางภาษีขายเรียงตามเลขบิล** (เซิร์ฟเวอร์เรียงมาให้แล้ว) และ**ตารางบิลยกเลิกอยู่ติดกัน** เพื่อให้ไล่เลขได้ต่อเนื่อง

**`net_vat` เน้นตัวใหญ่** — เป็นตัวเลขเดียวที่ต้องเอาไปกรอกใน ภ.พ.30

## 11. `pages/MorePage.jsx` — เมนูรวมบนมือถือ

แถบล่างใส่ได้ 4-5 เมนู แต่ระบบมี 12 หน้า → หน้านี้รวมที่เหลือไว้

```jsx
const GROUPS = [
  ["งานประจำวัน", [["/jobs", "ใบงาน"], ["/sale", "ขายหน้าร้าน"], ["/invoices", "บิล"]]],
  ["คลังและจัดซื้อ", [["/stock", "สต็อก"], ["/purchase-orders", "ใบสั่งซื้อ"],
                     ["/goods-receipts", "รับของ"]]],
  ["ลูกค้า", [["/vehicles", "ประวัติรถ"], ["/reminders", "เตือนบำรุงรักษา"]]],
  ["สรุปและตั้งค่า", [["/dashboard", "แดชบอร์ด"], ["/reports/tax", "รายงานภาษี"],
                     ["/settings", "ตั้งค่าและผู้ใช้"]]],
];
```

**จัดกลุ่มตามงาน ไม่ใช่เรียงตามตัวอักษร** — คนหาเมนูด้วยการนึกว่า "จะทำอะไร" ไม่ใช่ "ชื่อขึ้นต้นด้วยอะไร"

**กรองตาม role ด้วยรายการเดียวกับ `AppLayout`** — เขียนนิยามเมนูไว้ที่เดียวแล้ว import มาใช้ทั้งสองที่

**มีปุ่มออกจากระบบและชื่อผู้ใช้ท้ายหน้า** — บนมือถือไม่มีเมนูข้างให้วาง

## 12. เก็บงานหน้าจอ

- เติม `MENU` ใน `AppLayout.jsx` ให้ครบทุกหน้า (แถบล่างมือถือเอาแค่ 4-5 อันที่ใช้บ่อย ที่เหลือไปอยู่ใน "อื่น ๆ")
- ตั้งหน้าแรกหลังล็อกอิน: `/jobs` ทุก role (เป็นหน้าที่เปิดบ่อยที่สุด)
- ตรวจว่าทุก route มี `<Guard roles={...}>` ตรงกับสิทธิ์ที่ backend บังคับ

---

## เช็คว่าเฟสนี้เสร็จ

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
docker compose exec api python -m app.demo --reset
```

บนหน้าจอ (หลังรัน demo)
- แดชบอร์ด: คิวงานมีตัวเลข · กราฟ 30 วันมีแท่ง · กราฟ 12 เดือนมีแท่ง · รายการของต่ำกว่าขั้นต่ำมีของ
- กดที่การ์ด "เสร็จรอส่งมอบ" → ไปหน้าใบงานที่กรองสถานะนั้นแล้ว
- เอาเมาส์ชี้แท่งกราฟ → tooltip ขึ้นยอดขายและกำไร · กด Tab ไล่แท่ง → tooltip ขึ้นเหมือนกัน
- กาง "ดูเป็นตาราง" → ตัวเลขตรงกับกราฟ
- **หลังปิดงานเคลม กำไรของเดือนต้องลดลง** เท่ากับต้นทุนอะไหล่ของงานนั้น
- รายงานภาษี: เลือกเดือนปัจจุบัน → ภาษีขายเรียงตามเลขบิลไม่ข้าม · บิลที่ยกเลิกอยู่ในตารางแยก · ภาษีซื้อมีเฉพาะใบรับของที่มีใบกำกับ
- **ล็อกอินเป็น `emp1`** → แดชบอร์ดไม่มีการ์ดการเงินและไม่มีกราฟ · เมนูรายงานภาษีหาย · DevTools ดู response ของ `/api/dashboard` **ไม่มี key `finance`**
- **ล็อกอินเป็น `mech1`** → ไม่มีทั้งการเงินและผลงานช่าง
- ย่อเป็นมือถือ → กราฟเลื่อนซ้ายขวาได้ · เมนู "อื่น ๆ" มีทุกหน้าที่ role นั้นเข้าได้

## git

```
git add -A && git commit -m "feat: dashboard, tax report and demo data"
```
