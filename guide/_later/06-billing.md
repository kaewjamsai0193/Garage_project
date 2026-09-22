# เฟส 6 — บิล รับเงิน และขายหน้าร้าน

**จบเฟสนี้แล้ว** ครบวงจร: เปิดงาน → ซ่อม → ออกบิล → รับเงิน → งานปิดเอง และขายอะไหล่หน้าร้านได้

**อ่านก่อน** `new_scenario_summary.md` หัวข้อ 5, 6 · `data_model.md` หัวข้อ 6

> **ยังไม่ทำเฟสนี้** งานเคลม (เฟส 7) · รอบเตือนบำรุงรักษา (เฟส 8) — เผื่อที่ไว้ในโค้ดแล้วทั้งคู่ เฟสนั้นจะกลับมาเติมใน `receive`

---

## กฎที่ต้องเข้าใจก่อนเขียน

### เลขที่บิล — จุดที่ห้ามพลาด

**ห้ามใช้ SEQUENCE ของ Postgres**

sequence ออกแบบมาให้เร็วและไม่ล็อกกัน แลกกับการ **ข้ามเลขเมื่อ rollback** — ออกบิลแล้ว error เลขนั้นหายไปเลย
แต่กฎหมายภาษีบังคับว่าเลขใบกำกับต้องเรียงต่อกันไม่ข้าม (บิลที่ยกเลิกต้องยังอยู่ในทะเบียนให้ตรวจได้)

ทำแบบนี้แทน: `lock_shop` → `select max(doc_number) + 1 where doc_year = ปีไทย` → ใช้เลขนั้น
ช้ากว่านิดหน่อยเพราะต้องรอล็อก แต่อู่เดียวออกบิลวันละไม่กี่สิบใบ ไม่มีปัญหา

- บิลงานซ่อมกับบิลขายหน้าร้าน **ใช้ชุดเลขเดียวกัน**
- **รีเซ็ตทุกปี** ตามปฏิทินไทย (`timeutil.today().year`)

### สองประเภทเอกสาร

| ประเภท | ข้อมูลผู้ซื้อ |
|---|---|
| อย่างย่อ (ค่าเริ่มต้น) | ไม่บังคับ |
| เต็มรูป | ต้องมีชื่อ + ที่อยู่ + เลขผู้เสียภาษี **ครบ** ไม่งั้นปฏิเสธ |

ทั้งสองแบบใช้เลขชุดเดียวกันและเข้ารายงานภาษีขายเหมือนกัน

### คัดลอกเก็บบนบิล

ชื่ออู่ · ที่อยู่ · เลขผู้เสียภาษีอู่ · ข้อมูลผู้ซื้อ · ประเภทเอกสาร · รายการ · ราคา · **อัตรา VAT** · ส่วนลด · ต้นทุน · **จำนวนวันประกัน**

ทั้งหมดถูกก็อปมาแช่ไว้บนบิลตอนออก **พิมพ์บิลปีที่แล้วต้องได้กระดาษแผ่นเดิมเป๊ะ** แม้ค่าตั้งจะเปลี่ยนไปหมดแล้ว
นี่คือกฎบัญชี ไม่ใช่ความชอบส่วนตัว

**ต้นทุนบนบิล = ต้นทุนที่ตัดจริงตอนอนุมัติ ห้ามตัดสต็อกซ้ำตอนออกบิล**

### หัก ณ ที่จ่าย 3% — ที่คนเข้าใจผิดกันมากที่สุด

ไม่เกี่ยวกับ VAT เลย เป็น**ภาษีเงินได้ของอู่**ที่ลูกค้านิติบุคคลหักไว้แล้วนำส่งสรรพากรแทน พร้อมออกใบ 50 ทวิ ให้อู่ไปใช้เครดิตตอนยื่นภาษี

- หักจาก **ค่าแรงเท่านั้น** อะไหล่เป็นการขายสินค้าไม่ต้องหัก (บิลจึงต้องแยกแถวค่าแรงชัด)
- ฐาน = ค่าแรงหลังหักส่วนแบ่งส่วนลดทั้งบิล **ก่อน VAT**
- ระบบเสนอยอด พนักงานยืนยัน · ลูกค้าบุคคลธรรมดาไม่หัก
- ตัวอย่าง: อะไหล่ 3,210 + ค่าแรง 1,070 → ค่าแรงก่อน VAT 1,000 → หัก 30 → **ลูกค้าจ่ายจริง 4,250**

### รับเงิน
- **ครั้งเดียวเต็มจำนวน** ไม่มีมัดจำ ไม่มีค้างชำระ
- ครบเมื่อ **ยอดรับ + ยอดหัก ณ ที่จ่าย = ยอดบิล** ไม่ตรง → ปฏิเสธ
- บิลยอด 0 ใช้ "ยืนยันส่งมอบ" แทน · รับเงินซ้ำไม่ได้ · ช่างรับเงินไม่ได้

### ยกเลิกบิล
ได้เฉพาะ**ก่อนรับเงิน** ต้องมีเหตุผล เลขเดิมไม่ถูกใช้ซ้ำ
- บิลงานซ่อม: อะไหล่ยังอยู่กับใบงาน สถานะคงเดิม ออกใหม่ได้
- บิลขายหน้าร้าน: ต้องยืนยันว่าของกลับคลังสภาพดี แล้วคืนเข้า **Lot เดิม**

---

# ส่วน backend

## 1. ตารางที่เพิ่ม

```python
class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_year: Mapped[int]
    doc_number: Mapped[int]
    display_number: Mapped[str] = mapped_column(String(50))
    job_id: Mapped[int | None] = fk("job_orders.id")
    seller_name: Mapped[str] = mapped_column(String(200))
    seller_address: Mapped[str] = mapped_column(Text)
    seller_tax_id: Mapped[str] = mapped_column(String(20))
    tax_invoice_form: Mapped[str] = mapped_column(String(12))
    buyer_name: Mapped[str | None] = mapped_column(String(200))
    buyer_address: Mapped[str | None] = mapped_column(Text)
    buyer_tax_id: Mapped[str | None] = mapped_column(String(20))
    discount_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, server_default="0")
    discount_reason: Mapped[str | None] = mapped_column(Text)
    vat_rate: Mapped[Decimal] = mapped_column(RATE)
    subtotal_ex_vat: Mapped[Decimal] = mapped_column(MONEY)
    vat_amount: Mapped[Decimal] = mapped_column(MONEY)
    grand_total: Mapped[Decimal] = mapped_column(MONEY)
    cost_total: Mapped[Decimal] = mapped_column(MONEY)
    status: Mapped[str] = mapped_column(String(10))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[int | None] = fk("users.id")
    cancelled_at: Mapped[datetime | None] = mapped_column(TS)
    issued_by: Mapped[int] = fk("users.id")
    issued_at: Mapped[datetime] = created()
    warranty_days: Mapped[int] = mapped_column(default=0, server_default="0")
    warranty_expires_on: Mapped[date | None] = mapped_column(Date, index=True)
    amount_received: Mapped[Decimal | None] = mapped_column(MONEY)
    withholding_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    payment_method: Mapped[str | None] = mapped_column(String(12))
    received_by: Mapped[int | None] = fk("users.id")
    received_at: Mapped[datetime | None] = mapped_column(TS)
    job: Mapped["JobOrder | None"] = relationship(foreign_keys=[job_id])
    items: Mapped[list["InvoiceItem"]] = relationship(order_by="InvoiceItem.id")
    __table_args__ = (
        UniqueConstraint("doc_year", "doc_number"),
        CheckConstraint("status in ('issued','cancelled')", name="status"),
        CheckConstraint("tax_invoice_form in ('abbreviated','full')", name="form"),
        CheckConstraint("tax_invoice_form <> 'full' or (buyer_name is not null"
                        " and buyer_address is not null and buyer_tax_id is not null)", name="full_buyer"),
        CheckConstraint("discount_amount >= 0 and (discount_amount = 0 or discount_reason is not null)",
                        name="discount"),
        CheckConstraint("grand_total = subtotal_ex_vat + vat_amount", name="total"),
        CheckConstraint("warranty_days >= 0", name="warranty_days"),
        CheckConstraint("status <> 'cancelled' or (received_at is null and cancel_reason is not null)",
                        name="cancel"),
        CheckConstraint(
            "(amount_received is null) = (received_at is null)"
            " and (withholding_amount is null) = (received_at is null)"
            " and (payment_method is null) = (received_at is null)"
            " and (received_by is null) = (received_at is null)", name="payment"),
        CheckConstraint("payment_method is null or payment_method in ('cash','transfer','zero_total')",
                        name="payment_method"),
        CheckConstraint("amount_received is null or (amount_received >= 0 and withholding_amount >= 0)",
                        name="payment_amounts"),
        Index("invoices_one_issued_per_job", "job_id", unique=True,
              postgresql_where=text("job_id is not null and status = 'issued'")),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = fk("invoices.id")
    item_type: Mapped[str] = mapped_column(String(10))
    product_id: Mapped[int | None] = fk("products.id")
    description: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(20))
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_price: Mapped[Decimal] = mapped_column(PRICE)
    line_total: Mapped[Decimal] = mapped_column(MONEY)
    maintenance_cycle_months: Mapped[int | None]
    __table_args__ = (
        UniqueConstraint("invoice_id", "product_id"),
        CheckConstraint(
            "(item_type = 'labor' and product_id is null and qty = 1)"
            " or (item_type = 'part' and product_id is not null and qty > 0)", name="item_type"),
        CheckConstraint("unit_price >= 0", name="unit_price"),
    )
```

**ตารางนี้กว้างที่สุดในระบบเพราะมันคือเอกสารกฎหมาย** ทุกอย่างที่ต้องปรากฏบนกระดาษถูกคัดลอกมาเก็บ ไม่มีการ join ไปเอาตอนพิมพ์

**`UniqueConstraint("doc_year", "doc_number")`** — เลขห้ามซ้ำในปีเดียวกัน (`lock_shop` กันชั้นแรก อันนี้ชั้นสุดท้าย)

**`display_number` เก็บจริง ไม่คำนวณ** ต่างจาก `PO-00001` / `GR-00001` ที่คำนวณจาก id — เพราะมันคือเลขบนเอกสารภาษี ต้องคงที่ตลอดกาล

**`CHECK grand_total = subtotal_ex_vat + vat_amount`** — ให้ฐานยืนยันว่าสูตร VAT ไม่เพี้ยน ถ้า `split_vat` เขียนผิด ฐานจะไม่ยอมรับบิลเลย นี่คือเหตุผลที่ `split_vat` ต้องปัดฐานครั้งเดียวแล้วให้ VAT เป็นส่วนที่เหลือ

**`CHECK` ก้อน `payment` ที่ยาวมาก** — ห้าฟิลด์ของการรับเงิน (`amount_received`, `withholding_amount`, `payment_method`, `received_by`, `received_at`) ต้อง **มีครบทั้งหมด หรือว่างทั้งหมด**
สภาพ "รับเงินแล้วแต่ไม่รู้ว่าใครรับ" หรือ "มียอดรับแต่ไม่มีเวลารับ" เกิดขึ้นไม่ได้เลย

**`CHECK status <> 'cancelled' or received_at is null`** — บิลที่รับเงินแล้วยกเลิกไม่ได้ บังคับที่ฐาน

**`Index("invoices_one_issued_per_job", ...)` partial unique** — ใบงานหนึ่งมีบิลที่ใช้งานได้ใบเดียว แต่บิลที่ยกเลิกแล้วมีกี่ใบก็ได้ (ออกอย่างย่อ → ลูกค้าขอเต็มรูป → ยกเลิกแล้วออกใหม่ ทำได้ไม่จำกัด)

**`InvoiceItem.item_type` แยก `part` กับ `labor`** ด้วย CHECK ที่บังคับรูปร่างต่างกัน:
- `labor` → ไม่มี `product_id` และ `qty = 1` เสมอ
- `part` → ต้องมี `product_id` และ `qty > 0`

**นี่คือโครงสร้างที่ทำให้หัก ณ ที่จ่ายคำนวณได้** — รวมเฉพาะแถว `labor` ก็ได้ฐานค่าแรงทันที ถ้าเก็บค่าแรงเป็นคอลัมน์บนหัวบิลจะแยกยากกว่าและพิมพ์ยากกว่า

**`maintenance_cycle_months` คัดลอกมาเก็บบนรายการบิล** — เฟส 8 ใช้สร้างรอบเตือนตอนรับเงิน ถ้าไปอ่านจาก `products` ตอนนั้น แล้วมีคนแก้รอบของสินค้าไประหว่างนั้น รอบเตือนจะไม่ตรงกับที่ตกลงตอนขาย

## 2. `services/billing.py`

### ออกเลขและสร้างหัวบิล

```python
def _issue(db, head, rows, user, *, job=None, claim=False) -> Invoice:
    """ตรวจหัวบิล ออกเลขถัดไปใต้ lock_shop แล้วเขียนหัว + รายการ · คนเรียกใส่ต้นทุนและ commit เอง"""
    lines_sum = sum((r.line_total for r in rows), Decimal(0))
    if head.discount_amount > 0 and not head.discount_reason:
        raise HTTPException(422, "ส่วนลดต้องมีเหตุผล")
    if head.discount_amount > lines_sum:
        raise HTTPException(409, "ส่วนลดเกินยอดรวม")

    customer = job.customer if job else None
    name = head.buyer_name or (customer.name if customer else None)
    address = head.buyer_address or (customer.address if customer else None)
    tax_id = digits(head.buyer_tax_id) or (customer.tax_id if customer else None)
    if head.tax_invoice_form == "full" and not (name and address and tax_id):
        raise HTTPException(422, "ใบกำกับภาษีเต็มรูปต้องมีชื่อ ที่อยู่ และเลขผู้เสียภาษีของผู้ซื้อ")

    settings = db.get(Setting, 1)
    year = timeutil.today().year
    number = db.scalar(select(func.coalesce(func.max(Invoice.doc_number), 0))
                       .where(Invoice.doc_year == year)) + 1
    grand, subtotal, vat = invoice_totals([r.line_total for r in rows],
                                          head.discount_amount, settings.vat_rate)
    inv = Invoice(doc_year=year, doc_number=number, display_number=f"INV{year}-{number:05d}",
                  job_id=job.id if job else None,
                  seller_name=settings.shop_name, seller_address=settings.shop_address,
                  seller_tax_id=settings.shop_tax_id,
                  tax_invoice_form=head.tax_invoice_form,
                  buyer_name=name, buyer_address=address, buyer_tax_id=tax_id,
                  discount_amount=head.discount_amount,
                  discount_reason=head.discount_reason if head.discount_amount > 0 else None,
                  vat_rate=settings.vat_rate, subtotal_ex_vat=subtotal, vat_amount=vat, grand_total=grand,
                  cost_total=0, status="issued", issued_by=user.id,
                  warranty_days=settings.repair_warranty_days if job and not claim else 0)
    db.add(inv)
    db.flush()
    for row in rows:
        row.invoice_id = inv.id
        db.add(row)
    db.flush()
    return inv
```

**ฟังก์ชันเดียวใช้ทั้งบิลงานซ่อมและบิลหน้าร้าน** ต่างกันแค่ที่มาของ `rows` — เลขบิลจึงมาจากที่เดียว ไม่มีทางหลุดเป็นสองชุด

**`func.max(doc_number) + 1` ใต้ `lock_shop`** — คนเรียกล็อกไว้แล้วเสมอ ถ้าลืมล็อก สองคำสั่งจะอ่าน max ได้เลขเดียวกัน แล้วชน `UniqueConstraint`

**`coalesce(max(...), 0)`** บิลใบแรกของปีต้องได้เลข 1 ไม่ใช่ `None + 1`

**`buyer_* or customer.*`** — บิลงานซ่อมดึงข้อมูลลูกค้ามาให้อัตโนมัติ แต่พิมพ์ทับได้ (บริษัทจ่ายให้พนักงาน / ลูกค้าขอออกในนามคนอื่น)

**เช็ค "เต็มรูปต้องครบ" ที่ service ทั้งที่ฐานมี CHECK อยู่** — ชั้นนอกให้ข้อความไทยที่บอกว่าขาดอะไร ชั้นในกันพลาด (รูปแบบเดียวกับใบกำกับซื้อในเฟส 4)

**`warranty_days` ก็อปจากค่าตั้ง ณ ตอนออกบิล** — เจ้าของอู่เปลี่ยนจาก 30 เป็น 15 วันพรุ่งนี้ บิลวันนี้ยังประกัน 30 วันตามที่สัญญาไว้
บิลขายหน้าร้าน (`job is None`) และบิลงานเคลม (`claim`) ได้ 0 = ไม่มีประกัน

**`cost_total=0` ก่อน** แล้วคนเรียกค่อยคำนวณใส่ทีหลัง เพราะต้นทุนของบิลหน้าร้านต้องรอให้ `issue_fifo` ทำงานก่อน (ยังไม่มี movement ให้รวม)

### บิลงานซ่อม

```python
def issue_job_invoice(db, data, user) -> Invoice:
    lock_shop(db)
    job = get_or_404(db, JobOrder, data.job_id, "ใบงาน")
    if job.status != "done":
        raise HTTPException(409, "ออกบิลได้เมื่อใบงานเสร็จรอส่งมอบ")
    if db.scalar(select(Invoice.id).where(Invoice.job_id == job.id, Invoice.status == "issued")):
        raise HTTPException(409, "ใบงานนี้มีบิลที่ใช้งานอยู่แล้ว")
    claim = job.warranty_source_invoice_id is not None
    if claim and data.discount_amount > 0:
        raise HTTPException(409, "งานเคลมใส่ส่วนลดไม่ได้")

    issued = dict(db.execute(
        select(StockLot.product_id, -func.sum(StockMovement.qty)).select_from(StockMovement)
        .join(StockLot, StockLot.id == StockMovement.lot_id)
        .where(StockMovement.job_id == job.id).group_by(StockLot.product_id)).all())
    if {pid: q for pid, q in issued.items() if q != 0} != {i.product_id: i.qty for i in job.items}:
        raise HTTPException(409, "ยอดเบิกไม่ตรงกับรายการ กรุณาตรวจใบงาน")

    rows = [InvoiceItem(item_type="part", product_id=i.product_id, description=i.description,
                        unit=i.unit, qty=i.qty, unit_price=i.unit_price, line_total=i.line_total,
                        maintenance_cycle_months=i.product.maintenance_cycle_months)
            for i in job.items]
    rows.append(InvoiceItem(item_type="labor", description="ค่าแรง", unit="งาน", qty=1,
                            unit_price=job.labor_total, line_total=job.labor_total))
    inv = _issue(db, data, rows, user, job=job, claim=claim)
    inv.cost_total = _cost(db, StockMovement.job_id == job.id)
    db.commit()
    return inv
```

**บล็อก `issued` คือการตรวจสอบตัวเอง** — เทียบ "ของที่เบิกไปจริงตามสมุดสต็อก" กับ "รายการบนใบงาน" ถ้าไม่ตรงแปลว่ามีอะไรผิดปกติ (คนไปแก้ฐานตรง ๆ / บั๊กที่ยังไม่เจอ)
**ยอมออกบิลผิดไม่ได้** เพราะบิลคือเอกสารภาษี หยุดแล้วบอกคนใช้ดีกว่าออกบิลที่ต้นทุนไม่ตรง

`-func.sum(qty)` เพราะ movement ขาเบิกเป็นค่าลบ · `if q != 0` ตัดสินค้าที่เบิกแล้วคืนครบออก (เกิดตอน unapprove แล้วลบรายการนั้นทิ้ง)

**แถวค่าแรงต่อท้ายเสมอ แม้เป็น 0** — บิลต้องมีโครงเดียวกันทุกใบ และ `invoice_view` รวมแถว labor เพื่อคำนวณหัก ณ ที่จ่าย ถ้าไม่มีแถวจะต้องเขียน `if` เพิ่มทุกที่

```python
def _cost(db, ref) -> Decimal:
    db.flush()
    total = db.scalar(select(func.coalesce(func.sum(-StockMovement.qty * StockLot.unit_cost), 0))
                      .select_from(StockMovement)
                      .join(StockLot, StockLot.id == StockMovement.lot_id).where(ref))
    return q2(total)
```
**ต้นทุนมาจากสมุดสต็อก ไม่ใช่คำนวณใหม่** — `-qty × unit_cost ของ Lot นั้น` รวมทุก movement ที่ผูกกับใบงาน/รายการขายนี้
ขาคืน (`return`, qty เป็นบวก) จะได้ค่าลบ **หักล้างกันเอง** ต้นทุนของงานที่เคย unapprove แล้วอนุมัติใหม่จึงถูกต้องอัตโนมัติ

### ขายหน้าร้าน

```python
def issue_sale(db, data, user) -> Invoice:
    lock_shop(db)
    products = products_by_id(db, [i.product_id for i in data.items], "บิล")
    rows = []
    for item in data.items:
        p = products[item.product_id]
        price = item.unit_price if item.unit_price is not None else p.sale_price
        rows.append(InvoiceItem(item_type="part", product_id=p.id, description=p.name, unit=p.unit,
                                qty=item.qty, unit_price=price,
                                line_total=line_total(item.qty, price)))
    inv = _issue(db, data, rows, user)
    for row in rows:
        issue_fifo(db, row.product_id, row.qty, user, invoice_item_id=row.id)
    inv.cost_total = _cost(db, StockMovement.invoice_item_id.in_([r.id for r in rows]))
    db.commit()
    return inv
```

**ออกบิลและตัดสต็อกในคำสั่งเดียว** — ต่างจากงานซ่อมที่ตัดตอนอนุมัติ เพราะหน้าร้านไม่มีขั้นตอนกลาง ลูกค้าหยิบของจ่ายเงินกลับบ้าน

**ลำดับ: สร้างรายการ → `_issue` → `issue_fifo`** ต้องเรียงแบบนี้เพราะ `issue_fifo` ต้องการ `row.id` ที่เกิดหลัง `_issue` flush แล้ว
ถ้าของไม่พอ `issue_fifo` โยน 409 → **rollback ทั้งหมด บิลไม่เกิด และเลขไม่ถูกใช้**

**ไม่มีแถว labor** — ขายค่าแรงหน้าร้านไม่ได้ ผลคือ `suggested_withholding` เป็น 0 โดยอัตโนมัติ ไม่ต้องเขียนกฎแยก

### รับเงิน — เหตุการณ์ที่ต้องสำเร็จพร้อมกันหลายอย่าง

```python
def receive(db, invoice_id, data, user) -> Invoice:
    lock_shop(db)
    inv = get_or_404(db, Invoice, invoice_id, "บิล")
    if inv.status != "issued":
        raise HTTPException(409, "บิลนี้ถูกยกเลิกแล้ว")
    if inv.received_at is not None:
        raise HTTPException(409, "บิลนี้รับเงินแล้ว")
    if inv.grand_total == 0:
        if data.payment_method != "zero_total" or data.amount_received or data.withholding_amount:
            raise HTTPException(422, "บิลยอดศูนย์ให้กดยืนยันส่งมอบโดยไม่มียอดรับเงิน")
    elif data.payment_method == "zero_total":
        raise HTTPException(422, "กรุณาเลือกเงินสดหรือโอน")
    if data.amount_received + data.withholding_amount != inv.grand_total:
        raise HTTPException(409, "ยอดรับ + ยอดหัก ณ ที่จ่ายต้องเท่ากับยอดบิล")

    now = timeutil.now()
    day = timeutil.bkk_date(now)
    inv.amount_received, inv.withholding_amount, inv.payment_method = \
        data.amount_received, data.withholding_amount, data.payment_method
    inv.received_by, inv.received_at = user.id, now
    if inv.job_id:
        job = inv.job
        inv.warranty_expires_on = day + timedelta(days=inv.warranty_days) if inv.warranty_days else None
        job.status, job.closed_at = "closed", now
        # เฟส 8 มาเติมตรงนี้: สร้างรอบเตือนของอะไหล่ที่มี maintenance_cycle_months
    db.commit()
    return inv
```

**`amount_received + withholding_amount != grand_total` → ปฏิเสธ**
นี่คือกฎเดียวที่ทำให้ระบบไม่มีลูกหนี้ ไม่มีมัดจำ ไม่มียอดค้าง — จ่ายครบเท่านั้นถึงผ่าน และตรวจที่เซิร์ฟเวอร์ ไม่ใช่แค่หน้าจอคำนวณให้

**`bkk_date(now)` ไม่ใช่ `now.date()`** — วันหมดประกันต้องนับตามวันไทย ลูกค้าจ่ายเงินสี่ทุ่มครึ่งวันที่ 31 ม.ค. ต้องได้ประกันถึง 2 มี.ค. ไม่ใช่ 1 มี.ค. จาก UTC ที่ยังเป็นวันที่ 30

**`if inv.warranty_days else None`** — ตั้งค่าเป็น 0 วัน = ไม่มีประกัน ต้องเป็น `NULL` ไม่ใช่วันที่วันนี้ ไม่งั้นลูกค้าจะเคลมได้ภายในวันเดียวกัน

**`job.status = "closed"` ที่นี่ที่เดียว** — ไม่มี endpoint ให้ปิดงานเอง ปิดพร้อมรับเงินเท่านั้น จึงไม่มีทางส่งมอบรถโดยยังไม่ได้เงิน

**บิลหน้าร้านไม่แตะอะไรเพิ่ม** (`if inv.job_id:`) ไม่มีใบงานให้ปิด ไม่มีรถให้ตั้งประกัน

### ยกเลิกบิล

```python
def cancel_invoice(db, invoice_id, data, user) -> Invoice:
    lock_shop(db)
    inv = get_or_404(db, Invoice, invoice_id, "บิล")
    if inv.status != "issued":
        raise HTTPException(409, "บิลนี้ถูกยกเลิกแล้ว")
    if inv.received_at is not None:
        raise HTTPException(409, "บิลที่รับเงินแล้วยกเลิกไม่ได้")
    if inv.job_id is None:
        if not data.stock_returned:
            raise HTTPException(422, "ต้องยืนยันว่าของกลับเข้าคลังในสภาพพร้อมขาย")
        for row in inv.items:
            return_issued(db, user, invoice_item_id=row.id)
    inv.status, inv.cancel_reason = "cancelled", data.reason
    inv.cancelled_by, inv.cancelled_at = user.id, timeutil.now()
    db.commit()
    return inv
```

**บิลงานซ่อมยกเลิกแล้วไม่คืนของ** เพราะของยังอยู่ในรถลูกค้า ใบงานยังเป็น "เสร็จรอส่งมอบ" ออกบิลใหม่ได้เลย

**บิลหน้าร้านต้องคืน และต้องมีคนกดยืนยันว่าของกลับมาจริง** — `stock_returned` บังคับให้พนักงานคิดก่อนกด ถ้าลูกค้าเอาของไปใช้แล้วเอามาคืนแบบใช้ไม่ได้ ห้ามคืนเข้าสต็อก
`return_issued` รวมยอดสุทธิ ยกเลิกซ้ำจึงไม่คืนของสองเท่า (idempotent จากเฟส 3)

**เลขบิลไม่ถูกใช้ซ้ำ** — แถวยังอยู่ สถานะเป็น `cancelled` รายงานภาษีมีทะเบียนบิลยกเลิกให้ตรวจลำดับ

### `invoice_view` — และยอดหัก ณ ที่จ่ายที่เสนอ

```python
def invoice_view(db, inv) -> dict:
    job = inv.job
    claim = bool(job and job.warranty_source_invoice_id)
    lines = sum((r.line_total for r in inv.items), Decimal(0))
    labor = sum((r.line_total for r in inv.items if r.item_type == "labor"), Decimal(0))
    wht = Decimal("0.00") if claim or not job else \
        suggested_withholding(labor_net_ex_vat(labor, inv.discount_amount, lines, inv.vat_rate))
    ...
    return {
        **{key: getattr(inv, key) for key in COPIED},
        "id": inv.id, "display_number": inv.display_number,
        "kind": "sale" if job is None else ("claim" if claim else "job"),
        ...
        "suggested_withholding": wht,
        "gross_profit": inv.subtotal_ex_vat - inv.cost_total,
        "items": [...],
    }
```

**ยอดหักคำนวณตอนอ่าน ไม่เก็บ** — มันเป็นแค่ข้อเสนอ ยอดจริงคือสิ่งที่พนักงานยืนยันตอนรับเงิน (เก็บใน `withholding_amount`)

**`if claim or not job` → 0** บิลหน้าร้านไม่มีค่าแรง บิลเคลมยอด 0 ทั้งใบ ทั้งคู่ไม่มีอะไรให้หัก

**`gross_profit = subtotal_ex_vat − cost_total`** — **ยอดก่อน VAT** ลบต้นทุน
ถ้าเผลอใช้ `grand_total` กำไรจะสูงเกินจริงเท่ากับ VAT ทั้งก้อน ซึ่งเป็นเงินของสรรพากรไม่ใช่ของอู่

**`COPIED` เป็น tuple ของชื่อฟิลด์** แล้ว `{key: getattr(inv, key) for key in COPIED}` — ประหยัดการพิมพ์ 24 บรรทัด และเพิ่มฟิลด์ใหม่แค่เติมชื่อในรายการ

**`kind` รวมสามกรณีเป็นฟิลด์เดียว** (`job` / `sale` / `claim`) หน้าจอไม่ต้องรู้ว่าต้องเช็ค `job_id` กับ `warranty_source_invoice_id` เอง

## 3. schemas และ router

```python
class BillHeadIn(In):
    tax_invoice_form: Literal["abbreviated", "full"] = "abbreviated"
    buyer_name: str | None = Field(default=None, max_length=200)
    buyer_address: str | None = None
    buyer_tax_id: str | None = Field(default=None, max_length=30)
    discount_amount: Decimal = Field(default=Decimal(0), ge=0, decimal_places=2)
    discount_reason: str | None = None


class JobInvoiceIn(BillHeadIn):
    job_id: int


class SaleIn(BillHeadIn):
    items: list[SaleItemIn] = Field(min_length=1)


class ReceiveIn(In):
    payment_method: Literal["cash", "transfer", "zero_total"]
    amount_received: Decimal = Field(ge=0, decimal_places=2)
    withholding_amount: Decimal = Field(default=Decimal(0), ge=0, decimal_places=2)


class CancelInvoiceIn(In):
    reason: str = Field(min_length=1)
    stock_returned: bool = False
```

**`BillHeadIn` ใช้ร่วมกัน** แล้วสองแบบสืบทอดไปเติมของตัวเอง — ข้อมูลหัวบิลเหมือนกันเป๊ะ เขียนที่เดียว

**`tax_invoice_form` ค่าเริ่มต้นเป็น `abbreviated`** ตรงกับความจริงที่ลูกค้าส่วนใหญ่ไม่ขอเต็มรูป

**`InvoiceOut` / `InvoiceAdminOut`** — `cost_total` กับ `gross_profit` อยู่เฉพาะตัว admin (รูปแบบเดิมจากเฟส 3)

```python
router = APIRouter(prefix="/api/invoices", tags=["billing"])
staff = require_role("admin", "employee")


def out(db, user, inv):
    return by_role(user, InvoiceAdminOut, InvoiceOut, svc.invoice_view(db, inv))


@router.post("/job", response_model=None, status_code=201)
def issue_job_invoice(data: JobInvoiceIn, db=Depends(get_db), user=Depends(staff)):
    return out(db, user, svc.issue_job_invoice(db, data, user))


@router.post("/{invoice_id}/receive", response_model=None)
def receive(invoice_id: int, data: ReceiveIn, db=Depends(get_db), user=Depends(staff)):
    return out(db, user, svc.receive(db, invoice_id, data, user))
```
(`list` / `sale` / `get` / `cancel` เขียนแบบเดียวกัน)

**ทุก endpoint ของบิลเป็น `staff`** ไม่มีตัวไหนให้ช่างเข้าเลย — ช่างเห็นเลขบิลในหน้าใบงานได้ แต่กดเข้าไม่ได้

## 4. เทสต์ — `tests/flows.py` และ `tests/test_billing.py`

ทำตัวช่วยเดินครบวงจรไว้ก่อน เพราะเฟส 7–9 ต้องใช้ซ้ำตลอด:

```python
# tests/flows.py
def ready_job(client, h, vid, pid, users, qty="1", price="1000", labor="1070"):
    """เปิดใบงาน → ใส่รายการ → เลือกช่าง → อนุมัติ → เริ่ม → เสร็จ · คืน id ใบงานที่พร้อมออกบิล"""
    job = client.post("/api/jobs", json={"vehicle_id": vid, "mileage": 50000,
                                         "symptom": "เช็คระยะ"}, headers=h["admin"]).json()
    client.put(f"/api/jobs/{job['id']}/items",
               json={"labor_total": labor,
                     "items": [{"product_id": pid, "qty": qty, "unit_price": price}]}, headers=h["admin"])
    client.put(f"/api/jobs/{job['id']}/mechanics",
               json={"mechanics": [{"user_id": users["mechanic"].id, "is_primary": True}]},
               headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/approve", headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/start", headers=h["admin"])
    client.post(f"/api/jobs/{job['id']}/finish", headers=h["admin"])
    return job["id"]
```

```python
from tests.flows import ready_job


def test_vat_split_and_default_form(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    job = ready_job(client, h, vid, pid, users, qty="1", price="3800", labor="0")
    inv = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    assert inv["subtotal_ex_vat"] == "3551.40"
    assert inv["vat_amount"] == "248.60"
    assert inv["tax_invoice_form"] == "abbreviated"


def test_full_form_requires_buyer_details(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    job = ready_job(client, h, vid, pid, users, price="1000", labor="70")
    assert client.post("/api/invoices/job", json={"job_id": job, "tax_invoice_form": "full"},
                       headers=h["admin"]).status_code == 422
    body = {"job_id": job, "tax_invoice_form": "full", "buyer_name": "บริษัท ก จำกัด",
            "buyer_address": "กรุงเทพ", "buyer_tax_id": "0105500000001"}
    inv = client.post("/api/invoices/job", json=body, headers=h["admin"]).json()
    assert inv["subtotal_ex_vat"] == "1000.00" and inv["vat_amount"] == "70.00"


def test_withholding_suggestion(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    # อะไหล่ 3,210 + ค่าแรง 1,070 ไม่มีส่วนลด → เสนอ 30.00
    job = ready_job(client, h, vid, pid, users, qty="1", price="3210", labor="1070")
    inv = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    assert inv["suggested_withholding"] == "30.00"


def test_withholding_after_discount(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    job = ready_job(client, h, vid, pid, users, qty="1", price="3210", labor="1070")
    inv = client.post("/api/invoices/job",
                      json={"job_id": job, "discount_amount": "428",
                            "discount_reason": "ลูกค้าประจำ"}, headers=h["admin"]).json()
    assert inv["suggested_withholding"] == "27.00"


def test_receive_must_match_total(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    job = ready_job(client, h, vid, pid, users, qty="1", price="3210", labor="1070")
    inv = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    pay = f"/api/invoices/{inv['id']}/receive"

    assert client.post(pay, json={"payment_method": "cash", "amount_received": "4000",
                                  "withholding_amount": "30"}, headers=h["admin"]).status_code == 409
    assert client.post(pay, json={"payment_method": "cash", "amount_received": "4250",
                                  "withholding_amount": "30"}, headers=h["mechanic"]).status_code == 403
    assert client.post(pay, json={"payment_method": "cash", "amount_received": "4250",
                                  "withholding_amount": "30"}, headers=h["admin"]).status_code == 200
    # รับซ้ำไม่ได้
    assert client.post(pay, json={"payment_method": "cash", "amount_received": "4250",
                                  "withholding_amount": "30"}, headers=h["admin"]).status_code == 409
    # ปิดงานและตั้งวันหมดประกันแล้ว
    assert client.get(f"/api/jobs/{job}", headers=h["admin"]).json()["status"] == "closed"
    assert client.get(f"/api/invoices/{inv['id']}",
                      headers=h["admin"]).json()["warranty_expires_on"] is not None


def test_cancel_job_invoice_keeps_stock(client, h, make_vehicle, make_product, stock, users):
    vid, pid = make_vehicle(), make_product()
    stock(pid, 5, "500")
    job = ready_job(client, h, vid, pid, users)
    first = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()

    # ออกบิลซ้อนไม่ได้
    assert client.post("/api/invoices/job", json={"job_id": job},
                       headers=h["admin"]).status_code == 409
    client.post(f"/api/invoices/{first['id']}/cancel",
                json={"reason": "ลูกค้าขอเต็มรูป"}, headers=h["admin"])
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert lots[0]["qty_remaining"] == "4.000"                  # สต็อกไม่เปลี่ยน

    second = client.post("/api/invoices/job", json={"job_id": job}, headers=h["admin"]).json()
    assert second["display_number"] != first["display_number"]  # เลขใหม่ ไม่ใช้เลขเดิมซ้ำ
    assert second["cost_total"] == first["cost_total"]          # ต้นทุนเท่าเดิม


def test_counter_sale(client, h, make_product, stock):
    pid = make_product()
    stock(pid, 1, "300")
    sale = "/api/invoices/sale"
    # ของไม่พอ
    assert client.post(sale, json={"items": [{"product_id": pid, "qty": "2", "unit_price": "600"}]},
                       headers=h["admin"]).status_code == 409
    # ช่างขายไม่ได้
    assert client.post(sale, json={"items": [{"product_id": pid, "qty": "1", "unit_price": "600"}]},
                       headers=h["mechanic"]).status_code == 403
    # ส่วนลดไม่มีเหตุผล
    assert client.post(sale, json={"items": [{"product_id": pid, "qty": "1", "unit_price": "600"}],
                                   "discount_amount": "100"}, headers=h["admin"]).status_code == 422

    inv = client.post(sale, json={"items": [{"product_id": pid, "qty": "1", "unit_price": "600"}],
                                  "discount_amount": "100", "discount_reason": "ลดให้"},
                      headers=h["admin"]).json()
    assert inv["subtotal_ex_vat"] == "467.29" and inv["vat_amount"] == "32.71"
    assert inv["suggested_withholding"] == "0.00"


def test_cancel_sale_returns_stock_once(client, h, make_product, stock):
    pid = make_product()
    stock(pid, 5, "300")
    inv = client.post("/api/invoices/sale",
                      json={"items": [{"product_id": pid, "qty": "2", "unit_price": "600"}]},
                      headers=h["admin"]).json()
    url = f"/api/invoices/{inv['id']}/cancel"
    assert client.post(url, json={"reason": "ลูกค้าคืน"}, headers=h["admin"]).status_code == 422
    assert client.post(url, json={"reason": "ลูกค้าคืน", "stock_returned": True},
                       headers=h["admin"]).status_code == 200
    lots = client.get(f"/api/products/{pid}/lots", headers=h["admin"]).json()
    assert len(lots) == 1 and lots[0]["qty_remaining"] == "5.000"
    # ยกเลิกซ้ำไม่ได้
    assert client.post(url, json={"reason": "x", "stock_returned": True},
                       headers=h["admin"]).status_code == 409
```

ครอบคลุมกรณีตรวจรับข้อ 4, 5, 6, 9, 12, 19 — **เลขทั้งหมดเอามาจาก `data_model.md` ตรง ๆ ไม่ได้คิดเอง**

---

# ส่วนหน้าจอ

## 5. `components/BillFields.jsx`

```jsx
import Field from "./Field";

export const BLANK_BILL = {
  tax_invoice_form: "abbreviated", buyer_name: "", buyer_address: "",
  buyer_tax_id: "", discount_amount: "", discount_reason: "",
};

export const billBody = (v) => ({
  tax_invoice_form: v.tax_invoice_form,
  buyer_name: v.buyer_name || null, buyer_address: v.buyer_address || null,
  buyer_tax_id: v.buyer_tax_id || null,
  discount_amount: v.discount_amount || "0", discount_reason: v.discount_reason || null,
});

export default function BillFields({ value, onChange, lineTotal, noDiscount = false }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });
  const full = value.tax_invoice_form === "full";
  const buyer = (
    <div className="space-y-3">
      <Field label="ชื่อผู้ซื้อ" required={full} value={value.buyer_name} onChange={set("buyer_name")} />
      <label className="block">
        <span className="label">ที่อยู่ผู้ซื้อ</span>
        <textarea className="input" rows={2} required={full}
                  value={value.buyer_address} onChange={set("buyer_address")} />
      </label>
      <Field label="เลขผู้เสียภาษีผู้ซื้อ" inputMode="numeric" required={full}
             value={value.buyer_tax_id} onChange={set("buyer_tax_id")} />
    </div>
  );

  return (
    <>
      <section className="space-y-3">
        <h3 className="font-semibold">ประเภทเอกสาร</h3>
        <div role="group" aria-label="ประเภทเอกสาร" className="flex flex-wrap gap-2">
          {[["abbreviated", "อย่างย่อ"], ["full", "เต็มรูป"]].map(([key, label]) => (
            <button key={key} type="button" aria-pressed={value.tax_invoice_form === key}
              onClick={() => onChange({ ...value, tax_invoice_form: key })}
              className={`chip ${value.tax_invoice_form === key ? "chip-on" : ""}`}>{label}</button>
          ))}
        </div>
        <p className="text-sm text-muted">
          {full ? "ใบเสร็จรับเงิน/ใบกำกับภาษีเต็มรูป ต้องมีชื่อ ที่อยู่ และเลขผู้เสียภาษีของผู้ซื้อ"
                : "ใบเสร็จรับเงิน/ใบกำกับภาษีอย่างย่อ สำหรับลูกค้าทั่วไป"}
        </p>
        {full ? buyer : (
          <details className="rounded-lg border border-line px-3">
            <summary className="flex min-h-11 cursor-pointer items-center font-medium">
              ข้อมูลผู้ซื้อ (ไม่บังคับ)
            </summary>
            <div className="pb-3">{buyer}</div>
          </details>
        )}
      </section>
      {!noDiscount && (
        <section className="space-y-3">
          <h3 className="font-semibold">ส่วนลดทั้งบิล</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="ส่วนลด (บาท)" type="number" inputMode="decimal" step="0.01" min="0"
                   max={lineTotal} placeholder="0"
                   value={value.discount_amount} onChange={set("discount_amount")} />
            <Field label="เหตุผลส่วนลด" required={Number(value.discount_amount) > 0}
                   value={value.discount_reason} onChange={set("discount_reason")} />
          </div>
        </section>
      )}
    </>
  );
}
```

**ใช้ร่วมกันสองที่** — ป๊อปอัพออกบิลในหน้าใบงาน และหน้าขายหน้าร้าน

**`required={full}` เปลี่ยนตามประเภทเอกสาร** — เบราว์เซอร์บล็อกให้ก่อนถึงเซิร์ฟเวอร์ ผู้ใช้เห็นทันทีว่าช่องไหนบังคับ

**ช่องผู้ซื้อ "ยุบ" ตอนอย่างย่อ แต่ "กาง" ตอนเต็มรูป** — โครงเดียวกัน (ตัวแปร `buyer`) แค่ห่อคนละแบบ ข้อมูลที่กรอกไว้ไม่หายตอนสลับ

**`billBody()` แปลง `""` เป็น `null`** — pydantic รับ `None` ได้ แต่ `""` จะทำให้ข้อมูลบนบิลเป็นสตริงว่างแทนที่จะว่างจริง

## 6. `components/ReceivePayment.jsx`

```jsx
import { useState } from "react";
import { api, money } from "../api";
import Modal from "./Modal";

const satang = (v) => Math.round(Number(v || 0) * 100);
const baht = (s) => (s / 100).toFixed(2);

export default function ReceivePayment({ invoice, onClose, onDone }) {
  const [method, setMethod] = useState("cash");
  const [withhold, setWithhold] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const zero = satang(invoice.grand_total) === 0;
  const canWithhold = satang(invoice.suggested_withholding) > 0;
  const wht = withhold && canWithhold ? satang(invoice.suggested_withholding) : 0;
  const pays = satang(invoice.grand_total) - wht;

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    setBusy(true);
    try {
      const body = zero
        ? { payment_method: "zero_total", amount_received: "0", withholding_amount: "0" }
        : { payment_method: method, amount_received: baht(pays), withholding_amount: baht(wht) };
      await api(`/invoices/${invoice.id}/receive`, { method: "POST", body });
      onDone();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`${zero ? "ส่งมอบ" : "รับเงิน"} ${invoice.display_number}`}
      onClose={onClose} onSubmit={submit}
      footer={
        <>
          {msg && <p role="alert" className="field-error mb-2">{msg}</p>}
          <button className="btn btn-primary w-full" disabled={busy}>
            {busy ? "กำลังบันทึก…" : zero ? "ยืนยันส่งมอบ" : `ยืนยันรับเงิน ${money(pays / 100)}`}
          </button>
        </>
      }>
      {zero ? (
        <p className="text-muted">บิลยอด 0 บาท ยืนยันว่าส่งมอบให้ลูกค้าแล้ว ระบบจะปิดใบงาน</p>
      ) : (
        <>
          <div role="group" aria-label="วิธีรับเงิน" className="grid grid-cols-2 gap-2">
            {[["cash", "เงินสด"], ["transfer", "โอน"]].map(([key, label]) => (
              <button key={key} type="button" aria-pressed={method === key} onClick={() => setMethod(key)}
                className={`chip justify-center ${method === key ? "chip-on" : ""}`}>{label}</button>
            ))}
          </div>
          {canWithhold && (
            <label className="flex min-h-11 cursor-pointer items-center gap-3">
              <input type="checkbox" className="size-5 accent-accent"
                     checked={withhold} onChange={(e) => setWithhold(e.target.checked)} />
              <span>
                หัก ณ ที่จ่าย 3%
                <span className="block text-sm text-muted">
                  ลูกค้านิติบุคคล · 3% ของค่าแรงหลังส่วนลด ก่อน VAT
                </span>
              </span>
            </label>
          )}
          <dl className="space-y-1 rounded-lg bg-surface p-3 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">ยอดบิล</dt><dd className="num">{money(invoice.grand_total)}</dd>
            </div>
            {wht > 0 && (
              <div className="flex justify-between gap-3">
                <dt className="text-muted">หัก ณ ที่จ่าย</dt><dd className="num">−{money(wht / 100)}</dd>
              </div>
            )}
            <div className="flex justify-between gap-3 text-lg font-bold">
              <dt>ลูกค้าจ่าย</dt><dd className="num">{money(pays / 100)}</dd>
            </div>
          </dl>
        </>
      )}
    </Modal>
  );
}
```

**คิดเป็นสตางค์ (จำนวนเต็ม) ตลอดทั้งไฟล์**

```js
const satang = (v) => Math.round(Number(v || 0) * 100);
const baht = (s) => (s / 100).toFixed(2);
```
`4280.00 - 30.00` ใน JS ได้ `4249.999999999999` แล้วส่งไปเซิร์ฟเวอร์จะ **ไม่เท่ากับยอดบิล** และโดนปฏิเสธทันที
คูณ 100 เป็นจำนวนเต็มก่อน แล้วค่อยหารกลับตอนส่ง — **นี่คือจุดเดียวในหน้าจอที่ตัวเลขต้องตรงเป๊ะกับเซิร์ฟเวอร์**

**หัก ณ ที่จ่ายเป็นติ๊กถูกอันเดียว ไม่ใช่ช่องให้กรอก** — คำถามจริงคือ "ลูกค้าเป็นนิติบุคคลไหม" ไม่ใช่ "ยอดหักเท่าไหร่" ยอดมาจากเซิร์ฟเวอร์ที่คำนวณด้วย `Decimal` แล้ว
(ถ้าวันหนึ่งต้องพิมพ์ทับให้ตรงกับใบ 50 ทวิ ก็เพิ่มช่องได้ เพราะ API รับ `withholding_amount` อิสระอยู่แล้ว)

**ติ๊กโผล่เฉพาะเมื่อ `suggested_withholding > 0`** — บิลหน้าร้านและบิลเคลมไม่มีให้เห็น ไม่ต้องอธิบายว่าทำไมกดไม่ได้

**บิลยอด 0 เปลี่ยนทั้งหน้าเป็น "ยืนยันส่งมอบ"** ไม่มีวิธีจ่าย ไม่มีตัวเลข เพราะไม่มีเงินเปลี่ยนมือ

**ปุ่มบอกยอดที่จะรับ** (`ยืนยันรับเงิน 4,250.00`) — ยืนยันครั้งสุดท้ายตรงจุดที่กด

## 7. `pages/SalePage.jsx` — ขายหน้าร้าน

```jsx
const checkout = async (e) => {
  e.preventDefault();
  setFail(null);
  setBusy(true);
  let inv = null;
  try {
    inv = await api("/invoices/sale", { method: "POST", body: {
      ...billBody(bill),
      items: cart.map((l) => ({ product_id: l.product.id, qty: l.qty, unit_price: l.unit_price })),
    } });
    const zero = satang(inv.grand_total) === 0;
    await api(`/invoices/${inv.id}/receive`, { method: "POST", body: {
      payment_method: zero ? "zero_total" : method,
      amount_received: inv.grand_total, withholding_amount: "0",
    } });
    setDone(inv);
  } catch (err) {
    setFail({ text: err.message, invoice: inv });
    if (!inv) {
      setBusy(false);      // บิลยังไม่ออก: เก็บตะกร้าไว้ให้แก้แล้วลองใหม่
      return;
    }
  }
  setCart([]);
  setBill(BLANK_BILL);
  setPaying(false);
  setBusy(false);
  products.reload();
};
```

**ขายหน้าร้านคือ 2 request แต่ผู้ใช้เห็นเป็นขั้นตอนเดียว** (ออกบิล → รับเงิน)

**การจัดการ error แยกสองกรณี — สำคัญมาก**

| พังตอนไหน | ทำอะไร |
|---|---|
| **บิลยังไม่ออก** (ของไม่พอ / ส่วนลดไม่มีเหตุผล) | เก็บตะกร้าไว้ แสดง error ในป๊อปอัพ ให้แก้แล้วกดใหม่ |
| **บิลออกแล้วแต่รับเงินพัง** | ล้างตะกร้า แล้ว**ให้ลิงก์ไปที่บิลนั้น** พร้อมข้อความว่ารับเงินไม่สำเร็จ |

กรณีที่สองเกิดยาก แต่ถ้าเกิดแล้วไม่จัดการ จะมีบิลค้างในระบบที่ไม่มีใครรู้ว่ามีอยู่ **และเลขบิลถูกใช้ไปแล้ว**

```jsx
{fail?.invoice && (
  <p role="alert" className="field-error">
    ออกบิล {fail.invoice.display_number} แล้วแต่รับเงินไม่สำเร็จ: {fail.text} ·
    <Link to={`/invoices/${fail.invoice.id}`} className="underline">ไปรับเงินที่บิล</Link>
  </p>
)}
```

**ไม่ใช่ป๊อปอัพ แต่เป็นหน้าเต็ม** — เป็นงานที่ทำซ้ำ ๆ ทั้งวัน ต้องเปิดค้างไว้แล้วขายไปเรื่อย ๆ

**ตะกร้าใช้สตางค์เหมือน `ReceivePayment`** (`lineSatang`) ด้วยเหตุผลเดียวกัน

**เลือกสินค้าซ้ำ = เพิ่มจำนวน** เหมือนป๊อปอัพเพิ่มอะไหล่ในเฟส 5

**ปุ่มลบไม่มี — ใช้ปุ่มลบจำนวนจนเหลือ 0**
```jsx
const minus = (l) => (Number(l.qty) <= 1
  ? setCart((c) => c.filter((x) => x.product.id !== l.product.id))
  : setLine(l.product.id, { qty: String(Number(l.qty) - 1) }));
```
ปุ่มน้อยลงหนึ่งปุ่มต่อแถว และตรงกับสัญชาตญาณของคนใช้เครื่องคิดเงิน

**เตือน "ไม่พอขาย" ตั้งแต่ในตะกร้า** — ไม่ต้องรอไปตายตอนกดรับเงิน (แต่เซิร์ฟเวอร์ยังตรวจจริงอยู่ดี)

**แถบสรุปยอดติดล่าง `sticky`** ตะกร้ายาวแค่ไหนยอดรวมกับปุ่มรับเงินก็อยู่ในสายตาเสมอ

**แถบสีเขียวหลังขายเสร็จพร้อมปุ่มพิมพ์** — ขายเสร็จแล้วสิ่งถัดไปคือพิมพ์ใบเสร็จให้ลูกค้า ต้องอยู่ตรงนั้นเลย

## 8. `pages/InvoicePage.jsx`

```jsx
const unpaid = inv.status === "issued" && !inv.received_at;

<DetailLayout back="/invoices" backLabel="บิล" title={inv.display_number}
  subtitle={FORM_NAME[inv.tax_invoice_form]}
  badge={<span className="flex flex-wrap justify-end gap-1">
    <StatusBadge status={inv.kind} /><StatusBadge status={invoiceKey(inv)} />
  </span>}
  menu={unpaid ? [{ label: "ยกเลิกบิล", danger: true,
                    onClick: () => { setReturned(false); setDialog("cancel"); } }] : []}
  footer={unpaid ? (
    <div className="flex gap-2">
      <button type="button" className="btn btn-primary flex-1" onClick={() => setDialog("pay")}>
        <Icon name="receipt" size={20} />
        {Number(inv.grand_total) > 0 ? `รับเงิน ${money(inv.grand_total)}` : "ยืนยันส่งมอบ"}
      </button>
      <a href={printHref} target="_blank" rel="noreferrer" className="btn btn-secondary">
        <Icon name="printer" size={20} />พิมพ์
      </a>
    </div>
  ) : (
    <a href={printHref} target="_blank" rel="noreferrer" className="btn btn-primary w-full">
      <Icon name="printer" size={20} />พิมพ์
    </a>
  )}>
```

เพิ่มใน `StatusBadge.jsx`:
```jsx
unpaid: ["ค้างรับเงิน", "warn"],
paid: ["รับเงินแล้ว", "ok"],
job: ["งานซ่อม", "neutral"],
sale: ["หน้าร้าน", "neutral"],

export const invoiceKey = (inv) =>
  inv.status === "cancelled" ? "cancelled" : inv.received_at ? "paid" : "unpaid";
```

**ปุ่มหลักเปลี่ยนตามสถานะ** — ยังไม่รับเงิน ปุ่มคือรับเงิน · รับแล้ว ปุ่มคือพิมพ์
**"ยกเลิกบิล" อยู่ในเมนู ⋯ และโผล่เฉพาะตอนยังไม่รับเงิน** ตรงกับกฎที่ service บังคับ

**บล็อกสรุปยอดแสดงทุกขั้นของการคำนวณ**
```jsx
<Row label="รวมรายการ" value={money(inv.lines_total)} />
{Number(inv.discount_amount) > 0 && <Row label={`ส่วนลด (${inv.discount_reason})`} .../>}
<Row label="ฐานภาษี" value={money(inv.subtotal_ex_vat)} />
<Row label={`VAT ${Number(inv.vat_rate)}%`} value={money(inv.vat_amount)} />
<Row strong label="ยอดสุทธิ" value={money(inv.grand_total)} />
```
ลูกค้าถามว่า "ทำไม VAT เท่านี้" พนักงานชี้จอตอบได้ทันที · **ส่วนลดแสดงเหตุผลในวงเล็บ** เพราะต้องตอบได้ว่าลดให้ทำไม

**บรรทัดต้นทุนกับกำไรอยู่ใต้ `user.role === "admin"`** — และข้อมูลก็ไม่ได้ส่งมาให้ role อื่นอยู่แล้ว (`InvoiceOut` ไม่มีฟิลด์นี้)
**กำไรติดลบเป็นสีแดง** — งานเคลม (เฟส 7) จะติดลบเสมอ ตั้งใจให้เห็นชัด

**ป๊อปอัพยกเลิกบิลเปลี่ยนข้อความตาม `kind`** — บิลหน้าร้านมีติ๊ก "สินค้ากลับเข้าคลังในสภาพพร้อมขายแล้ว" ที่ `required` ส่วนบิลงานซ่อมบอกว่าอะไหล่ยังอยู่กับใบงาน

## 9. `pages/PrintInvoicePage.jsx`

```jsx
export default function PrintInvoicePage() {
  const { id } = useParams();
  const { data: inv, error } = useApi(`/invoices/${id}`);
  const part = (r) => r.item_type === "part";

  return (
    <PrintLayout title={inv ? FORM_NAME[inv.tax_invoice_form] : ""} number={inv?.display_number}
      date={inv && thaiDate(inv.issued_at)}
      seller={inv && { name: inv.seller_name, address: inv.seller_address, tax_id: inv.seller_tax_id }}
      loading={!inv} error={error}>
      {inv && (
        <>
          {inv.status === "cancelled" && (
            <p className="border-2 border-danger p-2 text-center text-lg font-bold text-danger">
              ยกเลิกแล้ว · {inv.cancel_reason}
            </p>
          )}
          <div className="grid grid-cols-2 gap-4">
            <Party title="ผู้ซื้อ" lines={[inv.buyer_name || "ลูกค้าทั่วไป", inv.buyer_address,
              inv.buyer_tax_id && `เลขประจำตัวผู้เสียภาษี ${inv.buyer_tax_id}`]} />
            {inv.job_number && <Party title="อ้างอิง"
              lines={[`ใบงาน ${inv.job_number}`, `ทะเบียน ${inv.vehicle_plate}`]} />}
          </div>
          <PrintTable
            head={[["ลำดับ"], ["รายการ"], ["จำนวน", true], ["หน่วย"],
                   ["ราคา/หน่วย", true], ["จำนวนเงิน", true]]}
            rows={inv.items.map((r, k) => [k + 1, r.description,
              part(r) ? qty(r.qty) : "", part(r) ? r.unit : "",
              part(r) ? money(r.unit_price) : "", money(r.line_total)])}
            foot={[
              ["รวม", money(inv.lines_total)],
              ...(Number(inv.discount_amount) > 0
                  ? [[`ส่วนลด (${inv.discount_reason})`, `−${money(inv.discount_amount)}`]] : []),
              ["มูลค่าก่อนภาษี", money(inv.subtotal_ex_vat)],
              [`ภาษีมูลค่าเพิ่ม ${Number(inv.vat_rate)}%`, money(inv.vat_amount)],
              ["ยอดสุทธิ", money(inv.grand_total), true],
            ]} />
          {inv.warranty_expires_on && <p>รับประกันงานซ่อมถึงวันที่ {thaiDate(inv.warranty_expires_on)}</p>}
          {inv.received_at && (
            <p>ชำระแล้ว {thaiDate(inv.received_at)} ({METHOD_NAME[inv.payment_method]})
              {Number(inv.withholding_amount) > 0 &&
                ` · หัก ณ ที่จ่าย ${money(inv.withholding_amount)}`}</p>
          )}
          <Signatures labels={["ผู้รับเงิน"]} />
        </>
      )}
    </PrintLayout>
  );
}
```

โดยมีค่าคงที่สองตัวที่ export จาก `InvoicePage.jsx` (ใช้ทั้งสองหน้า):
```jsx
export const FORM_NAME = { abbreviated: "ใบเสร็จรับเงิน/ใบกำกับภาษีอย่างย่อ",
                           full: "ใบเสร็จรับเงิน/ใบกำกับภาษีเต็มรูป" };
export const METHOD_NAME = { cash: "เงินสด", transfer: "โอน", zero_total: "ส่งมอบ (ยอด 0)" };
```

**`seller={...}` มาจากบิล ไม่ใช่จาก `/settings`** — นี่คือจุดที่การคัดลอกเก็บบนบิลออกดอกผล ย้ายอู่แล้วพิมพ์บิลเก่าได้ที่อยู่เดิมถูกต้อง

**แถวค่าแรงเว้นคอลัมน์จำนวน/หน่วย/ราคาว่าง** (`part(r) ? ... : ""`) — ใส่ "1 งาน × 1,070" ดูแปลก ค่าแรงเป็นก้อนเดียว

**บิลที่ยกเลิกยังพิมพ์ได้ แต่มีกรอบแดง "ยกเลิกแล้ว"** — ต้องเก็บไว้ในแฟ้มให้สรรพากรตรวจลำดับเลข ไม่ใช่ทิ้ง

**`FORM_NAME` เป็นหัวเอกสาร** — ชื่อเต็มตามกฎหมาย ไม่ใช่คำว่า "บิล"

## 10. กลับไปเติมหน้า `JobPage.jsx`

เพิ่มสองเงื่อนไขท้ายชุดปุ่มหลัก:

```jsx
else if (isStaff && job.status === "done" && !job.invoice_id)
  primary = { label: "ออกบิลและรับเงิน", icon: "receipt", onClick: () => setModal("bill") };
else if (isStaff && job.status === "done" && !job.invoice_paid)
  primary = { label: "รับเงิน", icon: "receipt", onClick: () => setModal("pay") };
```

และ `BillModal` ที่ออกบิลแล้วต่อด้วยรับเงินในป๊อปอัพเดียว:

```jsx
function BillModal({ job, onClose }) {
  const c = job.customer;
  const [bill, setBill] = useState({ ...BLANK_BILL, buyer_name: c.name ?? "",
                                     buyer_address: c.address ?? "", buyer_tax_id: c.tax_id ?? "" });
  const [invoice, setInvoice] = useState(null);
  ...
  const submit = async (e) => {
    e.preventDefault();
    const created = await api("/invoices/job",
                              { method: "POST", body: { job_id: job.id, ...billBody(bill) } });
    setInvoice(await api(`/invoices/${created.id}`));
  };

  if (invoice) return <ReceivePayment invoice={invoice} onClose={onClose} onDone={onClose} />;
  return <Modal title="ออกบิล" ...>{/* สรุปรายการ + BillFields ใน <details> */}</Modal>;
}
```

**ทำไมต้องสองขั้น ไม่ยิงทีเดียวจบ** — **ยอดหัก ณ ที่จ่ายที่เสนอ เซิร์ฟเวอร์เป็นคนคำนวณ** และคำนวณได้ก็ต่อเมื่อบิลออกแล้ว (ต้องรู้ส่วนลดจริง อัตรา VAT ที่ล็อกไว้ และแถวค่าแรง)
ออกบิลก่อน → อ่านบิลกลับมา → ป๊อปอัพรับเงินใช้ `suggested_withholding` จากบิลจริง
ผู้ใช้เห็นเป็นการกดปุ่มเดียวแล้วป๊อปอัพเปลี่ยนหน้า

**ข้อมูลผู้ซื้อเติมจากลูกค้าให้อัตโนมัติ** — ลูกค้าที่มีเลขผู้เสียภาษีในระบบ กดเต็มรูปแล้วครบเลย

**`BillFields` อยู่ใน `<details>` ที่ยุบไว้** — บิลส่วนใหญ่เป็นอย่างย่อไม่มีส่วนลด ไม่ต้องเห็นช่องพวกนี้

## 11. route ที่เพิ่ม

```jsx
<Route path="/print/invoice/:id" element={<Guard roles={STAFF}><PrintInvoicePage /></Guard>} />
...
<Route path="sale" element={<Guard roles={STAFF}><SalePage /></Guard>} />
<Route path="invoices" element={<Guard roles={STAFF}><InvoicesPage /></Guard>} />
<Route path="invoices/:id" element={<Guard roles={STAFF}><InvoicePage /></Guard>} />
```

**ขายหน้าร้านเป็นเมนูแยกจากบิล** — คนละงานกันคนละจังหวะ ไม่ควรต้องเข้าหน้าบิลก่อน

`InvoicesPage.jsx` (รายการบิล) เขียนตามแบบเดียวกับ `PurchaseOrdersPage` — `ListLayout` + `DataTable` + ตัวกรอง `ทั้งหมด / ค้างรับเงิน / รับแล้ว / ยกเลิก`

---

## เช็คว่าเฟสนี้เสร็จ

```
docker compose run --rm api pytest
docker compose exec -T web npm run build
```

บนหน้าจอ — **เดินครบวงจรหนึ่งรอบ**
- ใบงานที่ "เสร็จรอส่งมอบ" จากเฟส 5 → กด "ออกบิลและรับเงิน" → ป๊อปอัพรับเงินขึ้นต่อทันที
- ติ๊ก "หัก ณ ที่จ่าย 3%" → ยอดที่ลูกค้าจ่ายลดลง → ยืนยัน
- **ใบงานเปลี่ยนเป็น "ปิดงานแล้ว" เอง** และบิลมีวันหมดประกัน
- พิมพ์บิล → หัวกระดาษเป็นชื่ออู่ · มีแถวค่าแรงแยก · มีบรรทัดหัก ณ ที่จ่าย · มีวันหมดประกัน
- ออกบิลเต็มรูปโดยไม่กรอกเลขผู้เสียภาษี → โดนบล็อก
- ออกบิลใหม่ให้ใบงานที่มีบิลแล้ว → **"ใบงานนี้มีบิลที่ใช้งานอยู่แล้ว"**
- ยกเลิกบิล (ก่อนรับเงิน) → ออกใหม่ → **เลขใหม่ ไม่ใช้เลขเดิมซ้ำ** และสต็อกไม่ขยับ
- ขายหน้าร้าน: ใส่ตะกร้า 2 รายการ → รับเงิน → ของถูกตัดจากคลัง → ยกเลิกบิล (ติ๊กยืนยันของกลับคลัง) → **ของกลับเข้า Lot เดิม จำนวน Lot เท่าเดิม**
- ลองเลขข้อ 19 ด้วยมือ: อะไหล่ 3,210 + ค่าแรง 1,070 → ระบบต้องเสนอยอดหัก **30.00**
- **ล็อกอินเป็น `emp1`** → ไม่เห็นบรรทัดต้นทุนและกำไรบนบิล และ DevTools ก็ไม่มีฟิลด์นั้น
- **ล็อกอินเป็น `mech1`** → เมนูบิลหาย · เปิดใบงานที่ปิดแล้วเห็นเลขบิลแต่กดเข้าไม่ได้

## git

```
git add -A && git commit -m "feat: invoices, payment, counter sale and printing"
```
